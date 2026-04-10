"""Composants UI reutilisables."""

from .base_table import BaseTableMixin
from .calculator import CalculatorWidget
from .cash_counter_footer import CashCounterFooter
from .defilling_ticker_widget import DefillingWidget
from .header_info_widget import HeaderInfoWidget
from .mouvements_actions_panel import MouvementsActionsPanel
from .mouvements_history_panel import MouvementsHistoryPanel
from .pos_buttons import ActionButton, NavButton, POSButton
from .pos_tables import (
    POSTable,
    configure_table_for_basket,
    configure_table_for_products,
    configure_table_for_report,
    get_table_style,
)
from .product_info_panel import ProduitInfoPanel
from .products_table import ProduitsTable
from .quantity_editor import QuantityEditor
from .reports_widget import ReportsWidget

# from .sf_table_widget import SFTableWidget  # Disabled

__all__ = [
    "ActionButton",
    "BaseTableMixin",
    "CalculatorWidget",
    "CashCounterFooter",
    "DefillingWidget",
    "HeaderInfoWidget",
    "MouvementsActionsPanel",
    "MouvementsHistoryPanel",
    "NavButton",
    "POSButton",
    "POSTable",
    "ProduitInfoPanel",
    "ProduitsTable",
    "QuantityEditor",
    "ReportsWidget",
    # "SFTableWidget",  # Disabled
    "configure_table_for_basket",
    "configure_table_for_products",
    "configure_table_for_report",
    "get_table_style",
]
