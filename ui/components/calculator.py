"""
Standalone Calculator Widget Component.

This module provides a reusable calculator widget with secure arithmetic expression
evaluation. It can be imported and instantiated independently in any PyQt6 project.

Features:
- Secure arithmetic expression evaluation using AST parsing (no eval() vulnerabilities)
- Supports basic operations: +, -, *, /, and parentheses
- Customizable display and button styling
- Quantity emission mode for numerical input scenarios
- Clear signal integration for external validation

Usage:
    from ui.components.calculator import CalculatorWidget

    calc = CalculatorWidget()
    calc.quantite_emise.connect(lambda qty: print(f"Quantity: {qty}"))
    calc.show()
"""

from __future__ import annotations

import ast
from typing import Callable, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# =============================================================================
# Calculator Engine - Business Logic
# =============================================================================

# Type alias for binary operators
BinaryOperator = Callable[[float, float], float]

# Allowed binary operators for secure evaluation
ALLOWED_BINARY_OPERATORS: dict[type[ast.AST], BinaryOperator] = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
}


class CalculatorEngineError(Exception):
    """Base exception for calculator engine errors."""

    pass


class InvalidExpressionError(CalculatorEngineError):
    """Raised when an invalid expression is encountered."""

    pass


class UnsupportedOperatorError(CalculatorEngineError):
    """Raised when an unsupported operator is used."""

    pass


class DivisionByZeroError(CalculatorEngineError):
    """Raised when division by zero is attempted."""

    pass


class CalculatorEngine:
    """
    Secure arithmetic expression evaluator.

    This engine safely evaluates mathematical expressions using AST parsing,
    preventing code injection and arbitrary code execution vulnerabilities.

    Supported operations:
        - Addition (+)
        - Subtraction (-)
        - Multiplication (*)
        - Division (/)
        - Parentheses for grouping
        - Unary plus and minus

    Example:
        >>> engine = CalculatorEngine()
        >>> engine.evaluate("2 + 3")
        5.0
        >>> engine.evaluate("10 / 2")
        5.0
        >>> engine.evaluate("(1 + 2) * 3")
        9.0
    """

    def __init__(
        self, allowed_operators: Optional[dict[type[ast.AST], BinaryOperator]] = None
    ) -> None:
        """
        Initialize the calculator engine.

        Args:
            allowed_operators: Optional custom operator dictionary.
                              Defaults to basic arithmetic operators.
        """
        self._operators = allowed_operators or ALLOWED_BINARY_OPERATORS.copy()

    def evaluate(self, expression: str) -> float:
        """
        Evaluate a mathematical expression securely.

        Args:
            expression: The arithmetic expression to evaluate.

        Returns:
            The result of the evaluation as a float.

        Raises:
            InvalidExpressionError: If the expression is invalid or contains
                                   non-numeric constants.
            UnsupportedOperatorError: If the expression contains unsupported
                                     operators.
            DivisionByZeroError: If division by zero is attempted.
        """
        if not expression or not expression.strip():
            raise InvalidExpressionError("Empty expression")

        try:
            tree = ast.parse(expression.strip(), mode="eval")
        except SyntaxError as e:
            raise InvalidExpressionError(f"Syntax error: {e}")

        return self._evaluate_node(tree)

    def _evaluate_node(self, node: ast.AST) -> float:
        """Recursively evaluate an AST node."""
        if isinstance(node, ast.Expression):
            return self._evaluate_node(node.body)

        if isinstance(node, ast.BinOp):
            return self._evaluate_binary_op(node)

        if isinstance(node, ast.UnaryOp):
            return self._evaluate_unary_op(node)

        if isinstance(node, ast.Constant):
            return self._evaluate_constant(node)

        raise UnsupportedOperatorError(f"Unsupported node type: {type(node).__name__}")

    def _evaluate_binary_op(self, node: ast.BinOp) -> float:
        """Evaluate a binary operation node."""
        op_type = type(node.op)
        op = self._operators.get(op_type)

        if op is None:
            raise UnsupportedOperatorError(f"Operator not allowed: {node.op.__class__.__name__}")

        left = self._evaluate_node(node.left)
        right = self._evaluate_node(node.right)

        # Check for division by zero
        if isinstance(node.op, ast.Div) and right == 0:
            raise DivisionByZeroError("Division by zero")

        return op(left, right)

    def _evaluate_unary_op(self, node: ast.UnaryOp) -> float:
        """Evaluate a unary operation node."""
        if isinstance(node.op, ast.UAdd):
            return +self._evaluate_node(node.operand)
        if isinstance(node.op, ast.USub):
            return -self._evaluate_node(node.operand)
        raise UnsupportedOperatorError(f"Unary operator not allowed: {node.op.__class__.__name__}")

    def _evaluate_constant(self, node: ast.Constant) -> float:
        """Evaluate a constant node."""
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise InvalidExpressionError(f"Non-numeric constant: {node.value}")


# =============================================================================
# Calculator Widget - UI Component
# =============================================================================


