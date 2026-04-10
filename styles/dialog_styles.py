"""Reusable dialog styles built on design tokens."""

from styles.design_tokens import TOKENS

# Base dialog background
DIALOG_BASE = f"""
    QDialog {{
        background-color: {TOKENS['bg_sidebar']};
    }}
    QLabel {{
        color: {TOKENS['text_default']};
        font-size: 13px;
    }}
"""

# Form inputs (QLineEdit, QSpinBox, QComboBox, QTextEdit, QDateEdit)
INPUT_FIELD = f"""
    QLineEdit, QSpinBox, QComboBox, QTextEdit, QDateEdit {{
        background-color: {TOKENS['bg_input']};
        color: {TOKENS['text_primary']};
        border: 1px solid {TOKENS['border_input']};
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
    }}
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus, QDateEdit:focus {{
        border: 2px solid #3b82f6;
    }}
    QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled,
    QTextEdit:disabled, QDateEdit:disabled {{
        background-color: {TOKENS['bg_button_disabled']};
        color: {TOKENS['text_muted']};
    }}
"""

# Primary action button (Confirm, Save, Validate)
PRIMARY_BUTTON = f"""
    QPushButton {{
        background-color: #16a34a;
        color: #f8fafc;
        border: 1px solid #15803d;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 700;
        font-size: 13px;
        min-height: 12px;
    }}
    QPushButton:hover {{
        background-color: #15803d;
    }}
    QPushButton:pressed {{
        background-color: #166534;
    }}
    QPushButton:disabled {{
        background-color: {TOKENS['bg_button_disabled']};
        color: {TOKENS['text_muted']};
        border-color: {TOKENS['button_disabled_border']};
    }}
"""

# Secondary button (Cancel, Close, Annuler)
SECONDARY_BUTTON = f"""
    QPushButton {{
        background-color: {TOKENS['bg_button']};
        color: {TOKENS['text_default']};
        border: 1px solid {TOKENS['border_button']};
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        font-size: 13px;
        min-height: 12px;
    }}
    QPushButton:hover {{
        background-color: {TOKENS['bg_button_hover']};
    }}
    QPushButton:pressed {{
        background-color: {TOKENS['bg_button_pressed']};
    }}
"""

# Danger button (Delete, Supprimer)
DANGER_BUTTON = f"""
    QPushButton {{
        background-color: {TOKENS['danger']};
        color: {TOKENS['text_primary']};
        border: 1px solid #dc2626;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 700;
        font-size: 13px;
        min-height: 12px;
    }}
    QPushButton:hover {{
        background-color: #dc2626;
    }}
    QPushButton:pressed {{
        background-color: #b91c1c;
    }}
    QPushButton:disabled {{
        background-color: {TOKENS['bg_button_disabled']};
        color: {TOKENS['text_muted']};
        border-color: {TOKENS['button_disabled_border']};
    }}
"""

# Card-style container for grouping info
INFO_CARD = f"""
    background-color: {TOKENS['bg_card']};
    border: 1px solid {TOKENS['border_primary']};
    border-radius: 10px;
    padding: 14px;
"""

# Warning label style
WARNING_LABEL = """
    color: #f59e0b;
    font-weight: 700;
    font-size: 16px;
    padding: 12px;
    background-color: rgba(245, 158, 11, 0.1);
    border-radius: 8px;
"""

# Error label style
ERROR_LABEL = f"""
    color: {TOKENS['danger']};
    font-size: 12px;
    padding: 8px;
    background-color: rgba(239, 68, 68, 0.1);
    border-radius: 6px;
"""

# Success label style
SUCCESS_LABEL = f"""
    color: {TOKENS['success']};
    font-size: 12px;
    padding: 8px;
    background-color: rgba(76, 175, 80, 0.1);
    border-radius: 6px;
"""

# Total / large amount display
TOTAL_DISPLAY = f"""
    font-size: 24px;
    font-weight: 700;
    color: {TOKENS['total_caisse_text']};
    background-color: {TOKENS['total_caisse_bg']};
    border: 2px solid {TOKENS['total_caisse_border']};
    border-radius: 10px;
    padding: 14px 20px;
"""

# Change positive (sufficient payment)
CHANGE_POSITIVE = f"""
    color: {TOKENS['success']};
    font-size: 20px;
    font-weight: 700;
    padding: 10px 16px;
    background-color: rgba(76, 175, 80, 0.1);
    border-radius: 8px;
"""

# Change negative (insufficient payment)
CHANGE_NEGATIVE = f"""
    color: {TOKENS['danger']};
    font-size: 16px;
    font-weight: 600;
    padding: 10px 16px;
    background-color: rgba(239, 68, 68, 0.1);
    border-radius: 8px;
"""

# Money input (enlarged)
MONEY_INPUT = f"""
    QLineEdit {{
        background-color: {TOKENS['bg_input']};
        color: {TOKENS['text_primary']};
        border: 2px solid {TOKENS['border_input']};
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 18px;
        font-weight: 600;
    }}
    QLineEdit:focus {{
        border-color: #3b82f6;
    }}
"""

# Table widget for report dialogs
REPORT_TABLE = f"""
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

# Separator line
SEPARATOR = f"""
    background-color: {TOKENS['border_primary']};
    border: none;
    height: 1px;
"""

# Dialog header label
HEADER_LABEL = f"""
    font-size: 16px;
    font-weight: 700;
    color: {TOKENS['text_primary']};
    padding-bottom: 4px;
"""

# Stock info display (env dialog)
STOCK_INFO = f"""
    color: {TOKENS['text_muted']};
    font-weight: 600;
    font-size: 13px;
"""

# Min-height helper for inputs
INPUT_MIN_HEIGHT = 36
