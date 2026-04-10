"""Defilling widget showing product names in horizontal columns with scrolling."""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class DualLineScroller(QListWidget):
    """Scrolling widget that vertically scrolls product names with 2 visible lines."""

    def __init__(self, text_color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._paused = False
        self._product_count = 0
        self._scroll_timer = QTimer(self)
        self._scroll_speed = 1

        self.setFixedHeight(38)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setUniformItemSizes(True)
        self.setStyleSheet(
            f"QListWidget {{ background-color: transparent; border: none; color: {text_color}; "
            f"font-size: 12px; padding: 0px; }}"
            "QListWidget::item { background-color: transparent; padding: 1px 4px; border: none; }"
        )

        self._scroll_timer.timeout.connect(self._on_scroll_tick)

    def set_products(self, names: list[str]) -> int:
        """Set the product names to display. Returns the count."""
        self._scroll_timer.stop()
        self.clear()
        self._product_count = len(names)
        if not names:
            return 0

        display_list = names + names
        for name in display_list:
            item = QListWidgetItem(name)
            # Do not set foreground here; the stylesheet's color will apply
            self.addItem(item)

        scroll_bar = self.verticalScrollBar()
        if scroll_bar is not None:
            scroll_bar.setValue(0)

            max_scroll = scroll_bar.maximum()
            if max_scroll > 0:
                # < 5 produits: 5s pour parcourir, >= 5 produits: 3s pour parcourir
                total_time = 5000 if len(names) < 5 else 3000
                interval = (total_time * 3) // max_scroll
                self._scroll_timer.setInterval(max(20, interval))
                self._scroll_timer.start()

        return self._product_count

    def enterEvent(self, event: QEvent) -> None:
        self._paused = True
        self._scroll_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._paused = False
        scroll_bar = self.verticalScrollBar()
        if scroll_bar is not None and self._product_count > 0 and scroll_bar.maximum() > 0:
            self._scroll_timer.start()
        super().leaveEvent(event)

    def _on_scroll_tick(self) -> None:
        """Handle each scroll tick."""
        if self._paused:
            return

        scroll_bar = self.verticalScrollBar()
        if scroll_bar is None:
            return

        current = scroll_bar.value()
        max_val = scroll_bar.maximum()

        if current >= max_val:
            scroll_bar.setValue(0)
        else:
            scroll_bar.setValue(current + 1)


class DefillingWidget(QWidget):
    """Horizontal widget showing categorized products with vertical scrolling."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._dlv_names: list[str] = []
        self._remove_names: list[str] = []
        self._dlv_qty = 0
        self._remove_qty = 0

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 4, 8, 4)
        main_layout.setSpacing(12)

        self._dlv_column = self._create_column("A surveiller (0)", "#f87171", "#450a0a")
        self._remove_column = self._create_column("A enlever (0)", "#a78bfa", "#2e1065")

        main_layout.addWidget(self._dlv_column)
        main_layout.addWidget(self._remove_column)

    def _create_column(self, title: str, text_color: str, bg_color: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {bg_color}; border-radius: 6px; border: none;")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {text_color}; font-size: 12px; font-weight: bold; "
            "background-color: transparent; border: none; padding: 2px;"
        )
        layout.addWidget(title_label)

        scroller = DualLineScroller(text_color)
        layout.addWidget(scroller)

        # Store references as properties of the frame
        frame.setProperty("_title_label", title_label)
        frame.setProperty("_scroller", scroller)
        return frame

    def update_ticker(
        self,
        promo: list[dict],
        near_dlv: list[dict],
        to_remove: list[dict],
    ) -> None:
        """Update the widget with product data from each category."""
        # Ignore promo data as requested
        self._dlv_names = [p["nom"] for p in near_dlv]
        self._remove_names = [p["nom"] for p in to_remove]

        self._dlv_qty = sum(
            p.get("stock_boutique", 0) + p.get("stock_reserve", 0) for p in near_dlv
        )
        self._remove_qty = sum(
            p.get("stock_boutique", 0) + p.get("stock_reserve", 0) for p in to_remove
        )

        # Update column titles using property() to get the labels
        dlv_title = self._dlv_column.property("_title_label")
        remove_title = self._remove_column.property("_title_label")
        if dlv_title is not None:
            dlv_title.setText(f"A surveiller ({self._dlv_qty})")
        if remove_title is not None:
            remove_title.setText(f"A enlever ({self._remove_qty})")

        # Update scrollers using property() to get the scroller
        dlv_scroller = self._dlv_column.property("_scroller")
        remove_scroller = self._remove_column.property("_scroller")
        if dlv_scroller is not None:
            dlv_scroller.set_products(self._dlv_names)
        if remove_scroller is not None:
            remove_scroller.set_products(self._remove_names)

        tooltip_parts = []
        if self._dlv_names:
            tooltip_parts.append(f"DLV: {', '.join(self._dlv_names[:5])}")
        if self._remove_names:
            tooltip_parts.append(f"Retirer: {', '.join(self._remove_names[:5])}")
        self.setToolTip("\n".join(tooltip_parts) if tooltip_parts else "Aucun produit")
