"""Standardized button components for the POS application.

This module provides a factory pattern for creating consistently styled
buttons across the entire application, replacing inline style definitions.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton

from styles.design_tokens import TOKENS


class POSButton(QPushButton):
    """Standardized button for POS system with consistent styling.

    Supports different variants, sizes, and states while maintaining
    design token consistency.
    """

    VARIANTS = {
        "primary": {
            "bg": TOKENS["button_success"],
            "border": TOKENS["button_success_border"],
            "text": "#f8fafc",
            "hover_bg": "#15803d",
            "pressed_bg": "#166534",
        },
        "secondary": {
            "bg": TOKENS["bg_button"],
            "border": TOKENS["border_button"],
            "text": TOKENS["text_primary"],
            "hover_bg": TOKENS["bg_button_hover"],
            "pressed_bg": TOKENS["bg_button_pressed"],
        },
        "danger": {
            "bg": TOKENS["danger"],
            "border": "#dc2626",
            "text": TOKENS["text_primary"],
            "hover_bg": "#dc2626",
            "pressed_bg": "#b91c1c",
        },
        "info": {
            "bg": "#0d47a1",
            "border": "#1565c0",
            "text": "#f9fafb",
            "hover_bg": "#1565c0",
            "pressed_bg": "#0a2f6a",
        },
        "warning": {
            "bg": "#b8860b",
            "border": "#8b6914",
            "text": "#ffffff",
            "hover_bg": "#daa520",
            "pressed_bg": "#8b6914",
        },
    }

    SIZES = {
        "small": {"height": 28, "padding": "6px 12px", "font_size": 11},
        "medium": {"height": 36, "padding": "8px 16px", "font_size": 13},
        "large": {"height": 44, "padding": "10px 20px", "font_size": 13},
        "icon": {"height": 35, "padding": "0px", "font_size": 18},
    }

    def __init__(
        self,
        text: str,
        variant: str = "secondary",
        size: str = "medium",
        icon: str | None = None,
        parent=None,
    ):
        """Initialize the POS button.

        Args:
            text: Button text
            variant: Style variant ('primary', 'secondary', 'danger', 'info', 'warning')
            size: Size variant ('small', 'medium', 'large', 'icon')
            icon: Optional icon text (emoji or symbol)
            parent: Parent widget
        """
        super().__init__(text, parent)
        self._variant = variant
        self._size = size
        self._apply_style()

        if icon:
            self.setText(f"{icon} {text}" if text else icon)

    def _apply_style(self) -> None:
        """Apply the calculated stylesheet."""
        v = self.VARIANTS.get(self._variant, self.VARIANTS["secondary"])
        s = self.SIZES.get(self._size, self.SIZES["medium"])

        style = f"""
            QPushButton {{
                background-color: {v['bg']};
                color: {v['text']};
                border: 1px solid {v['border']};
                border-radius: 8px;
                padding: {s['padding']};
                font-weight: 600;
                font-size: {s['font_size']}px;
                min-height: {s['height']}px;
            }}
            QPushButton:hover {{
                background-color: {v['hover_bg']};
            }}
            QPushButton:pressed {{
                background-color: {v['pressed_bg']};
            }}
            QPushButton:disabled {{
                background-color: {TOKENS['bg_button_disabled']};
                color: {TOKENS['text_muted']};
                border-color: {TOKENS['button_disabled_border']};
            }}
        """
        self.setStyleSheet(style)

    def set_variant(self, variant: str) -> None:
        """Change the button variant at runtime."""
        self._variant = variant
        self._apply_style()


class NavButton(POSButton):
    """Navigation button for sidebar with checkable state."""

    def __init__(self, text: str, parent=None):
        """Initialize navigation button."""
        super().__init__(text, variant="secondary", size="medium", parent=parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_nav_style()

    def _apply_nav_style(self) -> None:
        """Apply navigation-specific styling."""
        nav_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {TOKENS['text_muted']};
                border: none;
                padding: 10px 14px;
                text-align: center;
                font-size: 14px;
                font-weight: 600;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: {TOKENS['bg_button_hover']};
                color: {TOKENS['text_default']};
            }}
            QPushButton:checked {{
                background-color: {TOKENS['bg_button_hover']};
                color: {TOKENS['text_primary']};
            }}
        """
        self.setStyleSheet(nav_style)


class ActionButton(POSButton):
    """Large action button for primary actions (e.g., ENCAISSER, PAYER)."""

    def __init__(self, text: str, enabled: bool = True, parent=None):
        """Initialize action button."""
        super().__init__(text, variant="primary", size="large", parent=parent)
        self.setEnabled(enabled)
        self._apply_action_style()

    def _apply_action_style(self) -> None:
        """Apply action button styling with gradient."""
        action_style = f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 {TOKENS['button_success']}, stop:1 #22c55e);
                color: white;
                font-size: 18px;
                font-weight: 700;
                border: 2px solid #4ade80;
                border-radius: 12px;
                padding: 12px 20px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #15803d, stop:1 #22c55e);
            }}
            QPushButton:pressed {{
                background-color: #166534;
            }}
            QPushButton:disabled {{
                background: none;
                background-color: {TOKENS['bg_button_disabled']};
                color: {TOKENS['text_muted']};
                border-color: {TOKENS['button_disabled_border']};
            }}
        """
        self.setStyleSheet(action_style)
