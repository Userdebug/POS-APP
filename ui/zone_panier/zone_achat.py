"""ZoneAchat — standalone purchases/reception basket widget.

Handles supplier management, facture editing, and invoice payment.
Owns its own BasketManager — no shared state with ZoneVente.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QGridLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.constants import DEFAULT_SUPPLIER_NAME
from core.formatters import format_grouped_int
from core.suppliers import default_fournisseurs, fournisseur_info_text
from services.facture_edit_service import FactureLineEditService
from services.panier_transactions_service import PanierTransactionsService
from services.reception_persistence_service import ReceptionPersistenceService
from ui.components.panier_table_builder import FactureRowDescriptor, PanierTableBuilder
from ui.style_constants import (
    TOTAL_FACTURE_DISABLED_STYLE,
    TOTAL_FACTURE_ENABLED_STYLE,
)

from .base_basket_widget import BaseBasketZone
from .basket_models import normalize_ligne

logger = logging.getLogger(__name__)


class ZoneAchat(BaseBasketZone):
    """Purchases mode basket with supplier management and facture editing."""

    @property
    def mode_key(self) -> str:
        return "achat"

    @property
    def _draft_key(self) -> str:
        return "achat"

    def __init__(
        self,
        db_manager: Any | None = None,
        tracking_service: Any | None = None,
        current_day_provider: Callable[[], str] | None = None,
    ) -> None:
        super().__init__(db_manager, tracking_service, current_day_provider)
        self.fournisseurs: list[dict[str, Any]] = default_fournisseurs()
        # Load suppliers from DB if available
        if self.db_manager is not None:
            try:
                suppliers_from_db = self.db_manager.achats.get_all_suppliers()
                if suppliers_from_db:
                    self.fournisseurs = suppliers_from_db
            except Exception:
                pass  # Fall back to defaults if DB fails
        self._updating_facture = False

        # Build UI
        from PyQt6.QtWidgets import QHeaderView, QTableWidget

        self.table = QTableWidget(0, 8)
        self.table.setObjectName("factureTable")
        self.table.setHorizontalHeaderLabels(
            ["Noms Produit", "Cat.", "PA", "PRC", "PV", "Qte", "Total", ""]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.cellChanged.connect(self._on_facture_cell_changed)
        self.table.currentCellChanged.connect(self._on_selection_changed)
        self.table.verticalHeader().setFixedWidth(24)
        self.table.verticalHeader().setDefaultSectionSize(30)
        header = self.table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            for col in (1, 2, 3, 4, 5, 6, 7):
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(1, 90)
            self.table.setColumnWidth(2, 70)
            self.table.setColumnWidth(3, 70)
            self.table.setColumnWidth(4, 70)
            self.table.setColumnWidth(5, 90)
            self.table.setColumnWidth(6, 90)
            self.table.setColumnWidth(7, 40)

        controls = self._build_controls()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.addWidget(controls)
        layout.addWidget(self.table, 1)

        self._refresh_combo()
        self.refresh()

    # ==================== Controls ====================

    def _build_controls(self) -> QWidget:
        bar = QWidget()
        layout = QGridLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(4)
        layout.setVerticalSpacing(3)

        self.btn_mode_switch = QPushButton("Vente")
        self.btn_mode_switch.setMinimumHeight(34)
        self.btn_mode_switch.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.btn_mode_switch.clicked.connect(self.mode_switch_request.emit)

        self.combo_fournisseur = QComboBox()
        self.combo_fournisseur.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.combo_fournisseur.setMinimumHeight(34)
        self.combo_fournisseur.currentIndexChanged.connect(self._on_fournisseur_change)

        self.btn_nouveau_fournisseur = QPushButton("+")
        self.btn_nouveau_fournisseur.setMinimumHeight(34)
        self.btn_nouveau_fournisseur.setFixedWidth(40)
        self.btn_nouveau_fournisseur.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        self.btn_nouveau_fournisseur.setToolTip("Ajouter un nouveau fournisseur")
        self.btn_nouveau_fournisseur.clicked.connect(self._add_new_fournisseur)

        self.btn_editer_fournisseur = QPushButton("\u270e")
        self.btn_editer_fournisseur.setMinimumHeight(34)
        self.btn_editer_fournisseur.setFixedWidth(40)
        self.btn_editer_fournisseur.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        self.btn_editer_fournisseur.setToolTip("Modifier le fournisseur sélectionné")
        self.btn_editer_fournisseur.clicked.connect(self._edit_fournisseur)

        self.btn_supprimer_fournisseur = QPushButton("\U0001f5d1\ufe0f")
        self.btn_supprimer_fournisseur.setMinimumHeight(34)
        self.btn_supprimer_fournisseur.setFixedWidth(40)
        self.btn_supprimer_fournisseur.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        self.btn_supprimer_fournisseur.setToolTip("Désactiver le fournisseur sélectionné")
        self.btn_supprimer_fournisseur.clicked.connect(self._delete_fournisseur)

        self.info_fournisseur = QLabel("NIF: - | STAT: - | CONTACT: - | NOTE: -")
        self.info_fournisseur.setStyleSheet("font-size: 11px; color: #a0aec0;")
        self.info_fournisseur.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.info_fournisseur.setMinimumHeight(34)
        self.info_fournisseur.setWordWrap(True)

        self.btn_nouveau_produit = QPushButton("New Product")
        self.btn_nouveau_produit.setMinimumHeight(34)
        self.btn_nouveau_produit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.btn_nouveau_produit.clicked.connect(self._show_add_produit_dialog)

        self.btn_payer = QPushButton("PAYER\n0 Ar")
        self.btn_payer.setObjectName("totalPanierLabel")
        self.btn_payer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.btn_payer.setMinimumHeight(34)
        self.btn_payer.clicked.connect(self.pay_active_invoice)

        layout.addWidget(self.btn_mode_switch, 0, 0, 2, 1)
        layout.addWidget(self.combo_fournisseur, 0, 1)
        layout.addWidget(self.btn_nouveau_fournisseur, 0, 2)
        layout.addWidget(self.btn_editer_fournisseur, 0, 3)
        layout.addWidget(self.btn_supprimer_fournisseur, 0, 4)
        layout.addWidget(self.info_fournisseur, 1, 1)
        layout.addWidget(self.btn_nouveau_produit, 1, 2, 1, 3)
        layout.addWidget(self.btn_payer, 0, 5, 2, 1)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 3)
        layout.setColumnStretch(2, 0)
        layout.setColumnStretch(3, 0)
        layout.setColumnStretch(4, 1)
        layout.setColumnStretch(5, 1)

        # Theme
        from styles.design_tokens import TOKENS

        accent = TOKENS.get("total_facture_border", "#7c2d12")
        border = "#7c2d12"
        bar.setStyleSheet(
            f"background-color: {TOKENS.get('bg_sidebar', '#1e293b')};"
            f" border: 1px solid {border}; border-radius: 10px;"
        )
        self.btn_mode_switch.setStyleSheet(
            f"font-weight: 700; border: 2px solid {accent};"
            f" background-color: {TOKENS.get('total_facture_bg', '#451a03')};"
            f" padding: 2px 4px; color: {TOKENS.get('text_primary', '#f8fafc')};"
        )
        self.btn_payer.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color:"
            f" {TOKENS.get('total_facture_text', '#fed7aa')};"
            f" background-color: {TOKENS.get('total_facture_bg', '#451a03')};"
            f" border: 2px solid {accent};"
            f" padding: 2px 4px; border-radius: 6px;"
        )

        return bar

    # ==================== Supplier Management ====================

    def _refresh_combo(self) -> None:
        combo = self.combo_fournisseur
        current_nom = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        for f in self.fournisseurs:
            combo.addItem(f.get("nom", ""))
        if current_nom:
            idx = combo.findText(current_nom)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        if combo.count() and combo.currentIndex() < 0:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def _current_fournisseur(self) -> dict[str, Any] | None:
        if not self.fournisseurs:
            return None
        idx = self.combo_fournisseur.currentIndex()
        if idx < 0 or idx >= len(self.fournisseurs):
            return self.fournisseurs[0]
        return self.fournisseurs[idx]

    def _on_fournisseur_change(self, _index: int) -> None:
        self._update_action_button_state()

    def _add_new_fournisseur(self) -> None:
        from ui.dialogs.add_fournisseur_dialog import AddFournisseurDialog

        max_code_num = 0
        for f in self.fournisseurs:
            code = f.get("code", "")
            if code and code.startswith("F-"):
                try:
                    num = int(code.split("-")[1])
                    if num > max_code_num:
                        max_code_num = num
                except ValueError:
                    pass
        default_code = f"F-{max_code_num + 1:03d}"

        dialog = AddFournisseurDialog(self, default_code=default_code, db_manager=self.db_manager)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        fournisseur = dialog.get_fournisseur()
        # Persist the new supplier to database
        if self.db_manager is not None:
            try:
                self.db_manager.achats.ensure_supplier(fournisseur)
                # Reload suppliers from database to get the ID and ensure consistency
                suppliers_from_db = self.db_manager.achats.get_all_suppliers()
                self.set_fournisseurs(suppliers_from_db)
            except Exception as exc:
                logger.error(f"Failed to persist new supplier: {exc}")
                QMessageBox.warning(
                    self,
                    "Erreur",
                    f"Impossible d'enregistrer le fournisseur: {exc}",
                )
                return
        else:
            # Fallback: add locally if no db_manager available
            self.fournisseurs.append(fournisseur)
        self._refresh_combo()
        self.combo_fournisseur.setCurrentIndex(len(self.fournisseurs) - 1)
        self.combo_fournisseur.repaint()

    def _edit_fournisseur(self) -> None:
        from ui.dialogs.add_fournisseur_dialog import AddFournisseurDialog

        current = self._current_fournisseur()
        if not current:
            return
        nom = current.get("nom", "")
        if nom == DEFAULT_SUPPLIER_NAME:
            QMessageBox.warning(
                self,
                "Modification impossible",
                "Impossible de modifier le fournisseur par défaut.",
            )
            return

        dialog = AddFournisseurDialog(
            self, default_code=current.get("code", ""), supplier=current, db_manager=self.db_manager
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        fournisseur = dialog.get_fournisseur()
        idx = self.combo_fournisseur.currentIndex()
        if 0 <= idx < len(self.fournisseurs):
            self.fournisseurs[idx] = fournisseur
        # Persist the update to database
        if self.db_manager is not None:
            try:
                self.db_manager.achats.update_supplier(fournisseur)
                # Reload suppliers from database
                suppliers_from_db = self.db_manager.achats.get_all_suppliers()
                self.set_fournisseurs(suppliers_from_db)
            except Exception as exc:
                logger.error(f"Failed to update supplier: {exc}")
                QMessageBox.warning(
                    self,
                    "Erreur",
                    f"Impossible de mettre à jour le fournisseur: {exc}",
                )
                return
        self._refresh_combo()

    def _delete_fournisseur(self) -> None:
        current = self._current_fournisseur()
        if not current:
            return
        nom = current.get("nom", "")
        if nom == DEFAULT_SUPPLIER_NAME:
            QMessageBox.warning(
                self,
                "Suppression impossible",
                "Impossible de supprimer le fournisseur par défaut.",
            )
            return

        confirm = QMessageBox.question(
            self,
            "Confirmer la suppression",
            f"Désactiver le fournisseur '{nom}' ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        # Persist soft delete to database
        if self.db_manager is not None and current.get("id"):
            try:
                self.db_manager.achats.deactivate_supplier(current["id"])
                # Reload suppliers from database
                suppliers_from_db = self.db_manager.achats.get_all_suppliers()
                self.set_fournisseurs(suppliers_from_db)
            except Exception as exc:
                logger.error(f"Failed to deactivate supplier: {exc}")
                QMessageBox.warning(
                    self,
                    "Erreur",
                    f"Impossible de désactiver le fournisseur: {exc}",
                )
                return
        else:
            idx = self.combo_fournisseur.currentIndex()
            if 0 <= idx < len(self.fournisseurs):
                self.fournisseurs.pop(idx)
        self._refresh_combo()

    def set_fournisseurs(self, fournisseurs: list[dict[str, Any]]) -> None:
        self.fournisseurs = list(fournisseurs or [])
        self._refresh_combo()

    # ==================== Table Population ====================

    def _populate_table(self, items: list[dict[str, Any]]) -> None:
        tables_data = PanierTableBuilder.build(items)
        for row_data in tables_data.facture_rows:
            row_f = self.table.rowCount()
            self.table.insertRow(row_f)
            self._ensure_row_marker(self.table, row_f)
            self._insert_facture_row_from_descriptor(row_f, row_data)

    def _append_draft_row(self, draft: dict[str, Any]) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._ensure_row_marker(self.table, row)
        self._insert_achat_row(row, draft, is_brouillon=True)

    def _insert_achat_row(self, row: int, ligne: dict[str, Any], is_brouillon: bool) -> None:
        pa = int(ligne.get("pa", ligne.get("prix", 0)))
        prc = int(ligne.get("prc", 0))
        pv = int(ligne.get("pv", 0))
        qte = int(ligne.get("qte", 1))
        total = pa * qte

        self.table.setItem(row, 0, QTableWidgetItem(str(ligne.get("nom", ""))))
        self.table.setItem(row, 1, QTableWidgetItem(str(ligne.get("categorie", ""))))
        self.table.setItem(row, 2, QTableWidgetItem(format_grouped_int(pa)))
        self.table.setItem(row, 3, QTableWidgetItem(format_grouped_int(prc)))
        self.table.setItem(row, 4, QTableWidgetItem(format_grouped_int(pv)))
        self._render_qte_cell(row, qte, is_brouillon)
        self.table.setItem(row, 6, QTableWidgetItem(format_grouped_int(total)))

        if not is_brouillon:
            self._render_delete_cell(row)
        self._apply_row_validation_style(self.table, row, validated=not is_brouillon)
        # Update action button state to refresh total after adding a line
        self._update_action_button_state()

    def _insert_facture_row_from_descriptor(self, row: int, row_data: FactureRowDescriptor) -> None:
        for col, cell_data in enumerate(row_data.cells):
            item = QTableWidgetItem(cell_data.value)
            if cell_data.align_right:
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            # Removed: item.setBackground(QColor("#bbdefb")) - conflicting with validation style
            flags = item.flags()
            if cell_data.editable:
                item.setFlags(flags | Qt.ItemFlag.ItemIsEditable)
            else:
                item.setFlags(flags & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, col, item)
        self._render_qte_cell(row, row_data.quantity, is_brouillon=False)
        self._render_delete_cell(row)
        self._apply_row_validation_style(self.table, row, validated=True)

    def _render_qte_cell(self, row: int, qte: int, is_brouillon: bool = False) -> None:
        editor = self._build_qte_editor(
            qte,
            lambda: self._change_row_qty(row, -1, is_brouillon),
            lambda: self._change_row_qty(row, +1, is_brouillon),
        )
        if is_brouillon:
            editor.quantity_changed.connect(self._update_quantity_for_draft)
        else:
            editor.quantity_changed.connect(lambda q: self._update_quantity_for_row(row, q))
        self.table.setCellWidget(row, 5, editor)

    def _render_delete_cell(self, row: int) -> None:
        btn = self._create_delete_button(lambda: self._remove_row(row, is_brouillon=False))
        self.table.setCellWidget(row, 7, btn)

    # ==================== Total ====================

    def _compute_total(self, items: list[dict[str, Any]]) -> int:
        return int(PanierTransactionsService.compute_invoice_total_preview(items))

    def _update_action_button_state(self) -> None:
        has_items = len(self.pm.get_actif()) > 0
        self.btn_payer.setEnabled(has_items)
        if has_items:
            self.btn_payer.setStyleSheet(TOTAL_FACTURE_ENABLED_STYLE)
        else:
            self.btn_payer.setStyleSheet(TOTAL_FACTURE_DISABLED_STYLE)
        montant = self._compute_total([normalize_ligne(p) for p in self.pm.get_actif()])
        self.btn_payer.setText(f"PAYER\n{format_grouped_int(montant)} Ar")
        self.info_fournisseur.setText(fournisseur_info_text(self._current_fournisseur()))

    # ==================== Add Product Override ====================

    def add_product(self, produit: dict[str, Any]) -> None:
        """Add product as achat draft (copies pa to prix)."""
        validated = self._validate_product_data(produit)
        validated["prix"] = validated.get("pa", 0)
        self.drafts.set_draft(normalize_ligne(validated), "achat")
        self.refresh()
        # Update action button state to refresh total after adding a line
        self._update_action_button_state()

    # ==================== Facture Cell Editing ====================

    def _on_facture_cell_changed(self, row: int, col: int) -> None:
        if self._updating_facture:
            return
        if row < 0:
            return
        cell = self.table.item(row, col)
        if cell is None:
            return
        text = (cell.text() or "").strip()

        # Resolve the data source: validated item or draft
        items = self.pm.get_actif()
        is_draft = row >= len(items)
        if is_draft:
            draft = self.drafts.get_draft("achat")
            if draft is None:
                return
            try:
                ligne = normalize_ligne(draft)
            except (TypeError, ValueError):
                ligne = normalize_ligne({})
        else:
            try:
                ligne = normalize_ligne(items[row])
            except (TypeError, ValueError):
                ligne = normalize_ligne({})

        result = FactureLineEditService.apply_cell_edit(ligne, col=col, text=text)
        if not result.handled:
            return

        self._updating_facture = True
        try:
            if result.formatted_cell_value is not None:
                item = self.table.item(row, col)
                if item is not None:
                    item.setText(result.formatted_cell_value)
            if col == 2 and result.formatted_prc_value is not None:
                prc_item = self.table.item(row, 3)
                if prc_item is None:
                    prc_item = QTableWidgetItem()
                    prc_item.setFlags(prc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row, 3, prc_item)
                prc_item.setText(result.formatted_prc_value)

            total_item = self.table.item(row, 6)
            if total_item is None:
                total_item = QTableWidgetItem()
                total_item.setFlags(total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 6, total_item)
            if result.formatted_total_value is not None:
                total_item.setText(result.formatted_total_value)
        finally:
            self._updating_facture = False

        # Persist edited data back to source
        if is_draft:
            self.drafts.set_draft(result.line, "achat")
        else:
            items[row] = result.line

        self._update_action_button_state()

    # ==================== Invoice Payment ====================

    def pay_active_invoice(self) -> None:
        """Validate and persist the current invoice."""
        items = self.pm.get_actif()
        if not items:
            return

        validated_items = []
        for item in items:
            quantite = item.get("qte", 1)
            prix = item.get("prix", 0)
            if quantite <= 0:
                logger.warning("Invalid quantity: qte=%s", quantite)
                continue
            if prix < 0:
                logger.warning("Invalid price: prix=%s", prix)
                continue
            validated_items.append(item)

        if not validated_items:
            logger.warning("No valid items to process in pay_active_invoice")
            return

        normalized_items = [normalize_ligne(ligne) for ligne in validated_items]
        total_preview = PanierTransactionsService.compute_invoice_total_preview(normalized_items)

        confirmation = QMessageBox.question(
            self,
            "Confirmer le paiement",
            (
                "Valider cette facture ?\n\n"
                f"Lignes: {len(validated_items)}\n"
                f"Total: {format_grouped_int(total_preview)} Ar"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmation != QMessageBox.StandardButton.Yes:
            return

        numero_facture = PanierTransactionsService.build_invoice_number()
        total_facture = 0
        for row in range(len(validated_items)):
            try:
                total_facture += self._save_reception_row(
                    row,
                    numero_facture=numero_facture,
                    refresh_after=False,
                    emit_product_signal=True,
                )
            except Exception as e:
                logger.error("Failed to save reception row %s: %s", row, e)
                QMessageBox.warning(
                    self,
                    "Erreur d'enregistrement",
                    f"Impossible d'enregistrer la ligne {row + 1}.\nErreur: {e}",
                )

        self.pm.clear_active()
        self.drafts.clear_draft("achat")
        self.refresh()
        self.table.clearSelection()
        self.table.setCurrentCell(-1, -1)
        self._emit_transaction_signal("achats", int(total_facture))

    def _save_reception_row(
        self,
        row: int,
        *,
        numero_facture: str | None,
        refresh_after: bool,
        emit_product_signal: bool,
    ) -> int:
        items = self.pm.get_actif()
        if row < 0 or row >= len(items):
            return 0

        try:
            raw_line = normalize_ligne(items[row])
        except (TypeError, ValueError):
            raw_line = normalize_ligne({})

        fournisseur = self._current_fournisseur() or {"nom": DEFAULT_SUPPLIER_NAME}
        result = ReceptionPersistenceService.save_reception_row(
            raw_line=raw_line,
            db_manager=self.db_manager,
            fournisseur=fournisseur,
            day=self._target_business_day(),
            numero_facture=numero_facture,
        )
        if not result.line:
            return 0

        if emit_product_signal and result.payload is not None:
            self.nouveau_produit_enregistre.emit(dict(result.payload))

        items[row] = dict(result.line)
        if refresh_after:
            self.refresh()
        return int(result.total)

    # ==================== Validation ====================

    def _compute_validation_enabled(self) -> bool:
        from controllers.panier_selection_controller import PanierSelectionController

        return PanierSelectionController.validation_enabled(
            mode="achat",
            has_brouillon=self.drafts.has_draft("achat"),
            has_achats_brouillon=self.drafts.has_draft("achat"),
            panier_row_count=0,
            panier_current_row=-1,
            facture_row_count=self.table.rowCount() if self.table else 0,
            facture_current_row=self.table.currentRow() if self.table else -1,
        )
