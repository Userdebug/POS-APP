"""Zone actions/etats: pont entre calculatrice et actions d'ecrans annexes."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QDate, pyqtSignal
from PyQt6.QtWidgets import (
    QDateEdit,
    QDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.formatters import format_grouped_int
from services.autosave_service import AutosaveService
from ui.components.calculator import CalculatorWidget
from ui.dialogs.cash_closure_dialog import CashClosureDialog
from ui.dialogs.daily_sales_report_dialog import RapportVenteJourDialog
from ui.dialogs.parametres_dialog import ParametresDialog
from ui.dialogs.report_table_dialog import TableReportDialog
from ui.style_constants import VALIDER_BUTTON_DISABLED_STYLE, VALIDER_BUTTON_ENABLED_STYLE


class ZoneActionsEtats(QWidget):
    quantite_depuis_calculatrice = pyqtSignal(int)
    valider_ligne_demande = pyqtSignal()
    ouvrir_mouvements_demande = pyqtSignal()
    ouvrir_depenses_demande = pyqtSignal()
    ouvrir_suivi_demande = pyqtSignal()
    ouvrir_parametres_demande = pyqtSignal()
    cloture_complete = pyqtSignal(
        str
    )  # Signal emitted when cloture workflow completes (emits cloture date)
    fermer_application = pyqtSignal()  # Signal to close the application

    def __init__(
        self,
        db_manager: Any | None = None,
        tracking_service: Any | None = None,
        reports_presenter: Any | None = None,
    ) -> None:
        super().__init__()
        self.db_manager = db_manager
        self.tracking_service = tracking_service
        self.reports_presenter = reports_presenter
        self._mode = "caisse"
        self._autosave_service = AutosaveService(db_manager) if db_manager else None

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(10)

        self.calculatrice = CalculatorWidget()
        self.main_layout.addWidget(self.calculatrice)

        self.calculatrice.quantite_emise.connect(self.quantite_depuis_calculatrice.emit)
        self.calculatrice.valider_ligne_demande.connect(self.valider_ligne_demande.emit)

    def set_mode(self, mode: str) -> None:
        """Memorise le mode courant pour les futures extensions de la zone."""
        self._mode = str(mode or "caisse")

    def update_ui_for_mode(self, mode: str) -> None:
        """Update UI elements when application mode changes.

        Args:
            mode: The new application mode (e.g., 'caisse', 'especes')
        """
        self.set_mode(mode)

    def set_valider_enabled(self, enabled: bool) -> None:
        self.calculatrice.btn_valider.setEnabled(bool(enabled))
        if enabled:
            self.calculatrice.btn_valider.setStyleSheet(VALIDER_BUTTON_ENABLED_STYLE)
        else:
            self.calculatrice.btn_valider.setStyleSheet(VALIDER_BUTTON_DISABLED_STYLE)

    def _open_tracking_report(self):
        if self.db_manager is None and self.tracking_service is None:
            QMessageBox.warning(self, "Erreur", "Service de suivi non disponible")
            return

        dialog = TableReportDialog(
            title="Etat Suivi",
            headers=["Categorie", "Achats (TTC)", "CA"],
            parent=self,
            allow_import=False,
        )
        dialog.controls_layout.addWidget(QLabel("Date:"))
        date_jour = QDateEdit()
        date_jour.setCalendarPopup(True)
        date_jour.setDisplayFormat("dd/MM/yy")
        date_jour.setDate(QDate.currentDate())
        dialog.controls_layout.addWidget(date_jour)
        btn_refresh = QPushButton("Actualiser")
        dialog.controls_layout.addWidget(btn_refresh)
        dialog.controls_layout.addStretch(1)

        def load_data():
            jour = date_jour.date().toString("yyyy-MM-dd")
            if self.tracking_service is not None:
                rows = self.tracking_service.get_tracking_rows(jour)
            elif self.db_manager is not None:
                rows = self.db_manager.get_daily_suivi_form(jour)
            else:
                rows = []
            dialog.set_rows(
                [
                    [
                        str(r.get("categorie", "-")),
                        format_grouped_int(r.get("achats_ttc", 0)),
                        format_grouped_int(r.get("ca_final", 0)),
                    ]
                    for r in rows
                ]
            )

        btn_refresh.clicked.connect(load_data)
        load_data()
        dialog.exec()

    def open_cloture_form(self, jour: str | None = None):
        if self.db_manager is None and self.tracking_service is None:
            return
        target_day = str(jour or QDate.currentDate().toString("yyyy-MM-dd"))
        dialog_rows = []
        suivi_rows = []
        if self.tracking_service is not None:
            dialog_rows = self.tracking_service.get_closure_rows(target_day)
        elif self.db_manager is not None:
            suivi_rows = self.db_manager.get_daily_suivi_form(target_day)
            existing_map = {
                str(r.get("categorie", "")): int(r.get("ca_ttc_final", 0) or 0)
                for r in self.db_manager.get_daily_closure_by_category(target_day)
            }
            for row in suivi_rows:
                categorie = str(row.get("categorie", "")).strip()
                if not categorie:
                    continue
                dialog_rows.append(
                    {
                        "categorie": categorie,
                        "ca_ttc_final": int(
                            existing_map.get(categorie, row.get("ca_final", 0) or 0)
                        ),
                    }
                )
        dialog = CashClosureDialog(self, target_day, self.db_manager)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        if self.tracking_service is not None:
            self.tracking_service.close_day(target_day, values)
        elif self.db_manager is not None:
            self.db_manager.upsert_daily_closure_by_category(target_day, values)
            edits = []
            achats_map = {
                str(r.get("categorie", "")): int(r.get("achats_ttc", 0) or 0) for r in suivi_rows
            }
            for row in values:
                cat = str(row.get("categorie", ""))
                edits.append(
                    {
                        "categorie": cat,
                        "achats_ttc": achats_map.get(cat, 0),
                        "ca_final": int(row.get("ca_ttc_final", 0) or 0),
                    }
                )
            self.db_manager.save_daily_tracking_form_edits(target_day, edits)
            self.db_manager.close_day_from_tracking_form(target_day)

        # Run autosave after successful closure
        self._run_autosave(target_day)

    def _run_autosave(self, target_day: str) -> bool:
        """Run autosave after successful closure.

        Args:
            target_day: The day that was just closed.

        Returns:
            True if autosave succeeded, False otherwise.
        """
        if self._autosave_service is None:
            return False

        success = self._autosave_service.run_autosave(target_day)
        if success:
            self.cloture_complete.emit(target_day)
        return success

    def _open_parametres(self):
        dialog = ParametresDialog(self, self.db_manager)
        dialog.exec()

    def open_cloture_simple(self, jour: str | None = None, parent_window=None):
        """Simplified cloture workflow with CA final entry dialog.

        This method implements the cloture workflow:
        1. Show ClotureCaisseDialog with table by category
        2. Save CA to database on validation
        3. Show "Nouvelle journée créée" message
        4. Create new day with same CA final values per category
        5. Open Rapport Vente Jour dialog

        Args:
            jour: Date in ISO format (YYYY-MM-DD), defaults to today.
            parent_window: Parent window for the dialogs.
        """
        if self.db_manager is None and self.tracking_service is None:
            return

        target_day = str(jour or QDate.currentDate().toString("yyyy-MM-dd"))

        # Start with empty rows - user enters values from scratch
        # Show ClotureCaisseDialog with table
        parent = parent_window if parent_window else self
        dialog = CashClosureDialog(parent, target_day, self.db_manager)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # Get values from dialog
        values = dialog.values()
        ca_final = sum(int(v.get("ca_ttc_final", 0)) for v in values)

        # Save closure to database
        if self.tracking_service is not None:
            self.tracking_service.close_day(target_day, values)
        elif self.db_manager is not None:
            self.db_manager.upsert_daily_closure_by_category(target_day, values)
            # Also update the suivi form
            edits = []
            for v in values:
                edits.append(
                    {
                        "categorie": v.get("categorie", ""),
                        "achats_ttc": 0,
                        "ca_final": v.get("ca_ttc_final", 0),
                    }
                )
            if edits:
                self.db_manager.save_daily_tracking_form_edits(target_day, edits)
            self.db_manager.close_day_from_tracking_form(target_day)

        # Run autosave after successful closure
        self._run_autosave(target_day)

        # Show success message
        QMessageBox.information(
            parent, "Clôture effectuée", "Nouvelle journée créée", QMessageBox.StandardButton.Ok
        )

        # Open Rapport Vente Jour dialog with complete daily report
        if self.reports_presenter is not None:
            rapport_data = self.reports_presenter.get_journalier_complet(target_day)
        else:
            rapport_data = None

        rapport_dialog = RapportVenteJourDialog(parent, target_day, rapport_data)
        # Connect importer clicked signal to close application
        rapport_dialog.importer_clicked.connect(self.fermer_application.emit)
        rapport_dialog.exec()
