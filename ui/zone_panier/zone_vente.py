"""ZoneVente — standalone sales/caisse basket widget.

Handles P1/P2/N/P basket switching, encaissement, and stock validation.
Owns its own BasketManager — no shared state with ZoneAchat.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.constants import DATE_FORMAT_TIME
from core.formatters import format_grouped_int
from services.panier_transactions_service import PanierTransactionsService
from styles.design_tokens import TOKENS
from ui.style_constants import (
    PANIER_TAB_ACTIVE_BORDER_STYLE,
    PANIER_TAB_BASE_STYLE,
    PANIER_TAB_INACTIVE_BORDER_STYLE,
    TOTAL_CAISSE_DISABLED_STYLE,
    TOTAL_CAISSE_ENABLED_STYLE,
)

from .base_basket_widget import BaseBasketZone
from .basket_models import ligne_total, normalize_ligne

logger = logging.getLogger(__name__)


class ZoneVente(BaseBasketZone):
    """Sales mode basket with P1/P2/N/P switching and encaissement."""

    sales_day_recorded = pyqtSignal(object)
    dialog_closed = pyqtSignal()

    @property
    def mode_key(self) -> str:
        return "vente"

    @property
    def _draft_key(self) -> str:
        return "vente"

    def __init__(
        self,
        db_manager: Any | None = None,
        tracking_service: Any | None = None,
        current_day_provider: Callable[[], str] | None = None,
    ) -> None:
        super().__init__(db_manager, tracking_service, current_day_provider)
        self.pm.switch_basket("P1")

        # Build UI
        from PyQt6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget

        self.table = QTableWidget(0, 5)
        self.table.setObjectName("panierTable")
        self.table.setHorizontalHeaderLabels(["Designation Produit", "PU", "Qte", "Total", ""])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.currentCellChanged.connect(self._on_selection_changed)
        vheader = self.table.verticalHeader()
        if vheader:
            vheader.setFixedWidth(30)
            vheader.setDefaultSectionSize(30)
        header = self.table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            for col in (1, 2, 3, 4):
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(1, 70)
            self.table.setColumnWidth(2, 90)
            self.table.setColumnWidth(3, 80)
            self.table.setColumnWidth(4, 40)

        controls = self._build_controls()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(controls)
        layout.addWidget(self.table, 1)

        self._refresh_buttons_style()
        self.refresh()

    # ==================== Controls ====================

    def _build_controls(self) -> QWidget:
        bar = QWidget()
        bar.setMinimumHeight(54)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(6)

        self.btn_mode_switch = QPushButton("Achats")
        self.btn_mode_switch.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.btn_mode_switch.setMinimumHeight(54)
        self.btn_mode_switch.clicked.connect(self.mode_switch_request.emit)

        self.btn_p1 = QPushButton("P1")
        self.btn_p1.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.btn_p1.setMinimumHeight(54)
        self.btn_p1.clicked.connect(lambda: self.switch_basket("P1"))

        self.btn_p2 = QPushButton("P2")
        self.btn_p2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.btn_p2.setMinimumHeight(54)
        self.btn_p2.clicked.connect(lambda: self.switch_basket("P2"))

        self.btn_np = QPushButton("N/P")
        self.btn_np.setObjectName("btn_np")
        self.btn_np.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.btn_np.setMinimumHeight(54)
        self.btn_np.clicked.connect(lambda: self.switch_basket("N/P"))

        self.btn_clear = QPushButton("Vider")
        self.btn_clear.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.btn_clear.setMinimumHeight(54)
        self.btn_clear.clicked.connect(self.clear_basket)
        self.btn_clear.setStyleSheet(
            "font-size: 14px; font-weight: 700; padding: 1px 3px;"
            " background-color: #2563eb; color: #eff6ff; border: 2px solid #93c5fd;"
            " border-radius: 6px;"
        )

        self.btn_encaisser = QPushButton("ENCAISSER\n0 Ar")
        self.btn_encaisser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.btn_encaisser.setMinimumHeight(54)
        self.btn_encaisser.clicked.connect(self.collect_active_basket)

        for w in (
            self.btn_mode_switch,
            self.btn_p1,
            self.btn_p2,
            self.btn_np,
            self.btn_clear,
            self.btn_encaisser,
        ):
            layout.addWidget(w)

        self._apply_controls_theme()
        return bar

    def _apply_controls_theme(self) -> None:
        accent = TOKENS["button_success"]
        border = "#14532d"
        bar = self.btn_mode_switch.parentWidget()
        if bar:
            bar.setStyleSheet(
                f"background-color: {TOKENS['bg_sidebar']};"
                f" border: 1px solid {border}; border-radius: 10px;"
            )
        self.btn_mode_switch.setStyleSheet(
            f"font-weight: 700; border: 2px solid {accent};"
            f" background-color: {TOKENS['panier_tab_bg']};"
            f" padding: 1px 3px; color: {TOKENS['text_primary']};"
        )

    # ==================== Table Population ====================

    def _populate_table(self, items: list[dict[str, Any]]) -> None:
        """Legacy method - uses batch version."""
        self._populate_table_batch(items)

    def _populate_table_batch(self, items: list[dict[str, Any]]) -> None:
        """Populate table using pre-allocated rows (index-based, no insertRow)."""
        assert self.table is not None
        for idx, ligne in enumerate(items):
            self._ensure_row_marker(self.table, idx)
            self._insert_vente_row(idx, ligne, is_brouillon=False)

    def _append_draft_row(self, draft: dict[str, Any]) -> None:
        """Legacy method - uses batch version."""
        row = self.table.rowCount() - 1 if self.table.rowCount() > 0 else 0
        self._append_draft_row_batch(draft, row)

    def _append_draft_row_batch(self, draft: dict[str, Any], row_index: int) -> None:
        """Append draft row using pre-allocated row at given index."""
        assert self.table is not None
        self._ensure_row_marker(self.table, row_index)
        self._insert_vente_row(row_index, draft, is_brouillon=True)

    def _insert_vente_row(self, row: int, ligne: dict[str, Any], is_brouillon: bool) -> None:
        """Insert vente row at given row index (uses pre-allocated row)."""
        assert self.table is not None
        pu = int(ligne.get("prix", 0))
        total = ligne_total(ligne)

        self.table.setItem(row, 0, QTableWidgetItem(str(ligne.get("nom", ""))))
        self.table.setItem(row, 1, QTableWidgetItem(format_grouped_int(pu)))
        self._render_qte_cell(row, int(ligne.get("qte", 1)), is_brouillon)
        self.table.setItem(row, 3, QTableWidgetItem(format_grouped_int(total)))

        if not is_brouillon:
            self._render_delete_cell(row, is_brouillon)
        self._apply_row_validation_style(self.table, row, validated=not is_brouillon)

    def _insert_row_at_index(self, row: int, ligne: dict[str, Any], is_brouillon: bool) -> None:
        """Insert row at pre-allocated index (delegate to _insert_vente_row)."""
        self._insert_vente_row(row, ligne, is_brouillon)

    def _render_qte_cell(self, row: int, qte: int, is_brouillon: bool) -> None:
        assert self.table is not None
        editor = self._build_qte_editor(
            qte,
            lambda: self._change_row_qty(row, -1, is_brouillon),
            lambda: self._change_row_qty(row, +1, is_brouillon),
        )
        if is_brouillon:
            editor.quantity_changed.connect(self._update_quantity_for_draft)
        else:
            editor.quantity_changed.connect(lambda q: self._update_quantity_for_row(row, q))
        self.table.setCellWidget(row, 2, editor)

    def _render_delete_cell(self, row: int, is_brouillon: bool) -> None:
        assert self.table is not None
        btn = self._create_delete_button(lambda: self._delete_row(row, is_brouillon))
        self.table.setCellWidget(row, 4, btn)

    def _delete_row(self, row: int, is_brouillon: bool) -> None:
        self._activate_row(row)
        self._remove_row(row, is_brouillon)

    # ==================== Total ====================

    def _compute_total(self, items: list[dict[str, Any]]) -> int:
        summary = PanierTransactionsService.compute_collection_summary(items)
        return int(summary.total)

    # ==================== Basket Switching ====================

    def switch_basket(self, nom: str) -> None:
        """Switch between P1/P2/N/P baskets."""
        self.pm.switch_basket(nom)
        self.drafts.clear_draft("vente")
        self._refresh_buttons_style()
        self.refresh()

    def _refresh_buttons_style(self) -> None:
        mapping = [("P1", self.btn_p1), ("P2", self.btn_p2), ("N/P", self.btn_np)]
        for nom, btn in mapping:
            if self.pm.actif == nom:
                style = PANIER_TAB_ACTIVE_BORDER_STYLE
            else:
                style = PANIER_TAB_INACTIVE_BORDER_STYLE
            base = PANIER_TAB_BASE_STYLE
            if nom == "N/P":
                base = base.replace(f"color: {TOKENS['panier_tab_text']};", "color: #fbbf24;")
            btn.setStyleSheet(f"{base} {style}")

    # ==================== Encaisser ====================

    def _update_action_button_state(self) -> None:
        has_items = len(self.pm.get_actif()) > 0
        any_items = any(len(v or []) > 0 for v in self.pm.paniers.values())
        can_encaisser = has_items and any_items
        self.btn_encaisser.setEnabled(can_encaisser)
        if can_encaisser:
            self.btn_encaisser.setStyleSheet(TOTAL_CAISSE_ENABLED_STYLE)
        else:
            self.btn_encaisser.setStyleSheet(TOTAL_CAISSE_DISABLED_STYLE)
        # Update basket button text with counts
        for nom, btn in [("P1", self.btn_p1), ("P2", self.btn_p2), ("N/P", self.btn_np)]:
            items = self.pm.paniers.get(nom, [])
            count = len(items)
            tot = sum(int(p.get("pv", 0)) * int(p.get("qte", 1)) for p in items)
            label = f"{count} produit" if count == 1 else f"{count} produits"
            btn.setText(f"{nom}\n{label}\n{format_grouped_int(tot)} Ar")
        # Update encaisser button text
        montant = sum(int(p.get("pv", 0)) * int(p.get("qte", 1)) for p in self.pm.get_actif())
        self.btn_encaisser.setText(f"ENCAISSER\n{format_grouped_int(montant)} Ar")

    def collect_active_basket(self) -> None:
        """Validate and collect payment for the active basket."""
        items = [normalize_ligne(p) for p in self.pm.get_actif()]
        if not items:
            return

        validated_items = []
        for item in items:
            produit_id = item.get("id")
            quantite = item.get("qte", 1)

            if not produit_id or quantite <= 0:
                logger.warning("Invalid product or quantity: id=%s, qte=%s", produit_id, quantite)
                continue

            if self.db_manager:
                try:
                    produit = self.db_manager.get_produit_by_id(produit_id)
                    if produit:
                        current_stock = int(produit.get("qte_stock", 0))
                        if quantite > current_stock:
                            logger.warning(
                                "Insufficient stock for %s: requested %s, available %s",
                                produit_id,
                                quantite,
                                current_stock,
                            )
                            QMessageBox.warning(
                                self,
                                "Stock insuffisant",
                                f"Stock insuffisant pour '{item.get('nom', 'Inconnu')}'.\n"
                                f"Demandé: {quantite}, Disponible: {current_stock}",
                            )
                            continue
                except Exception as e:
                    logger.error("Error checking stock for %s: %s", produit_id, e)

            validated_items.append(item)

        if not validated_items:
            logger.warning("No valid items to process in collect_active_basket")
            return

        summary = PanierTransactionsService.compute_collection_summary(validated_items)

        from ui.dialogs.encaissement_dialog import EncaissementDialog

        dialog = EncaissementDialog(self, total=summary.total, panier_name=self.pm.actif)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.dialog_closed.emit()

        day = self._target_business_day()
        PanierTransactionsService.apply_tracking_collection(
            day,
            validated_items,
            db_manager=self.db_manager,
            tracking_service=self.tracking_service,
        )

        if self.db_manager:
            for item in validated_items:
                produit_id = item.get("id")
                quantite = item.get("qte", 1)
                if produit_id and quantite:
                    try:
                        self.db_manager.decrement_stock(produit_id, quantite)
                    except Exception as e:
                        logger.error("Failed to decrement stock for %s: %s", produit_id, e)
                        QMessageBox.warning(
                            self,
                            "Erreur de mise à jour du stock",
                            f"Impossible de mettre à jour le stock pour "
                            f"'{item.get('nom', 'Inconnu')}'.\nErreur: {e}",
                        )

        heure = datetime.now().strftime(DATE_FORMAT_TIME)
        ventes_rows = PanierTransactionsService.build_sales_rows(
            validated_items, day=day, heure=heure
        )
        if ventes_rows:
            self.sales_day_recorded.emit(ventes_rows)

        self.pm.clear_active()
        self.drafts.clear_draft("vente")
        self.refresh()
        self._emit_transaction_signal("vente", int(summary.total))

    # ==================== Validation ====================

    def _compute_validation_enabled(self) -> bool:
        from controllers.panier_selection_controller import PanierSelectionController

        return PanierSelectionController.validation_enabled(
            mode="vente",
            has_brouillon=self.drafts.has_draft("vente"),
            has_achats_brouillon=False,
            panier_row_count=self.table.rowCount() if self.table else 0,
            panier_current_row=self.table.currentRow() if self.table else -1,
            facture_row_count=0,
            facture_current_row=-1,
        )

    # ==================== Add Product Override ====================

    def add_product(self, produit: dict[str, Any]) -> None:
        """Add product as vente draft."""
        validated = self._validate_product_data(produit)
        self.drafts.set_draft(normalize_ligne(validated), "vente")
        self.refresh()

    # ==================== Show/Hide ====================

    def showEvent(self, a0) -> None:
        """Refresh button styles when zone becomes visible."""
        super().showEvent(a0)
        self._refresh_buttons_style()
