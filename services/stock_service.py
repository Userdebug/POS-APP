"""Stock management service."""

import logging
from typing import Any

from core.exceptions import InsufficientStockError

logger = logging.getLogger(__name__)


def validate_quantity_against_stock(
    db_manager: Any,
    produit_id: int | None,
    requested_qte: int,
) -> tuple[bool, str]:
    """Validate if quantity is available in stock.

    Args:
        db_manager: Database manager instance
        produit_id: Product ID to check
        requested_qte: Quantity requested

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not produit_id:
        return True, ""  # New products don't have stock

    if requested_qte <= 0:
        return False, "Quantité invalide (doit être positive)"

    try:
        produit = db_manager.get_produit_by_id(produit_id)
        if not produit:
            return False, "Produit non trouvé"

        current_stock = int(produit.get("qte_stock", 0))
        if requested_qte > current_stock:
            return (
                False,
                f"Stock insuffisant! Stock actuel: {current_stock}, Quantité demandée: {requested_qte}",
            )

        return True, ""
    except Exception as e:
        logger.exception(f"Error checking stock for product {produit_id}")
        return False, f"Erreur de vérification du stock: {e}"


def validate_quantity_strict(
    db_manager: Any,
    produit_id: int,
    requested_qte: int,
) -> None:
    """Validate quantity against stock, raising InsufficientStockError on failure.

    Args:
        db_manager: Database manager instance
        produit_id: Product ID to check
        requested_qte: Quantity requested

    Raises:
        InsufficientStockError: If stock is insufficient.
        ValueError: If product not found or quantity invalid.
    """
    if requested_qte <= 0:
        raise ValueError("Quantité invalide (doit être positive)")

    produit = db_manager.get_produit_by_id(produit_id)
    if not produit:
        raise ValueError(f"Produit non trouvé: {produit_id}")

    current_stock = int(produit.get("qte_stock", 0))
    if requested_qte > current_stock:
        raise InsufficientStockError(produit_id, requested_qte, current_stock)


def decrement_stock(
    db_manager: Any,
    produit_id: int,
    quantite: int,
) -> bool:
    """Decrement stock for a product.

    Args:
        db_manager: Database manager instance
        produit_id: Product ID
        quantite: Quantity to decrement

    Returns:
        True if successful, False otherwise
    """
    if not produit_id or quantite <= 0:
        return False

    try:
        db_manager.decrement_stock(produit_id, quantite)
        logger.info(f"Stock decremented for product {produit_id}: -{quantite}")
        return True
    except Exception:
        logger.exception(f"Error decrementing stock for product {produit_id}")
        return False
