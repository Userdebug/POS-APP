"""Presenter for report tables (Oasis, Guest, Ventes Jour, SF).

This module contains UI-independent business logic for computing and formatting
report data. It separates calculation logic from PyQt6 presentation.

No PyQt6 dependencies - returns plain Python data structures ready for display.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from core.formatters import format_grouped_int

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OasisReportRow:
    """Single row in Oasis report."""

    categorie: str
    total_prc: int


@dataclass(frozen=True)
class GuestReportRow:
    """Single row in Guest report with category break."""

    categorie: str
    produit: str
    qte: int
    val: int


@dataclass(frozen=True)
class GuestSubtotalRow:
    """Subtotal row for Guest report."""

    categorie: str
    total: int


@dataclass(frozen=True)
class DailySalesRow:
    """Single row in daily sales report."""

    categorie: str
    produit: str
    quantite_vendue: int
    total_vente: int
    stock_final: int


@dataclass(frozen=True)
class DailySalesSubtotalRow:
    """Subtotal row for daily sales report."""

    categorie: str
    total_qte: int
    total_val: int


@dataclass(frozen=True)
class DailyExpenseRow:
    """Single row in daily expenses report."""

    designation: str
    valeur: int
    remarque: str


@dataclass(frozen=True)
class DailyReceptionRow:
    """Single row in daily receptions (invoices) report."""

    numero_facture: str
    fournisseur: str
    total_ttc: int


@dataclass(frozen=True)
class JournalierCompletData:
    """Complete daily report data containing sales, expenses, and receptions."""

    jour: str
    sales: list[DailySalesRow]
    sales_subtotals: list[DailySalesSubtotalRow]
    total_ventes: int
    expenses: list[DailyExpenseRow]
    total_depenses: int
    receptions: list[DailyReceptionRow]
    total_receptions: int


@dataclass(frozen=True)
class SFTableData:
    """SF (Stock Flux) table data for a date range."""

    categories: list[str]
    data_by_category: dict[str, dict[str, Any]]
    date_debut: str
    date_fin: str


class ReportsPresenter:
    """Business logic for report table generation.

    Provides methods to compute and format report data from the database,
    returning simple data structures suitable for UI consumption.
    """

    def __init__(self, db_manager: Any) -> None:
        """Initialize presenter with database access.

        Args:
            db_manager: DatabaseManager instance for data access.
        """
        self._db_manager = db_manager

    def get_oasis_report(self, jour: str) -> list[OasisReportRow]:
        """Get Oasis report data for a given day.

        Args:
            jour: Date in ISO format (YYYY-MM-DD).

        Returns:
            List of OasisReportRow objects with category totals.
        """
        try:
            raw_data = self._db_manager.get_oasis_stats(jour)
            return [
                OasisReportRow(
                    categorie=str(row.get("categorie", "")),
                    total_prc=int(str(row.get("total_prc", 0) or 0).replace(" ", "") or 0),
                )
                for row in raw_data
            ]
        except Exception as exc:
            logger.warning("Failed to get Oasis report for %s: %s", jour, exc)
            return []

    def get_guest_report(self, jour: str) -> tuple[list[GuestReportRow], list[GuestSubtotalRow]]:
        """Get Guest report data for a given day with subtotals.

        Args:
            jour: Date in ISO format (YYYY-MM-DD).

        Returns:
            Tuple of (detail rows, subtotal rows).
        """
        try:
            raw_data = self._db_manager.get_guest_stats(jour)
            detail_rows: list[GuestReportRow] = []
            subtotal_rows: list[GuestSubtotalRow] = []

            current_cat: str | None = None
            cat_total_val = 0

            for row_data in raw_data:
                cat = str(row_data.get("categorie", ""))
                # Handle category change - add subtotal
                if current_cat is not None and cat != current_cat:
                    subtotal_rows.append(
                        GuestSubtotalRow(
                            categorie=current_cat,
                            total=cat_total_val,
                        )
                    )
                    cat_total_val = 0

                current_cat = cat

                detail_rows.append(
                    GuestReportRow(
                        categorie=cat,
                        produit=str(row_data.get("produit", "")),
                        qte=int(str(row_data.get("qte", 0) or 0).replace(" ", "") or 0),
                        val=int(str(row_data.get("val", 0) or 0).replace(" ", "") or 0),
                    )
                )
                cat_total_val += int(str(row_data.get("val", 0) or 0).replace(" ", "") or 0)

            # Add final subtotal
            if current_cat is not None:
                subtotal_rows.append(
                    GuestSubtotalRow(
                        categorie=current_cat,
                        total=cat_total_val,
                    )
                )

            return detail_rows, subtotal_rows
        except Exception as exc:
            logger.warning("Failed to get Guest report for %s: %s", jour, exc)
            return [], []

    def get_journalier_complet(self, jour: str) -> JournalierCompletData:
        """Get complete daily report: sales, expenses, and receptions.

        This is the main daily report used in the cloture workflow.

        Args:
            jour: Date in ISO format (YYYY-MM-DD).

        Returns:
            JournalierCompletData with all daily summary data.
        """
        # 1. Sales data
        sales: list[DailySalesRow] = []
        sales_subtotals: list[DailySalesSubtotalRow] = []
        total_ventes = 0

        try:
            raw_sales = self._db_manager.get_detailed_daily_sales(jour)
            current_cat: str | None = None
            cat_total_qte = 0
            cat_total_val = 0

            for row_data in raw_sales:
                cat = str(row_data.get("categorie", ""))

                # Handle category change - add subtotal
                if current_cat is not None and cat != current_cat:
                    sales_subtotals.append(
                        DailySalesSubtotalRow(
                            categorie=current_cat,
                            total_qte=cat_total_qte,
                            total_val=cat_total_val,
                        )
                    )
                    cat_total_qte = 0
                    cat_total_val = 0

                current_cat = cat

                qte = int(row_data.get("quantite_vendue", 0) or 0)
                total = int(row_data.get("total_vente", 0) or 0)

                cat_total_qte += qte
                cat_total_val += total
                total_ventes += total

                sales.append(
                    DailySalesRow(
                        categorie=cat,
                        produit=str(row_data.get("produit", "")),
                        quantite_vendue=qte,
                        total_vente=total,
                        stock_final=int(row_data.get("stock_final", 0) or 0),
                    )
                )

            # Add final subtotal
            if current_cat is not None:
                sales_subtotals.append(
                    DailySalesSubtotalRow(
                        categorie=current_cat,
                        total_qte=cat_total_qte,
                        total_val=cat_total_val,
                    )
                )
        except Exception as exc:
            logger.warning("Failed to get sales data for %s: %s", jour, exc)

        # 2. Expenses data
        expenses: list[DailyExpenseRow] = []
        total_depenses = 0

        try:
            raw_expenses = self._db_manager.list_depenses_jour(jour)
            for row in raw_expenses:
                valeur = int(row.get("valeur", 0) or 0)
                total_depenses += valeur
                expenses.append(
                    DailyExpenseRow(
                        designation=str(row.get("designation", "")),
                        valeur=valeur,
                        remarque=str(row.get("remarque", "")),
                    )
                )
        except Exception as exc:
            logger.warning("Failed to get expenses data for %s: %s", jour, exc)

        # 3. Achats (invoices) data
        achats: list[DailyReceptionRow] = []
        total_achats = 0

        try:
            raw_achats = self._db_manager.list_daily_achats(jour)
            for row in raw_achats:
                total_ttc = int(row.get("total_ttc", 0) or 0)
                total_achats += total_ttc
                achats.append(
                    DailyReceptionRow(
                        numero_facture=str(row.get("numero_facture", "-")),
                        fournisseur=str(row.get("fournisseur", "-")),
                        total_ttc=total_ttc,
                    )
                )
        except Exception as exc:
            logger.warning("Failed to get achats data for %s: %s", jour, exc)

        return JournalierCompletData(
            jour=jour,
            sales=sales,
            sales_subtotals=sales_subtotals,
            total_ventes=total_ventes,
            expenses=expenses,
            total_depenses=total_depenses,
            receptions=achats,
            total_receptions=total_achats,
        )

    def get_sf_table_data(self, date_debut: str, date_fin: str) -> SFTableData:
        """Get SF (Stock Flux) table data for margin percentages by category.

        Args:
            date_debut: Start date in ISO format.
            date_fin: End date in ISO format.

        Returns:
            SFTableData with categories and computed margins.
        """
        try:
            from services.analyse_journaliere_service import AnalyseJournaliereService

            analyse_service = AnalyseJournaliereService(self._db_manager)
            data = analyse_service.get_sf_report(date_debut, date_fin)
            categories = analyse_service.get_sf_categories()

            # Build lookup dict, ensuring order matches categories
            data_by_category = {
                str(item.get("sous_categorie", "")): item
                for item in data
                if item.get("sous_categorie")
            }

            # Reorder data to match categories order (categories are sorted alphabetically)
            ordered_data: dict[str, dict[str, Any]] = {}
            for cat in categories:
                if cat in data_by_category:
                    ordered_data[cat] = data_by_category[cat]

            return SFTableData(
                categories=categories,
                data_by_category=ordered_data,
                date_debut=date_debut,
                date_fin=date_fin,
            )
        except Exception as exc:
            logger.warning("Failed to get SF table data: %s", exc)
            return SFTableData(
                categories=[],
                data_by_category={},
                date_debut=date_debut,
                date_fin=date_fin,
            )

    @staticmethod
    def format_sf_margin(item: dict[str, Any] | None) -> str:
        """Format margin percentage from SF data item.

        Args:
            item: Dictionary with 'marge_ttc' and 'vente_theo_ttc' keys.

        Returns:
            Formatted percentage string (e.g., "25.5%").
        """
        if item is None:
            return ""
        cat_marge = float(item.get("marge_ttc", 0) or 0)
        cat_ca = float(item.get("vente_theo_ttc", 0) or 0)
        if cat_ca <= 0:
            return "0%"
        return f"{(cat_marge / cat_ca) * 100:.1f}%"

    @staticmethod
    def format_amount(amount: int) -> str:
        """Format amount with thousand separators.

        Args:
            amount: Integer amount to format.

        Returns:
            Formatted string (e.g., "1 234 567").
        """
        return format_grouped_int(amount)
