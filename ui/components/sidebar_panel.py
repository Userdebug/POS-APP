from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
)

from ui.components.pos_buttons import NavButton


class SidebarPanel(QFrame):
    produits_clicked = pyqtSignal()
    depenses_clicked = pyqtSignal()
    nfr_clicked = pyqtSignal()
    sf_clicked = pyqtSignal()
    suivi_clicked = pyqtSignal()
    parametres_clicked = pyqtSignal()
    coffre_clicked = pyqtSignal()
    admin_clicked = pyqtSignal()
    cloture_clicked = pyqtSignal()
    achats_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedWidth(150)
        self._nav_buttons: dict[str, NavButton] = {}
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 20, 8, 16)
        main_layout.setSpacing(10)

        # Logo section
        logo = QLabel("GCN")
        logo.setObjectName("AppTitle")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(logo)
        main_layout.addSpacing(10)

        # Nav buttons container - centered
        nav_layout = QVBoxLayout()
        nav_layout.setSpacing(8)
        nav_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for label in ["Produits", "Depenses", "Achats"]:
            btn = NavButton(label)
            nav_layout.addWidget(btn)
            self._nav_buttons[label] = btn

        self._nav_buttons["Produits"].clicked.connect(self.produits_clicked.emit)
        self._nav_buttons["Depenses"].clicked.connect(self.depenses_clicked.emit)
        self._nav_buttons["Achats"].clicked.connect(self.achats_clicked.emit)

        # Admin section container with visual grouping
        admin_container = QFrame()
        admin_container.setObjectName("AdminGroup")
        admin_container.setStyleSheet("""
            QFrame#AdminGroup {
                border: 1px dotted #6b7280;
                border-radius: 8px;
                padding: 4px;
                margin-top: 8px;
            }
        """)
        admin_layout = QVBoxLayout(admin_container)
        admin_layout.setSpacing(8)
        admin_layout.setContentsMargins(8, 12, 8, 8)

        # Admin button (to unlock disabled buttons)
        self.btn_admin = NavButton("Admin")
        self.btn_admin.setObjectName("AdminButton")
        admin_style = """
            QPushButton {
                background-color: #7c3aed;
                color: white;
                border: none;
                padding: 8px 12px;
                font-weight: bold;
                font-size: 13px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #8b5cf6;
            }
        """
        self.btn_admin.setStyleSheet(admin_style)
        self.btn_admin.clicked.connect(self.admin_clicked.emit)
        admin_layout.addWidget(self.btn_admin)

        # Disabled buttons (require admin)
        for label in ["NFR", "SF", "SUIVI", "Parametres"]:
            btn = NavButton(label)
            admin_layout.addWidget(btn)
            self._nav_buttons[label] = btn

        self._nav_buttons["NFR"].clicked.connect(self.nfr_clicked.emit)
        self._nav_buttons["SF"].clicked.connect(self.sf_clicked.emit)
        self._nav_buttons["SUIVI"].clicked.connect(self.suivi_clicked.emit)
        self._nav_buttons["Parametres"].clicked.connect(self.parametres_clicked.emit)

        self.set_nav_checked("Produits")

        self._nav_buttons["NFR"].setEnabled(False)
        self._nav_buttons["SF"].setEnabled(False)
        self._nav_buttons["SUIVI"].setEnabled(False)
        self._nav_buttons["Parametres"].setEnabled(False)

        # Add admin group to nav layout
        nav_layout.addWidget(admin_container)

        # Add nav layout to main layout
        main_layout.addLayout(nav_layout)
        main_layout.addStretch(1)

        # Bottom section container
        bottom_layout = QVBoxLayout()
        bottom_layout.setSpacing(8)
        bottom_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Coffre button with lock icon
        self.btn_coffre = QToolButton()
        self.btn_coffre.setObjectName("CoffreButton")
        self.btn_coffre.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_coffre.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.btn_coffre.setText("")
        self.btn_coffre.setIconSize(QSize(32, 32))
        self.btn_coffre.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        pixmap = QPixmap(48, 48)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setFont(QFont("Segoe UI Emoji", 24))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "🔐")
        painter.end()
        self.btn_coffre.setIcon(QIcon(pixmap))

        coffre_style = """
            QToolButton {
                background-color: #b8860b;
                color: #ffffff;
                border: 2px solid #8b6914;
                padding: 10px 14px;
                font-weight: 700;
                font-size: 16px;
                border-radius: 12px;
            }
            QToolButton:hover {
                background-color: #daa520;
                border-color: #ffd700;
            }
        """
        self.btn_coffre.setStyleSheet(coffre_style)
        self.btn_coffre.clicked.connect(self.coffre_clicked.emit)
        bottom_layout.addWidget(self.btn_coffre)

        # Ecart button for cloture - 2 row format (Écart on top, value below)
        self.btn_ecart = QPushButton("Écart\n0 Ar")
        self.btn_ecart.setObjectName("EcartButton")
        self.btn_ecart.setFixedHeight(50)
        # Neutral style (matches theme)
        self._ecart_neutral = """
            QPushButton {
                background-color: #333333;
                color: white;
                border: none;
                padding: 4px 12px;
                font-weight: bold;
                font-size: 14px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
        """
        # Positive (green) style
        self._ecart_positive = """
            QPushButton {
                background-color: #16a34a;
                color: white;
                border: 1px solid #15803d;
                padding: 4px 12px;
                font-weight: bold;
                font-size: 14px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #22c55e;
            }
        """
        # Negative (red) style
        self._ecart_negative = """
            QPushButton {
                background-color: #dc2626;
                color: white;
                border: 1px solid #b91c1c;
                padding: 4px 12px;
                font-weight: bold;
                font-size: 14px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #ef4444;
            }
        """
        self.btn_ecart.setStyleSheet(self._ecart_neutral)
        self.btn_ecart.clicked.connect(self.cloture_clicked.emit)
        bottom_layout.addWidget(self.btn_ecart)

        main_layout.addLayout(bottom_layout)

    def set_nav_checked(self, label: str):
        for name, btn in self._nav_buttons.items():
            btn.setChecked(name == label)

    def enable_admin_buttons(self) -> None:
        self._nav_buttons["NFR"].setEnabled(True)
        self._nav_buttons["SF"].setEnabled(True)
        self._nav_buttons["SUIVI"].setEnabled(True)
        self._nav_buttons["Parametres"].setEnabled(True)

    def disable_admin_buttons(self) -> None:
        self._nav_buttons["NFR"].setEnabled(False)
        self._nav_buttons["SF"].setEnabled(False)
        self._nav_buttons["SUIVI"].setEnabled(False)
        self._nav_buttons["Parametres"].setEnabled(False)

    def update_ecart_text(self, text: str) -> None:
        if hasattr(self, "btn_ecart"):
            # Handle both formats: "Écart: 1000 Ar" or just "1000 Ar"
            if ":" in text:
                # Format: "Écart: 1000 Ar" - extract just the value
                parts = text.split(":", 1)
                value = parts[1].strip()
                self.btn_ecart.setText(f"Écart\n{value}")
            else:
                self.btn_ecart.setText(f"Écart\n{text}")

            # Set color based on value
            self._set_ecart_color(text)

    def _set_ecart_color(self, text: str) -> None:
        """Apply color based on ecart value."""
        # Extract numeric value from text
        value_str = text
        if ":" in text:
            parts = text.split(":", 1)
            value_str = parts[1].strip()

        # Remove "Ar" and any whitespace (including thousands separator spaces)
        value_str = value_str.replace("Ar", "").replace(" ", "").strip()

        try:
            value = int(value_str)
        except ValueError:
            # Cannot parse, use neutral
            self.btn_ecart.setStyleSheet(self._ecart_neutral)
            return

        # Apply appropriate style
        if value < 0:
            self.btn_ecart.setStyleSheet(self._ecart_negative)
        elif value > 0:
            self.btn_ecart.setStyleSheet(self._ecart_positive)
        else:
            self.btn_ecart.setStyleSheet(self._ecart_neutral)
