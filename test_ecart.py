#!/usr/bin/env python
"""Quick test for ecart color fix."""

import sys

sys.path.insert(0, ".")

from ui.components.sidebar_panel import SidebarPanel

sp = SidebarPanel()


def get_color(text):
    sp._set_ecart_color(text)
    style = sp.btn_ecart.styleSheet()
    if "#16a34a" in style:
        return "green"
    elif "#dc2626" in style:
        return "red"
    elif "#333333" in style:
        return "neutral"
    return "unknown"


# Test cases
tests = [
    ("1000", "green"),
    ("-500", "red"),
    ("0", "neutral"),
    ("10000", "green"),
    ("-10000", "red"),
]

all_passed = True
for value, expected in tests:
    result = get_color(value)
    status = "PASS" if result == expected else "FAIL"
    if result != expected:
        all_passed = False
    print(f"{status}: {value} -> expected {expected}, got {result}")

sys.exit(0 if all_passed else 1)