class CalculatorWidget(QWidget):
    """
    A calculator widget with secure arithmetic expression evaluation.

    This widget provides a full calculator interface with number buttons,
    operators, and special buttons for clearing, computing, and emitting
    quantities. It uses the CalculatorEngine for secure expression evaluation.

    Signals:
        quantite_emise: Emitted when the quantity button is pressed.
                        Passes the integer quantity value.
        valider_ligne_demande: Emitted when the validate button is pressed.

    Example:
        calc = CalculatorWidget()
        calc.quantite_emise.connect(lambda qty: print(f"Quantity: {qty}"))
        calc.show()
    """

    quantite_emise = pyqtSignal(int)
    """Emitted when quantity button (Q) is pressed with the integer value."""

    valider_ligne_demande = pyqtSignal()
    """Emitted when the validate button is pressed."""

    def __init__(
        self, engine: Optional[CalculatorEngine] = None, parent: Optional[QWidget] = None
    ) -> None:
        """
        Initialize the calculator widget.

        Args:
            engine: Optional CalculatorEngine instance. If not provided,
                   a new one will be created.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._engine = engine or CalculatorEngine()
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the user interface."""
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(4)

        # Create display and validate button row
        display_row = QHBoxLayout()
        display_row.setSpacing(4)

        self.display = QLineEdit("0")
        self.display.setReadOnly(True)
        self.display.setStyleSheet(self._get_display_style())
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        display_row.addWidget(self.display, 1)

        # Validate button using design tokens
        self.btn_valider = QPushButton("Valider")
        self.btn_valider.setStyleSheet(self._get_validate_button_style())
        self.btn_valider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_valider.clicked.connect(self._on_valider_clicked)
        display_row.addWidget(self.btn_valider)
        root.addLayout(display_row)

        # Create button grid — uniform stretch so every row gets equal height
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(3)
        for row in range(5):
            grid.setRowStretch(row, 1)
        for col in range(4):
            grid.setColumnStretch(col, 1)
        root.addLayout(grid, 1)

        # Define button layout optimized for POS
        # Row 0: 7, 8, 9, ÷
        # Row 1: 4, 5, 6, ×
        # Row 2: 1, 2, 3, −
        # Row 3: 0, 00, ., +
        # Row 4: C (2 cols), =, Q
        buttons = [
            ("7", 0, 0),
            ("8", 0, 1),
            ("9", 0, 2),
            ("÷", 0, 3),
            ("4", 1, 0),
            ("5", 1, 1),
            ("6", 1, 2),
            ("×", 1, 3),
            ("1", 2, 0),
            ("2", 2, 1),
            ("3", 2, 2),
            ("−", 2, 3),
            ("0", 3, 0),
            ("00", 3, 1),
            (".", 3, 2),
            ("+", 3, 3),
            ("C", 4, 0, 1, 2),  # Clear spans 2 columns
            ("=", 4, 2),
            ("Q", 4, 3),
        ]

        for text, row, col, *spans in buttons:
            row_span = spans[0] if len(spans) > 0 else 1
            col_span = spans[1] if len(spans) > 1 else 1

            btn = QPushButton(text)
            btn.setStyleSheet(self._get_button_style(text))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

            # Connect button click handler
            btn.clicked.connect(lambda _, t=text: self._on_button(t))

            # Add to grid with spans for special buttons
            if row_span > 1 or col_span > 1:
                grid.addWidget(btn, row, col, row_span, col_span)
            else:
                grid.addWidget(btn, row, col)

    def _get_display_style(self) -> str:
        """Get stylesheet for the calculator display using design tokens."""
        return """
            font-size: 14px;
            font-weight: bold;
            background-color: #1e293b;
            color: #f9fafb;
            padding: 4px 8px;
            border: 1px solid #334155;
            border-radius: 6px;
        """

    def _get_validate_button_style(self) -> str:
        """Get stylesheet for the validate button using design tokens."""
        return """
            QPushButton {
                font-size: 11px;
                font-weight: bold;
                background-color: #1e293b;
                color: #f9fafb;
                border: 1px solid #334155;
                padding: 4px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
            QPushButton:pressed {
                background-color: #1e293b;
            }
            QPushButton:disabled {
                background-color: #374151;
                color: #6b7280;
                border-color: #4b5563;
            }
        """

    def _get_button_style(self, text: str) -> str:
        """Get stylesheet for calculator buttons using design tokens.

        All buttons share uniform padding and no min-width constraint so that
        the QSizePolicy.Expanding policy drives consistent sizing across the
        grid. Only background/border/font-weight vary per role.

        Args:
            text: Button text to determine special styling.

        Returns:
            CSS stylesheet string for the button.
        """
        # Base button style — shared by every button (uniform padding, no min-width)
        base = """
            QPushButton {
                font-size: 12px;
                background-color: #1e293b;
                color: #f9fafb;
                border: 1px solid #334155;
                padding: 6px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #475569;
            }
            QPushButton:pressed {
                background-color: #0f172a;
            }
        """

        # Quantity button (Q)
        if text == "Q":
            return (
                base
                + """
                QPushButton {
                    font-weight: bold;
                    background-color: #1f6feb;
                    border: 1px solid #1f6feb;
                }
                QPushButton:hover { background-color: #1a5fd4; }
                QPushButton:pressed { background-color: #1f6feb; }
            """
            )

        # Operator buttons
        if text in ("+", "\u2212", "\u00d7", "\u00f7", "="):
            return (
                base
                + """
                QPushButton {
                    font-size: 14px;
                    font-weight: bold;
                    background-color: #334155;
                    border: 1px solid #475569;
                }
                QPushButton:hover { background-color: #475569; }
                QPushButton:pressed { background-color: #1e293b; }
            """
            )

        # Clear button
        if text == "C":
            return (
                base
                + """
                QPushButton {
                    font-weight: bold;
                    background-color: #991b1b;
                    border: 1px solid #b91c1c;
                }
                QPushButton:hover { background-color: #b91c1c; }
                QPushButton:pressed { background-color: #7f1d1d; }
            """
            )

        return base

    def _on_button(self, text: str) -> None:
        """
        Handle button click events.

        Args:
            text: The button text identifying which button was pressed.
        """
        current = self.display.text().strip() or "0"

        # Clear button
        if text == "C":
            self._set_display("0")
            return

        # Evaluate button
        if text == "=":
            self._compute()
            return

        # Quantity button
        if text == "Q":
            self._emit_quantite()
            return

        # Handle "00" button (common in POS for large amounts)
        if text == "00":
            if current == "0":
                return  # Don't add "00" to "0"
            self._set_display(current + "00")
            return

        # Map display symbols to calculation operators
        operator_map = {
            "×": "*",
            "÷": "/",
            "−": "-",
            "+": "+",
        }

        # Number/operator buttons - handle leading zero
        if current == "0" and text not in (".", "+", "−", "×", "÷"):
            self._set_display(text)
        else:
            # Use mapped operator for calculation
            mapped_text = operator_map.get(text, text)
            self._set_display(current + mapped_text)

    def _compute(self) -> None:
        """Evaluate the current expression and display the result."""
        expr = self.display.text().strip()

        if not expr:
            return

        try:
            value = self._engine.evaluate(expr)

            # Convert to int if whole number
            if isinstance(value, float) and value.is_integer():
                value = int(value)

            self._set_display(str(value))

        except (InvalidExpressionError, UnsupportedOperatorError, DivisionByZeroError):
            # On error, reset to 0
            self._set_display("0")
        except ZeroDivisionError:
            self._set_display("0")

    def _emit_quantite(self) -> None:
        """Emit the current display value as an integer quantity."""
        text = self.display.text().strip()

        try:
            value = int(float(text))
        except ValueError:
            value = 0

        if value <= 0:
            return

        self.quantite_emise.emit(value)
        self._set_display("0")

    def _on_valider_clicked(self) -> None:
        """Handle validate button click."""
        self.valider_ligne_demande.emit()

    def _set_display(self, text: str) -> None:
        """
        Set the display text.

        Args:
            text: The text to display.
        """
        self.display.setText(text)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_value(self) -> Optional[float]:
        """
        Get the current display value as a float.

        Returns:
            The current value as a float, or None if the display is empty/invalid.
        """
        text = self.display.text().strip()

        if not text or text == "0":
            return None

        try:
            return float(text)
        except ValueError:
            return None

    def get_display_text(self) -> str:
        """
        Get the current display text.

        Returns:
            The current text displayed in the calculator.
        """
        return self.display.text()

    def clear(self) -> None:
        """Clear the calculator display."""
        self._set_display("0")

    def set_display(self, text: str) -> None:
        """
        Set the display to a specific value.

        Args:
            text: The text to display.
        """
        if text:
            self._set_display(text)
        else:
            self._set_display("0")


# =============================================================================
# Standalone Test
# =============================================================================

if __name__ == "__main__":
    import sys

    from PyQt6.QtWidgets import QApplication

    # Test the engine
    engine = CalculatorEngine()

    test_cases = [
        ("2 + 3", 5.0),
        ("10 - 4", 6.0),
        ("3 * 4", 12.0),
        ("15 / 3", 5.0),
        ("(1 + 2) * 3", 9.0),
        ("10 / 2 + 3", 8.0),
        ("-5 + 10", 5.0),
        ("2.5 * 4", 10.0),
    ]

    for expr, expected in test_cases:
        result = engine.evaluate(expr)
        status = "✓" if result == expected else "✗"

    print("\nTesting error handling:")
    error_cases = [
        ("2 +", "InvalidExpressionError"),
        ("__import__('os')", "UnsupportedOperatorError"),
    ]

    for expr, expected_error in error_cases:
        try:
            engine.evaluate(expr)
        except CalculatorEngineError:
            pass

    print("\nTesting CalculatorWidget:")

    # Create Qt application for widget testing
    app = QApplication(sys.argv)

    widget = CalculatorWidget()
    widget.setWindowTitle("Calculator Widget Test")
    widget.show()

    sys.exit(app.exec())
