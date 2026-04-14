"""BaseBasketZone — shared mechanics for ZoneVente and ZoneAchat.

Provides draft management, table row helpers, validation state,
and the core refresh loop. Each concrete zone implements abstract
methods for its own table layout and controls.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QIcon
from PyQt6.QtWidgets import (
    QMessageBox,
    QPushButton,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from controllers.panier_selection_controller import PanierSelectionController
from core.constants import DATE_FORMAT_DAY
from ui.components.quantity_editor import QuantityEditor
from ui.dialogs.add_produit_dialog import AddProduitDialog
from viewmodels.panier_viewmodel import BasketManager

from .basket_models import normalize_ligne
from .draft_manager import DraftManager

logger = logging.getLogger(__name__)


class BaseBasketZone(QWidget):
    """Base class for mode-specific basket widgets.

    Signals:
        transaction_finalisee: Emitted after a successful transaction (mode, total).
        validation_state_changed: Emitted when the validation button state changes.
        nouveau_produit_enregistre: Emitted when a new product is saved to DB.
        mode_switch_request: Emitted when the user clicks the mode-switch button.
    """

    transaction_finalisee = pyqtSignal(str, int)
    validation_state_changed = pyqtSignal(bool)
    nouveau_produit_enregistre = pyqtSignal(dict)
    mode_switch_request = pyqtSignal()

    # Subclasses must set: mode_key, _draft_key

    def __init__(
        self,
        db_manager: Any | None = None,
        tracking_service: Any | None = None,
        current_day_provider: Callable[[], str] | None = None,
    ) -> None:
        super().__init__()
        self.db_manager = db_manager
        self.tracking_service = tracking_service
        self.current_day_provider = current_day_provider

        self.pm = BasketManager()
        self.pm.set_mode(self.mode_key)
        self.drafts = DraftManager()

        self._refresh_lock = False
        self._active_row = -1
        self._trash_icon: QIcon | None = None

        # Row marker colors
        self._active_row_fg = QColor("#ffffff")
        self._active_row_bg = QColor("#f59e0b")
        self._validated_row_fg = QColor("#ffffff")
        self._validated_row_bg = QColor("#22c55e")
        self._inactive_row_fg = QColor("#64748b")

        # Table reference — set by subclass in _build_table()
        self.table: QTableWidget | None = None

    # ==================== Abstract Interface ====================

    @property
    def mode_key(self) -> str:
        """Return 'vente' or 'achat'."""
        raise NotImplementedError

    @property
    def _draft_key(self) -> str:
        """Return the draft key ('vente' or 'achat')."""
        raise NotImplementedError

    def _build_table(self) -> None:
        """Create self.table with mode-specific columns."""
        raise NotImplementedError

    def _build_controls(self) -> QWidget:
        """Create and return the controls widget for this zone."""
        raise NotImplementedError

    def _populate_table(self, items: list[dict[str, Any]]) -> None:
        """Insert validated items into the table."""
        raise NotImplementedError

    def _append_draft_row(self, draft: dict[str, Any]) -> None:
        """Append the brouillon (draft) row to the table."""
        raise NotImplementedError

    def _compute_total(self, items: list[dict[str, Any]]) -> int:
        """Compute the display total for the given items."""
        raise NotImplementedError

    def _compute_validation_enabled(self) -> bool:
        """Return whether the Valider button should be enabled."""
        raise NotImplementedError

    def _update_action_button_state(self) -> None:
        """Update the enable/disable state of the action button (Encaisser/Payer)."""
        raise NotImplementedError

    # ==================== Refresh ====================

    def refresh(self) -> None:
        """Clear and repopulate the table from current basket data."""
        if self._refresh_lock:
            return
        self._refresh_lock = True
        try:
            previous_row = self._active_row
            items = [normalize_ligne(p) for p in self.pm.get_actif()]
            draft = self.drafts.get_draft(self._draft_key)
            has_draft = draft is not None

            if self.table:
                # Block signals to prevent layout thrashing during population
                self.table.blockSignals(True)
                self.table.setUpdatesEnabled(False)
            try:
                if self.table:
                    # Pre-allocate all rows at once - much faster than row-by-row insertion
                    item_count = len(items)
                    total_rows = item_count + (1 if has_draft else 0)
                    self.table.setRowCount(total_rows)

                # Populate items using pre-allocated rows (index-based, no insertRow)
                self._populate_table_batch(items)

                # Append draft row using pre-allocated row
                if draft and self.table:
                    self._append_draft_row_batch(draft, len(items))

                # Restore selection
                if self.table:
                    has_brouillon = self.drafts.has_draft(self._draft_key)
                    target = PanierSelectionController.refresh_basket_target(
                        row_count=self.table.rowCount(),
                        previous_active_row=previous_row,
                        has_brouillon=has_brouillon,
                    )
                    if target is not None:
                        self.table.setCurrentCell(target, 0)
                    else:
                        self._active_row = -1

                self._update_action_button_state()
                self._emit_validation_state()
            finally:
                if self.table:
                    self.table.blockSignals(False)
                    self.table.setUpdatesEnabled(True)
                    viewport = self.table.viewport()
                    if viewport is not None:
                        viewport.update()
        except Exception:
            logger.exception("Error during refresh")
            raise
        finally:
            self._refresh_lock = False

    def _populate_table_batch(self, items: list[dict[str, Any]]) -> None:
        """Populate table using pre-allocated rows (index-based, no insertRow)."""
        for idx, ligne in enumerate(items):
            self._ensure_row_marker(self.table, idx)
            self._insert_row_at_index(idx, ligne, is_brouillon=False)

    def _append_draft_row_batch(self, draft: dict[str, Any], row_index: int) -> None:
        """Append draft row using pre-allocated row at given index."""
        self._ensure_row_marker(self.table, row_index)
        self._insert_row_at_index(row_index, draft, is_brouillon=True)

    def _insert_row_at_index(self, row: int, ligne: dict[str, Any], is_brouillon: bool) -> None:
        """Insert row data at pre-allocated row index. Subclass implements specifics."""
        raise NotImplementedError

    # ==================== Validation ====================

    def validate_current_line(self) -> dict | None:
        """Validate the current draft line and add it to the basket.

        Returns:
            The validated item dict, or None if no draft exists.
        """
        draft = self.drafts.get_draft(self._draft_key)
        if not draft:
            return None

        if self.mode_key == "vente":
            is_valid, error_msg = self._check_stock_available(draft)
            if not is_valid:
                QMessageBox.warning(self, "Attention", error_msg)
                return None

        final_item = dict(draft)
        final_item["type"] = self.mode_key

        self.pm.add(final_item)
        self.drafts.clear_draft(self._draft_key)
        self.refresh()
        return final_item

    # ==================== Product Management ====================

    def add_product(self, produit: dict[str, Any]) -> None:
        """Add a product as a draft line (subclass may override for mode-specific prep)."""
        validated = self._validate_product_data(produit)
        self.drafts.set_draft(normalize_ligne(validated), self._draft_key)
        self.refresh()

    @staticmethod
    def _validate_product_data(produit: dict[str, Any]) -> dict[str, Any]:
        data = dict(produit)
        data.setdefault("nom", "")
        data.setdefault("prix", 0)
        data.setdefault("qte", 1)
        data["qte"] = max(1, int(data.get("qte", 1)))
        return data

    # ==================== Stock Validation ====================

    def _check_stock_available(self, ligne: dict[str, Any]) -> tuple[bool, str]:
        """Check if the requested quantity is available in stock."""
        from core.utils import validate_quantity_against_stock

        produit_id = ligne.get("id")
        requested_qte = int(ligne.get("qte", 1))

        if not produit_id or requested_qte <= 0:
            return True, ""
        if not self.db_manager:
            return True, ""

        try:
            produit = self.db_manager.get_produit_by_id(produit_id)
            if not produit:
                return True, ""
            current_stock = int(produit.get("qte_stock", 0))
            return validate_quantity_against_stock(ligne, current_stock)
        except Exception as e:
            logger.error("Error checking stock: %s", e)
            return True, ""

    # ==================== Quantity ====================

    def appliquer_quantite(self, quantite: int) -> None:
        """Apply a quantity from the calculator to the draft or selected row."""
        qte = int(quantite)
        if qte <= 0:
            return

        draft = self.drafts.get_draft(self._draft_key)
        if draft is not None:
            draft["qte"] = qte
            self.refresh()
            return

        if self.table:
            row = self.table.currentRow()
            items = self.pm.get_actif()
            if 0 <= row < len(items):
                items[row]["qte"] = qte
                self.refresh()

    def _change_row_qty(self, row: int, delta: int, is_brouillon: bool) -> None:
        """Change quantity by delta for the given row."""
        if is_brouillon:
            draft_line = self.drafts.get_draft(self._draft_key)
            if draft_line is None:
                return
            current = int(draft_line.get("qte", 1))
            draft_line["qte"] = max(1, current + int(delta))
            self.refresh()
            return

        items = self.pm.get_actif()
        if 0 <= row < len(items):
            current = int(items[row].get("qte", 1))
            items[row]["qte"] = max(1, current + int(delta))
            self.refresh()

    def _update_quantity_for_draft(self, q: int) -> None:
        """Update quantity for the current draft."""
        draft_line = self.drafts.get_draft(self._draft_key)
        if draft_line is not None:
            draft_line["qte"] = max(1, int(q))

    def _update_quantity_for_row(self, row: int, q: int) -> None:
        """Update quantity for the specified row."""
        items = self.pm.get_actif()
        if 0 <= row < len(items):
            items[row]["qte"] = max(1, int(q))
            # Refresh display, line total and action button state
            self.refresh()
            self._update_action_button_state()

    # ==================== Quantity Updates ====================

    def _activate_row(self, row: int) -> None:
        if self.table and 0 <= row < self.table.rowCount():
            self.table.setCurrentCell(row, 0)

    def _remove_row(self, row: int, is_brouillon: bool) -> None:
        if is_brouillon:
            self.drafts.clear_draft(self._draft_key)
            self.refresh()
            return
        items = self.pm.get_actif()
        if 0 <= row < len(items):
            items.pop(row)
        self.refresh()

    def clear_basket(self) -> None:
        """Clear the active basket and all drafts."""
        self.pm.clear_active()
        self.drafts.clear_all()
        self.refresh()

    # ==================== Row Markers ====================

    def _ensure_row_marker(self, table: QTableWidget, row: int) -> QTableWidgetItem:
        header_item = table.verticalHeaderItem(row)
        if header_item is None:
            header_item = QTableWidgetItem()
            header_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setVerticalHeaderItem(row, header_item)
        if not header_item.text():
            header_item.setText("·")
        return header_item

    def _set_row_marker_active(self, table: QTableWidget, row: int, active: bool) -> None:
        if not (0 <= row < table.rowCount()):
            return
        header_item = self._ensure_row_marker(table, row)
        font = header_item.font()
        is_validated = header_item.text().isdigit()

        if active:
            if is_validated:
                header_item.setForeground(QBrush(self._active_row_fg))
                header_item.setBackground(QBrush(self._validated_row_bg))
            else:
                header_item.setForeground(QBrush(self._active_row_fg))
                header_item.setBackground(QBrush(self._active_row_bg))
                header_item.setText("●")
            font.setBold(True)
        else:
            if is_validated:
                header_item.setForeground(QBrush(self._validated_row_fg))
                header_item.setBackground(QBrush(self._validated_row_bg))
            else:
                header_item.setForeground(QBrush(self._inactive_row_fg))
                header_item.setBackground(QBrush(QColor("#1f2937")))
                header_item.setText("·")
            font.setBold(False)
        header_item.setFont(font)

    def _apply_row_validation_style(self, table: QTableWidget, row: int, validated: bool) -> None:
        if not validated:
            return
        header_item = self._ensure_row_marker(table, row)
        header_item.setText(str(row + 1))
        header_item.setForeground(QBrush(self._validated_row_fg))
        header_item.setBackground(QBrush(self._validated_row_bg))

    # ==================== Widget Factories ====================

    def _create_delete_button(self, callback: Callable[[], None]) -> QPushButton:
        btn = QPushButton()
        trash_icon = self._get_red_trash_icon()
        if trash_icon is not None:
            btn.setIcon(trash_icon)
        btn.setStyleSheet("color:#c62828;")
        btn.setToolTip("Supprimer la ligne")
        btn.clicked.connect(callback)
        return btn

    def _build_qte_editor(self, qte: int, on_minus: Callable, on_plus: Callable) -> QuantityEditor:
        return QuantityEditor(
            quantity=max(1, qte),
            min_quantity=1,
            on_minus=on_minus,
            on_plus=on_plus,
            parent=None,
            min_val=1,
        )

    def _get_red_trash_icon(self) -> QIcon | None:
        if self._trash_icon is not None:
            return self._trash_icon
        style = self.style()
        if style is None:
            return None
        base_icon = style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
        pixmap = base_icon.pixmap(16, 16)
        if pixmap.isNull():
            return base_icon
        from PyQt6.QtGui import QPainter as QP

        painter = QP(pixmap)
        painter.setCompositionMode(QP.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor("#c62828"))
        painter.end()
        self._trash_icon = QIcon(pixmap)
        return self._trash_icon

    # ==================== Business Day ====================

    def _target_business_day(self) -> str:
        if callable(self.current_day_provider):
            day = str(self.current_day_provider() or "").strip()
            if day:
                return day
        return datetime.now().strftime(DATE_FORMAT_DAY)

    # ==================== Signal Helpers ====================

    def _emit_validation_state(self) -> None:
        self.validation_state_changed.emit(self._compute_validation_enabled())

    def current_validation_enabled(self) -> bool:
        return self._compute_validation_enabled()

    def _emit_transaction_signal(self, mode: str, total: int) -> None:
        self.transaction_finalisee.emit(mode, int(total))

    # ==================== Product Dialog ====================

    def _show_add_produit_dialog(self) -> None:
        categories: list[tuple[int, str]] = []
        try:
            if self.db_manager:
                with self.db_manager._connect() as conn:
                    rows = conn.execute(
                        "SELECT id, nom FROM categories WHERE parent_id IS NOT NULL ORDER BY nom ASC"
                    ).fetchall()
                    categories = [(row[0], row[1]) for row in rows]
        except Exception as e:
            logger.warning("Could not load categories: %s", e)

        dialog = AddProduitDialog(self, categories=categories)
        if dialog.exec():
            produit_data = dialog.get_produit()
            try:
                if self.db_manager:
                    self.db_manager.upsert_products([produit_data])
                    self.nouveau_produit_enregistre.emit(produit_data)
            except Exception as e:
                logger.error("Failed to save product: %s", e)
                QMessageBox.critical(self, "Erreur", f"Impossible d'enregistrer le produit: {e}")

    # ==================== Selection ====================

    def _on_selection_changed(
        self, current_row: int, _current_col: int, previous_row: int, _previous_col: int
    ) -> None:
        if self.table:
            self._set_row_marker_active(self.table, previous_row, False)
            self._set_row_marker_active(self.table, current_row, True)
        self._active_row = current_row
        self._emit_validation_state()
