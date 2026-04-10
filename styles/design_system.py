"""Design system extensions for typography, spacing, and component styles.

This module extends the base design tokens with structured design system
values for better consistency across all UI components.
"""

from dataclasses import dataclass


@dataclass
class Typography:
    """Typography scale for the POS application."""

    font_family: str = "Segoe UI"
    h1_size: int = 24
    h2_size: int = 20
    h3_size: int = 16
    body_size: int = 13
    caption_size: int = 11
    button_size: int = 13


@dataclass
class Spacing:
    """8-point grid spacing system."""

    xs: int = 4  # Extra small
    sm: int = 8  # Small
    md: int = 12  # Medium
    lg: int = 16  # Large
    xl: int = 24  # Extra large
    xxl: int = 32  # 2x Extra large


@dataclass
class BorderRadius:
    """Border radius values."""

    none: int = 0
    sm: int = 4
    md: int = 8
    lg: int = 12
    pill: int = 999


# Design system instances
TYPOGRAPHY = Typography()
SPACING = Spacing()
BORDER_RADIUS = BorderRadius()
