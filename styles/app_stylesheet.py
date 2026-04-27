"""Generation du stylesheet global a partir des design tokens."""

from string import Template

from styles.design_tokens import TOKENS

_QSS_TEMPLATE = Template("""
QMainWindow {
    background-color: $bg_window;
}
QWidget {
    background-color: transparent;
    color: $text_default;
    font-family: "Segoe UI";
    font-size: 13px;
}
QFrame#Sidebar {
    background-color: $bg_sidebar;
    border-right: 1px solid $border_primary;
}
QFrame#MainContent {
    background-color: $bg_panel;
    border-radius: 15px;
}
QFrame#CartFrame {
    background-color: $bg_card;
    border-radius: 15px;
}
QFrame#FooterFrame {
    background-color: $bg_card;
    border-radius: 8px;
}
QLabel#AppTitle {
    color: $text_primary;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#SoonTag {
    color: $text_muted;
    font-size: 11px;
    font-weight: 600;
    padding: 6px 8px;
    background-color: $bg_soon;
    border: 1px dashed $border_input;
    border-radius: 8px;
}
QLabel[metric="true"] {
    font-size: 16px;
    font-weight: 700;
    background-color: $bg_card;
    padding: 10px;
    border-radius: 6px;
    color: $text_primary;
}
QPushButton#DangerButton {
    background-color: $danger;
    color: $text_primary;
    font-weight: 700;
}
QPushButton#DangerButton:hover {
    background-color: #dc2626;
}
QPushButton#btn_np {
    color: #fbbf24;
}
QToolButton#CoffreButton, QPushButton#CoffreButton {
    background-color: #b8860b;
    color: #ffffff;
    border: 2px solid #8b6914;
    padding: 10px 14px;
    font-weight: 700;
    font-size: 16px;
    border-radius: 12px;
}
QToolButton#CoffreButton:hover, QPushButton#CoffreButton:hover {
    background-color: #daa520;
    border-color: #ffd700;
}
QPushButton[nav="true"] {
    background-color: transparent;
    color: $text_muted;
    border: none;
    padding: 10px 14px;
    text-align: left;
    font-size: 14px;
    font-weight: 600;
    border-radius: 8px;
}
QPushButton[nav="true"]:hover {
    background-color: $bg_button_hover;
    color: $text_default;
}
QPushButton[nav="true"]:checked {
    background-color: $bg_button_hover;
    color: $text_primary;
}
QPushButton {
    background-color: $bg_button;
    color: $text_primary;
    border: 1px solid $border_button;
    border-radius: 8px;
    padding: 7px 12px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: $bg_button_hover;
}
QPushButton:pressed {
    background-color: $bg_button_pressed;
}
QPushButton:disabled {
    background-color: $bg_button_disabled;
    color: $text_muted;
}
QLineEdit, QComboBox, QDateEdit {
    background-color: $bg_input;
    border: 1px solid $border_input;
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: $success;
    selection-color: $text_primary;
}
QGroupBox {
    border: none;
    margin-top: 18px;
    padding: 10px 0px;
    font-weight: 700;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 0px;
    padding: 0px;
    color: #e2e8f0;
    font-size: 16px;
}
QTableWidget {
    background-color: transparent;
    border: none;
    gridline-color: $border_primary;
    alternate-background-color: transparent;
}
QTableWidget::item:selected {
    background-color: $bg_button_disabled;
    color: $text_primary;
}
QHeaderView::section {
    background-color: transparent;
    color: $text_header;
    border: none;
    padding: 6px 8px;
    font-weight: 700;
}
QTableCornerButton::section {
    background-color: transparent;
    border: none;
}
QTableWidget#sf_report_table {
    border: 1px solid $border_input;
    background-color: $bg_panel;
    color: $text_default;
    font-size: 12px;
}
QTableWidget#sf_report_table::item {
    padding: 8px;
}
QTableWidget#sf_report_table::item:selected {
    background-color: $bg_button_disabled;
    color: $text_primary;
}
QScrollBar:vertical {
    background-color: transparent;
    width: 10px;
    border: none;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: $border_input;
    min-height: 40px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background-color: $text_muted;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
QScrollBar:horizontal {
    background-color: transparent;
    height: 10px;
    border: none;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background-color: $border_input;
    min-width: 40px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background-color: $text_muted;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}
""")


def build_stylesheet(tokens: dict[str, str] | None = None) -> str:
    merged = dict(TOKENS)
    if tokens:
        merged.update(tokens)
    return _QSS_TEMPLATE.safe_substitute(merged)
