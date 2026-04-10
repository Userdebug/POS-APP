from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
)

from core.constants import BILLETAGE_DENOMINATIONS
from core.formatters import format_grouped_int
from services.cash_counter_service import CashCounterService
from ui.components.quantity_editor import QuantityEditor


class CashCounterFooter(QFrame):
    """Widget de comptage des coupures de billets."""

    billetage_updated = pyqtSignal(int)

    def __init__(
        self,
        cash_counter: CashCounterService | None = None,
        denominations: list[int] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("FooterFrame")
        self.cash_counter = cash_counter or CashCounterService()
        # Use provided denominations or fall back to default for backward compatibility
        self.coupures = (
            denominations if denominations is not None else list(BILLETAGE_DENOMINATIONS)
        )
        self.editors_coupures: dict[int, QuantityEditor] = {}
        self.subtotals_coupures: dict[int, QLabel] = {}
        self._build_ui()

    def _build_ui(self):
        # Use a table-like layout with 3 columns: Billets | Quantité | Total
        grid = QGridLayout()
        grid.setSpacing(2)

        grid.setColumnStretch(0, 0)  # Billets column - fixed
        grid.setColumnStretch(1, 1)  # Quantité column - expandable
        grid.setColumnStretch(2, 0)  # Total column - fixed

        # Data rows for each coupure - 3 columns
        for row, val in enumerate(self.coupures):
            # Billets column
            lbl_val = QLabel(format_grouped_int(val))
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_val.setStyleSheet("font-size: 11px;")
            grid.addWidget(lbl_val, row + 1, 0)

            # Quantité column - use new QuantityEditor with min_val and max_val
            editor = QuantityEditor(
                quantity=0,
                min_quantity=0,
                on_minus=None,
                on_plus=None,
                parent=None,
                min_val=0,
                max_val=9999,
            )
            editor.quantity_changed.connect(self.recalculate)
            # Reduce font size to match context (11px like other columns)
            editor.setStyleSheet("font-size: 10px;")
            grid.addWidget(editor, row + 1, 1)
            self.editors_coupures[val] = editor

            # Total column
            lbl_sub = QLabel("0")
            lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_sub.setStyleSheet("color: #a0aec0; font-size: 11px;")
            lbl_sub.setFixedWidth(70)
            lbl_sub.setFixedHeight(20)
            lbl_sub.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            grid.addWidget(lbl_sub, row + 1, 2)
            self.subtotals_coupures[val] = lbl_sub

        # TOTAL row (last row)
        total_row = len(self.coupures) + 1

        # Separator line - spans 2 columns now
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        grid.addWidget(separator, total_row, 0, 1, 2)

        # TOTAL label in column 0
        lbl_total_title = QLabel("TOTAL")
        lbl_total_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_total_title.setStyleSheet("font-weight: bold; font-size: 12px;")
        grid.addWidget(lbl_total_title, total_row + 1, 0)

        # Clear button in column 1
        btn_clear = QPushButton("C")
        btn_clear.setFixedSize(24, 24)
        btn_clear.setStyleSheet(
            "QPushButton { font-weight: bold; font-size: 11px; border-radius: 12px; "
            "background-color: #e53e3e; color: white; }"
            "QPushButton:hover { background-color: #c53030; }"
        )
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.clicked.connect(self.reset_inputs)
        grid.addWidget(btn_clear, total_row + 1, 1, Qt.AlignmentFlag.AlignCenter)

        # TOTAL value in column 2 (aligned right)
        self.lbl_total_billets = QLabel("0")
        self.lbl_total_billets.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.lbl_total_billets.setStyleSheet("font-weight: bold; font-size: 12px;")
        self.lbl_total_billets.setFixedWidth(70)
        self.lbl_total_billets.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        grid.addWidget(self.lbl_total_billets, total_row + 1, 2)

        # Add grid to main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 5, 5)
        main_layout.setSpacing(10)
        main_layout.addLayout(grid, 1)

    def reset_inputs(self):
        """Reset tous les editors à 0."""
        for editor in self.editors_coupures.values():
            editor.set_quantity(0)

    def recalculate(self):
        quantities = {val: self.editors_coupures[val].quantity() for val in self.coupures}
        result = self.cash_counter.compute(
            coupures=self.coupures,
            quantities=quantities,
        )
        for val in self.coupures:
            self.subtotals_coupures[val].setText(format_grouped_int(result.subtotals.get(val, 0)))
        self.lbl_total_billets.setText(format_grouped_int(result.total_billets))
        # Emit signal for external listeners
        self.billetage_updated.emit(result.total_billets)

    def get_total(self) -> int:
        """Retourne le total actuel des billets."""
        return self.cash_counter.compute(
            coupures=self.coupures,
            quantities={val: self.editors_coupures[val].quantity() for val in self.coupures},
        ).total_billets

    def reset(self) -> None:
        """Reset tous les editors à 0."""
        self.reset_inputs()
