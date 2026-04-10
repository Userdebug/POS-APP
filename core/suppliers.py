"""Supplier domain logic for the POS application.

This module provides supplier/fournisseur data structures and utilities.
Moved from ui/zone_panier/basket_suppliers.py for better architecture.
"""

from core.constants import DEFAULT_SUPPLIER_NAME


def default_fournisseurs() -> list[dict]:
    """Return default supplier list for the application.

    Returns:
        List of supplier dictionaries with default values.
    """
    return [
        {
            "nom": DEFAULT_SUPPLIER_NAME,
            "code": "F-001",
            "nif": "0000000000",
            "stat": "00000-00-00000",
            "contact": "034 00 000 00",
            "note": "**",
            "telephone": "034 00 000 00",
            "adresse": "Antananarivo",
        },
        {
            "nom": "MADA DISTRIB",
            "code": "F-002",
            "nif": "0000000001",
            "stat": "00000-00-00001",
            "contact": "033 12 345 67",
            "note": "****",
            "telephone": "033 12 345 67",
            "adresse": "Toamasina",
        },
    ]


def build_new_fournisseur(nom: str, index: int) -> dict:
    """Build a new supplier dictionary with given name and index.

    Args:
        nom: Supplier name
        index: Supplier index number

    Returns:
        Supplier dictionary with default empty values.
    """
    return {
        "nom": str(nom),
        "code": f"F-{int(index):03d}",
        "nif": "",
        "stat": "",
        "contact": "",
        "note": "",
        "telephone": "",
        "adresse": "",
    }


def fournisseur_info_text(fournisseur: dict | None) -> str:
    """Generate formatted supplier info text for display.

    Args:
        fournisseur: Supplier dictionary or None

    Returns:
        Formatted string with supplier information.
    """
    if not fournisseur:
        return "NIF: - | STAT: - | CONTACT: - | NOTE: -"
    nif = fournisseur.get("nif", "") or "-"
    stat = fournisseur.get("stat", "") or "-"
    contact = fournisseur.get("contact", "") or fournisseur.get("telephone", "") or "-"
    note = fournisseur.get("note", "") or fournisseur.get("adresse", "") or "-"
    return f"NIF: {nif} | STAT: {stat} | CONTACT: {contact} | NOTE: {note}"
