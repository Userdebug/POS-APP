"""Domain-specific exceptions for the POS application."""

from __future__ import annotations


class POSException(Exception):
    """Base exception for all POS application errors.

    Args:
        message: A human-readable description of the error.
    """

    def __init__(self, message: str = "") -> None:
        super().__init__(message)


class StockError(POSException):
    """Base exception for stock-related errors.

    Args:
        message: A human-readable description of the stock error.
    """

    def __init__(self, message: str = "") -> None:
        super().__init__(message)


class InsufficientStockError(StockError):
    """Raised when requested quantity exceeds available stock.

    Args:
        product_id: The product ID that has insufficient stock.
        requested: The quantity requested.
        available: The quantity available in stock.

    Returns:
        None
    """

    def __init__(self, product_id: int, requested: int, available: int) -> None:
        self.product_id = product_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Stock insuffisant pour produit {product_id}: "
            f"demande={requested}, disponible={available}"
        )


class SessionError(POSException):
    """Raised for session-related errors (open, close, authentication).

    Args:
        message: A human-readable description of the session error.
    """

    def __init__(self, message: str = "") -> None:
        super().__init__(message)


class ValidationError(POSException):
    """Raised when input validation fails.

    Args:
        message: A human-readable description of the validation error.
    """

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
