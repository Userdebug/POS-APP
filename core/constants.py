"""Constantes metier partagees pour l'application POS.

Regroupe les valeurs fixes utilisees a travers l'application :
categories, denominations de billetage, formats de date, labels.
"""

from __future__ import annotations

__all__ = [
    "DEFAULT_CATEGORY_NAME",
    "DEFAULT_SUPPLIER_NAME",
    "CURRENCY_LABEL",
    "FACTURE_NUMBER_PREFIX",
    "BILLETAGE_DENOMINATIONS",
    "DATE_FORMAT_DAY",
    "DATE_FORMAT_MONTH",
    "DATE_FORMAT_TIME",
    "DATE_FORMAT_FACTURE_REF",
    "OASIS_CATEGORIES",
    "GUEST_CATEGORIES",
    "PARENT_CATEGORY_OASIS",
    "PARENT_CATEGORY_GUEST",
]

DEFAULT_CATEGORY_NAME: str = "Sans categorie"
DEFAULT_SUPPLIER_NAME: str = "FOURNISSEUR PAR DEFAUT"

CURRENCY_LABEL: str = "Ar"
FACTURE_NUMBER_PREFIX: str = "FACT"

PARENT_CATEGORY_OASIS: str = "Catégorie 1 - OW (Owners)"
PARENT_CATEGORY_GUEST: str = "Catégorie 2 - NOW (Not owners)"

BILLETAGE_DENOMINATIONS: tuple[int, ...] = (20000, 10000, 5000, 2000, 1000, 500, 200, 100)

OASIS_CATEGORIES: tuple[str, ...] = ("BA", "BSA", "Confi", "EPI", "Tabac")
GUEST_CATEGORIES: tuple[str, ...] = (
    "HS",
    "Baz",
    "GL",
    "Gaz",
    "PF",
    "Zoth",
    "Lub",
    "Pea",
    "Solaires",
)

DATE_FORMAT_DAY: str = "%Y-%m-%d"
DATE_FORMAT_MONTH: str = "%Y-%m"
DATE_FORMAT_TIME: str = "%H:%M:%S"
DATE_FORMAT_FACTURE_REF: str = "%Y%m%d-%H%M%S"
