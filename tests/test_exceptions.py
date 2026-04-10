"""Tests for domain-specific exceptions."""

import unittest

from core.exceptions import (
    InsufficientStockError,
    POSException,
    SessionError,
    StockError,
    ValidationError,
)


class TestExceptions(unittest.TestCase):
    def test_pos_exception_is_base(self) -> None:
        exc = POSException("test error")
        self.assertIsInstance(exc, Exception)
        self.assertEqual(str(exc), "test error")

    def test_stock_error_inherits_pos_exception(self) -> None:
        exc = StockError("stock error")
        self.assertIsInstance(exc, POSException)

    def test_insufficient_stock_error_attributes(self) -> None:
        exc = InsufficientStockError(product_id=42, requested=10, available=5)
        self.assertIsInstance(exc, StockError)
        self.assertEqual(exc.product_id, 42)
        self.assertEqual(exc.requested, 10)
        self.assertEqual(exc.available, 5)
        self.assertIn("42", str(exc))
        self.assertIn("10", str(exc))
        self.assertIn("5", str(exc))

    def test_session_error_inherits_pos_exception(self) -> None:
        exc = SessionError("session error")
        self.assertIsInstance(exc, POSException)

    def test_validation_error_inherits_pos_exception(self) -> None:
        exc = ValidationError("validation error")
        self.assertIsInstance(exc, POSException)

    def test_insufficient_stock_error_message_contains_fields(self) -> None:
        exc = InsufficientStockError(product_id=7, requested=20, available=3)
        message = str(exc)
        self.assertIn("7", message)
        self.assertIn("20", message)
        self.assertIn("3", message)
        self.assertIn("insuffisant", message)

    def test_session_error_custom_message(self) -> None:
        exc = SessionError("session non ouverte")
        self.assertEqual(str(exc), "session non ouverte")

    def test_validation_error_custom_message(self) -> None:
        exc = ValidationError("quantite negative interdite")
        self.assertEqual(str(exc), "quantite negative interdite")

    def test_all_exceptions_catchable_by_pos_exception(self) -> None:
        """Toutes les exceptions doivent etre capturables via POSException."""
        exceptions = [
            StockError("stock error"),
            InsufficientStockError(product_id=1, requested=5, available=2),
            SessionError("session error"),
            ValidationError("validation error"),
        ]
        for exc in exceptions:
            with self.subTest(exc=type(exc).__name__):
                self.assertIsInstance(exc, POSException)
                try:
                    raise exc
                except POSException:
                    pass  # Successfully caught

    def test_pos_exception_with_no_args(self) -> None:
        exc = POSException()
        self.assertEqual(str(exc), "")


if __name__ == "__main__":
    unittest.main()
