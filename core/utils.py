"""Utility functions shared across the application."""

from __future__ import annotations

from typing import Any

__all__ = [
    "calculate_line_total",
    "normalize_product_line",
    "validate_quantity_against_stock",
]


def calculate_line_total(
    line: dict[str, Any],
    price_field: str = "pv",
    default_qty: int = 1,
) -> int:
    """Calculate the total for a product line (price × quantity).

    This is a unified function that consolidates duplicate implementations
    previously found in:
    - PanierTransactionsService.line_total()
    - FactureLineEditService._line_total()
    - PanierTableBuilder._line_total()

    Args:
        line: Dictionary containing product line data
        price_field: Field name to use for price (default: "pv")
                     Other common values: "pa" (purchase price), "prix", "prc"
        default_qty: Default quantity when not specified (default: 1)

    Returns:
        The total price (price × quantity)
    """
    # Handle different price field names flexibly with error handling
    if price_field == "pv":
        # For pv (selling price), check prix first then pv
        try:
            price_val = line.get("prix", line.get(price_field, 0)) or 0
            price = int(price_val)
        except (TypeError, ValueError):
            price = 0
    else:
        try:
            price = int(line.get(price_field, 0) or 0)
        except (TypeError, ValueError):
            price = 0

    # Get quantity with default
    qte_raw = line.get("qte")
    if qte_raw is None:
        qte = default_qty
    else:
        try:
            qte = int(qte_raw)
            if qte < 1:
                qte = default_qty
        except (TypeError, ValueError):
            qte = default_qty

    return price * qte


def normalize_product_line(
    data: dict[str, Any],
    mode: str = "caisse",
) -> dict[str, Any]:
    """Normalize product line data for basket operations.

    This consolidates duplicate normalization logic from:
    - basket_models.normalize_ligne()
    - ReceptionPersistenceService._sanitize_line()

    Args:
        data: Raw product data dictionary
        mode: Operation mode - "caisse" (cash register) or "reception" (invoice)

    Returns:
        Normalized product line dictionary with consistent field names
    """
    from core.formatters import parse_grouped_int

    # Parse numeric fields
    pa = parse_grouped_int(data.get("pa", 0))
    pv = parse_grouped_int(data.get("pv", data.get("prix", pa)))
    prc = parse_grouped_int(data.get("prc", round(pa * 1.2)))

    # Get and normalize category
    categorie = str(data.get("categorie", "")).strip()
    if not categorie or categorie == "-":
        categorie = "Sans categorie"

    # Get quantity with minimum of 1
    qte = max(1, parse_grouped_int(data.get("qte", 1)))

    return {
        "id": data.get("id"),
        "nom": str(data.get("nom", "")).strip(),
        "categorie": categorie,
        "pa": pa,
        "pv": pv,
        "prc": prc,
        "qte": qte,
    }


def validate_quantity_against_stock(
    ligne: dict[str, Any],
    available_stock: int,
) -> tuple[bool, str]:
    """Validate if the quantity in a basket line doesn't exceed available stock.

    Args:
        ligne: The product line dict containing 'qte' and 'id' fields
        available_stock: The current stock quantity available

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if quantity is valid, False otherwise
        - error_message: Error message if invalid, empty string otherwise
    """
    if not ligne:
        return True, ""

    # Skip validation for new products (no ID) or invalid quantities
    produit_id = ligne.get("id")
    requested_qte = int(ligne.get("qte", 1) or 1)

    if not produit_id or requested_qte <= 0:
        return True, ""

    # Check if quantity exceeds available stock
    if requested_qte > available_stock:
        return (
            False,
            f"Stock insuffisant! Stock actuel: {available_stock}, Quantité demandée: {requested_qte}",
        )

    return True, ""
