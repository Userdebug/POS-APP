from core.utils import calculate_line_total, normalize_product_line


def normalize_ligne(produit: dict, mode: str = "vente") -> dict:
    """Normalize product line data for basket operations.

    This function now delegates to the unified normalize_product_line function
    from core.utils, while preserving additional fields specific to basket operations.
    """
    normalized = normalize_product_line(produit, mode=mode)
    # Preserve basket-specific fields
    normalized["dlv_dlc"] = str(produit.get("dlv_dlc", ""))
    normalized["prix"] = normalized["pv"]  # Alias for backward compatibility
    normalized["nouveau"] = bool(produit.get("nouveau", False))
    return normalized


def ligne_total(ligne: dict) -> int:
    """Calculate line total using unified utility function."""
    return calculate_line_total(ligne, price_field="pv")
