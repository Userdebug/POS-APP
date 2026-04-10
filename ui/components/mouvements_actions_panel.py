"""Actions de mouvements de stock."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QGroupBox, QHBoxLayout, QLabel, QPushButton

from ui.components.quantity_editor import QuantityEditor


class MouvementsActionsPanel(QGroupBox):
    """Panel des actions de mouvements sur une seule ligne."""

    action_declenchee = pyqtSignal(tuple)

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Actions Produit")
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #2a3142;
                border-radius: 10px;
                margin-top: 12px;
                padding: 8px;
                font-weight: 700;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #e2e8f0;
            }
            """)

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 10, 8, 8)
        root.setSpacing(8)
        self._all_buttons: list[QPushButton] = []

        qty_tag = QLabel("Qte")
        qty_tag.setStyleSheet("color:#94a3b8; font-size:11px; font-weight:700; padding:0 2px;")
        root.addWidget(qty_tag)

        # Use QuantityEditor for quantity input (allows negative values for stock movements)
        self._qty_editor = QuantityEditor(
            quantity=1,
            min_quantity=None,  # Allow negative values for stock reductions
            on_minus=None,
            on_plus=None,
            parent=None,
            min_val=-999,  # Allow negative quantities
            max_val=999,
        )
        self._qty_editor.setFixedWidth(100)
        self._qty_editor.setMinimumHeight(34)
        root.addWidget(self._qty_editor)

        self._add_separator(root)
        self._add_group(
            root, "Mouvements", [("Res->Btq", "#3b82f6", "RB"), ("Btq->Res", "#f59e0b", "BR")]
        )
        self._add_separator(root)
        self._add_group(
            root, "Corrections", [("Corr Btq", "#10b981", "EB"), ("Corr Res", "#22c55e", "ER")]
        )
        self._add_separator(root)
        self._add_group(
            root, "Enlever", [("DLV", "#ef4444", "ENV_DLV"), ("Abime", "#dc2626", "ENV_ABIME")]
        )
        root.addStretch(1)

        self.set_actions_enabled(False)

    def _add_group(self, layout: QHBoxLayout, title: str, buttons: list[tuple[str, str, str]]):
        tag = QLabel(title)
        tag.setStyleSheet("color:#94a3b8; font-size:11px; font-weight:700; padding:0 2px;")
        layout.addWidget(tag)
        for text, color, action in buttons:
            btn = self._create_btn(text, color)
            btn.clicked.connect(
                lambda _checked=False, a=action: self.action_declenchee.emit(
                    (a, str(self._qty_editor.quantity()))
                )
            )
            layout.addWidget(btn)
            self._all_buttons.append(btn)

    def _add_separator(self, layout: QHBoxLayout):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color:#334155;")
        layout.addWidget(sep)

    def _create_btn(self, text: str, color: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setMinimumHeight(34)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #0f172a;
                border: 1px solid {color};
                color: {color};
                font-weight: 700;
                border-radius: 7px;
                padding: 4px 10px;
            }}
            QPushButton:hover {{ background-color: {color}; color: #0b1220; }}
            QPushButton:disabled {{
                border-color: #475569;
                color: #64748b;
                background-color: #111827;
            }}
            """)
        return btn

    def get_quantite(self) -> int:
        """Retourne la quantité actuelle."""
        return self._qty_editor.quantity()

    def set_actions_enabled(self, enabled: bool) -> None:
        for btn in self._all_buttons:
            btn.setEnabled(enabled)
        self._qty_editor.setEnabled(enabled)
