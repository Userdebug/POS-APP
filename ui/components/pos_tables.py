"""Standardized table styling for the POS application.

This module provides factory functions for creating consistently styled
tables across the entire application, replacing inline style definitions.
"""

from __future__ import annotations

from typing import Literal

from PyQt6.QtWidgets import QAbstractItemView, QTableWidget

from styles.design_tokens import TOKENS

TableVariant = Literal["default", "report", "products", "basket"]


def get_table_style(variant: TableVariant = "default") -> str:
    """Get table stylesheet for the specified variant.

    Args:
        variant: Table style variant.
            - 'default': Standard transparent table for main UI
            - 'report': Styled table for reports/dialogs
            - 'products': Product listing table
            - 'basket': Cart/basket table

    Returns:
        CSS stylesheet string for QTableWidget.
    """
    base_style = f"""
        QTableWidget {{
            background-color: transparent;
            border: none;
            gridline-color: {TOKENS['border_primary']};
            }}
            QTableWidget::item {{
                padding: 4px 8px;
            }}
            QTableWidget::item:selected {{
            background-color: {TOKENS['bg_button_disabled']};
        }}
        QHeaderView::section {{
            background-color: transparent;
            color: {TOKENS['text_header']};
            border: none;
            padding: 6px 8px;
            font-weight: 700;
        }}
        QTableCornerButton::section {{
            background-color: transparent;
            border: none;
        }}
    """

    if variant == "report":
        return f"""
            QTableWidget {{
                background-color: {TOKENS['bg_panel']};
                alternate-background-color: {TOKENS['bg_card']};
                color: {TOKENS['text_default']};
                border: 1px solid {TOKENS['border_input']};
                border-radius: 8px;
                gridline-color: {TOKENS['border_primary']};
            }}
            QTableWidget::item {{
                padding: 8px 12px;
            }}
            QTableWidget::item:selected {{
                background-color: {TOKENS['bg_button_disabled']};
            }}
            QHeaderView::section {{
                background-color: {TOKENS['bg_card']};
                color: {TOKENS['text_primary']};
                border: none;
                padding: 10px 12px;
                font-weight: 700;
                font-size: 13px;
            }}
            QTableCornerButton::section {{
                background-color: {TOKENS['bg_card']};
                border: none;
            }}
        """

    elif variant == "products":
        return f"""
            QTableWidget {{
                background-color: {TOKENS['bg_panel']};
                color: {TOKENS['text_default']};
                border: 1px solid {TOKENS['border_input']};
                border-radius: 8px;
                gridline-color: {TOKENS['border_primary']};
            }}
            QTableWidget::item {{
                padding: 8px 12px;
            }}
            QTableWidget::item:selected {{
                background-color: {TOKENS['bg_button_disabled']};
            }}
            QHeaderView::section {{
                background-color: {TOKENS['bg_card']};
                color: {TOKENS['text_primary']};
                border: none;
                padding: 10px 12px;
                font-weight: 700;
                font-size: 12px;
            }}
            QTableCornerButton::section {{
                background-color: {TOKENS['bg_card']};
                border: none;
            }}
        """

    elif variant == "basket":
        return f"""
            QTableWidget {{
                background-color: {TOKENS['bg_panel']};
                alternate-background-color: {TOKENS['bg_card']};
                color: {TOKENS['text_default']};
                border: 1px solid {TOKENS['border_input']};
                border-radius: 8px;
                gridline-color: {TOKENS['border_primary']};
            }}
            QTableWidget::item {{
                padding: 6px 10px;
            }}
            QTableWidget::item:selected {{
                background-color: {TOKENS['bg_button_disabled']};
            }}
            QHeaderView::section {{
                background-color: {TOKENS['bg_card']};
                color: {TOKENS['text_primary']};
                border: none;
                padding: 8px 10px;
                font-weight: 700;
                font-size: 12px;
            }}
            QTableCornerButton::section {{
                background-color: {TOKENS['bg_card']};
                border: none;
            }}
        """

    return base_style


class POSTable(QTableWidget):
    """Standardized table widget for the POS application.

    Provides pre-configured styling based on variant.
    """

    def __init__(
        self,
        rows: int = 0,
        columns: int = 0,
        variant: TableVariant = "default",
        parent=None,
    ):
        """Initialize POS table with variant styling.

        Args:
            rows: Initial number of rows
            columns: Initial number of columns
            variant: Table style variant
            parent: Parent widget
        """
        super().__init__(rows, columns, parent)
        self.variant = variant
        self._apply_default_config()
        self._apply_style()

    def _apply_default_config(self) -> None:
        """Apply default table configuration."""
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)

    def _apply_style(self) -> None:
        """Apply the variant-specific stylesheet."""
        self.setStyleSheet(get_table_style(self.variant))

    def set_variant(self, variant: TableVariant) -> None:
        """Change the table variant at runtime."""
        self.variant = variant
        self._apply_style()


def configure_table_for_products(table: QTableWidget) -> None:
    """Configure a table widget for product display.

    Args:
        table: QTableWidget to configure
    """
    table.setStyleSheet(get_table_style("products"))
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setWordWrap(True)


def configure_table_for_basket(table: QTableWidget) -> None:
    """Configure a table widget for basket display.

    Args:
        table: QTableWidget to configure
    """
    table.setStyleSheet(get_table_style("basket"))
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)


def configure_table_for_report(table: QTableWidget) -> None:
    """Configure a table widget for report display.

    Args:
        table: QTableWidget to configure
    """
    table.setStyleSheet(get_table_style("report"))
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
