"""Main Controller for Passive View pattern.

This controller manages business logic that was previously in MainWindow,
providing a clear separation between UI (Passive View) and business logic.
"""

from __future__ import annotations

import logging
from typing import Any

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from core.constants import BILLETAGE_DENOMINATIONS
from core.database import DatabaseManager
from core.formatters import format_grouped_int
from presenters.reports_presenter import ReportsPresenter
from services.daily_reset_service import DailyResetService
from services.suivi_journalier_service import DailyTrackingService
from ui.main.data_loader_thread import DataLoaderThread
from viewmodels.dashboard_viewmodel import DashboardViewModel
from viewmodels.panier_viewmodel import BasketManagerFactory

logger = logging.getLogger(__name__)


class MainController(QObject):
    """Controller for MainWindow implementing Passive View pattern.

    Handles all business logic including:
    - Database session management
    - Cash denomination handling
    - Dashboard totals computation
    - Sales recording
    - Safe (coffre) management
    - Report generation
    - Product data loading
    """

    # Qt Signals for Passive View updates
    totals_updated = pyqtSignal(
        int, int, int, int
    )  # total_depenses, total_ventes, total_caisse, total_coffre
    sales_list_updated = pyqtSignal(list)  # sales: list[dict]
    safe_balance_updated = pyqtSignal(int, str)  # new_total, display_text
    billetage_total_updated = pyqtSignal(int)  # total
    data_loaded = pyqtSignal(list)  # produits: list[dict]
    navigation_requested = pyqtSignal(str)  # screen
    header_data_updated = pyqtSignal(dict)  # header zone data

    def __init__(self, user: dict[str, Any]) -> None:
        """Initialize the controller with user context.

        Args:
            user: Dictionary containing user info (nom, role, etc.)
        """
        super().__init__()
        self.user = user

        # Initialize managers and services
        self.db_manager = DatabaseManager()
        self.panier_manager = BasketManagerFactory()
        self.tracking_service = DailyTrackingService(self.db_manager)
        self.daily_reset_service = DailyResetService(self.db_manager)
        self.dashboard_vm = DashboardViewModel(
            self.db_manager, tracking_service=self.tracking_service
        )
        self.reports_presenter = ReportsPresenter(self.db_manager)

        # Session tracking
        self.operateur_id: int | None = None
        self.session_id: int | None = None

        # Safe total in memory
        self.total_coffre: int = 0
        self._load_coffre_total()

        # Data loader thread (started on demand)
        self._loader_thread: DataLoaderThread | None = None

        # Global refresh timer (90 seconds) - starts after first header refresh
        self._global_refresh_timer = QTimer(self)
        self._global_refresh_timer.timeout.connect(self.refresh_header_data)
        self._global_refresh_timer.setInterval(90000)
        self._global_refresh_started = False

    # ==================== App State ====================

    def update_app_state(self, mode: str | None = None) -> None:
        """Update application state in database.

        Args:
            mode: Application mode to persist (e.g., 'caisse', 'reception')
        """
        if mode is not None:
            self.db_manager.set_parameter("APP_MODE", mode)
            logger.debug("App state updated: mode=%s", mode)

    # ==================== Session Management ====================

    def open_session(self) -> tuple[int, int]:
        """Open database session for the current user.

        Returns:
            Tuple of (operateur_id, session_id)
        """
        vendeur_nom = str(self.user.get("nom", "Operateur"))
        droit_acces = str(self.user.get("role", "vendeur"))
        self.operateur_id, self.session_id = self.db_manager.open_db_session(
            vendeur_nom, droit_acces
        )
        logger.info(
            "Session opened for %s (role: %s) - operateur_id: %s, session_id: %s",
            vendeur_nom,
            droit_acces,
            self.operateur_id,
            self.session_id,
        )
        self.refresh_header_data()
        return self.operateur_id, self.session_id

    def close_session(self) -> None:
        """Close the current database session."""
        if self.session_id is not None:
            self.db_manager.close_session(self.session_id)
            logger.info("Session closed: %s", self.session_id)
            self.session_id = None
            self.operateur_id = None

    # ==================== Cash Denominations ====================

    def _get_cash_denominations(self) -> list[int]:
        """Query DB for cash denominations.

        Returns:
            List of denomination values, or default denominations if not set.
        """
        default_denoms = list(BILLETAGE_DENOMINATIONS)
        try:
            raw = self.db_manager.get_setting("CASH_DENOMINATIONS", "")
            if not raw:
                return default_denoms
            # Parse comma-separated string into list of integers
            denominations = []
            for part in raw.split(","):
                part = part.strip()
                if part:
                    try:
                        denominations.append(int(part))
                    except ValueError:
                        # Skip invalid values
                        continue
            if not denominations:
                return default_denoms
            return denominations
        except Exception:
            # Fallback to default on any error
            return default_denoms

    def _load_coffre_total(self) -> None:
        """Load persisted coffre total from database on startup."""
        try:
            raw = self.db_manager.get_parameter("COFFRE_TOTAL", "0")
            self.total_coffre = int(raw) if raw else 0
        except (ValueError, TypeError):
            self.total_coffre = 0

    def get_cash_denominations(self) -> list[int]:
        """Public API for getting cash denominations.

        Returns:
            List of denomination values.
        """
        return self._get_cash_denominations()

    # ==================== Dashboard Totals ====================

    def compute_totals_for_day(self, jour: str) -> dict[str, int]:
        """Compute totals for a given day.

        Args:
            jour: Date in ISO format (YYYY-MM-DD)

        Returns:
            Dictionary with total_depenses, total_ventes, total_caisse
        """
        totals = self.dashboard_vm.compute_totals_for_day(jour, self.total_coffre)
        return {
            "total_depenses": totals.total_depenses,
            "total_ventes": totals.total_ventes,
            "total_caisse": totals.total_caisse,
        }

    def _refresh_all_data(self, jour: str) -> None:
        """Compute and emit totals for the given day.

        Args:
            jour: Date in ISO format (YYYY-MM-DD)
        """
        totals = self.dashboard_vm.compute_totals_for_day(jour, self.total_coffre)

        # Emit formatted totals for display
        formatted_depenses = format_grouped_int(totals.total_depenses)
        formatted_ventes = format_grouped_int(totals.total_ventes)
        formatted_caisse = format_grouped_int(totals.total_caisse)

        logger.debug(
            "Totals for %s: depenses=%s, ventes=%s, caisse=%s",
            jour,
            formatted_depenses,
            formatted_ventes,
            formatted_caisse,
        )

        # Emit the signal with raw values (view will format as needed)
        # total_caisse is already computed as: ventes - depenses - total_coffre
        self.totals_updated.emit(
            totals.total_depenses,
            totals.total_ventes,
            totals.total_caisse,
            self.total_coffre,
        )

    # ==================== Sales Management ====================

    def list_ventes_jour(self, jour: str) -> list[dict[str, Any]]:
        """List all sales for a given day.

        Args:
            jour: Date in ISO format (YYYY-MM-DD)

        Returns:
            List of sale records.
        """
        return self.db_manager.list_ventes_jour(jour)

    def record_sales(self, sales_rows: list[dict[str, Any]]) -> None:
        """Persist sales to database.

        Args:
            sales_rows: List of sale records to persist.
        """
        logger.debug(f"[DEBUG] record_sales called with {len(sales_rows)} rows")
        self._on_sales_day_recorded(sales_rows)

    def _on_sales_day_recorded(self, sales_rows: list[dict[str, Any]]) -> None:
        """Persist sales to database and refresh data.

        Args:
            sales_rows: List of sale records to persist.
        """
        for row in sales_rows or []:
            produit_id = int(row.get("produit_id", 0) or 0)
            if produit_id <= 0:
                continue
            try:
                self.db_manager.record_sale(
                    produit_id=produit_id,
                    produit_nom=str(row.get("produit", "")),
                    quantite=max(1, int(row.get("quantite", 1) or 1)),
                    prix_unitaire=max(0, int(row.get("prix_unitaire", 0) or 0)),
                    session_id=int(self.session_id),
                )
            except (RuntimeError, TypeError, ValueError) as exc:
                logger.warning("vente non enregistree pour produit_id=%s: %s", produit_id, exc)
                continue

        # Refresh dashboard after recording sales
        from datetime import date

        today = date.today().isoformat()
        self._refresh_all_data(today)
        self.refresh_header_data()

    def _on_transaction_finalisee(self, mode: str, montant: int) -> None:
        """Handle transaction finalization - refresh data.

        Args:
            mode: Transaction mode (e.g., 'caisse', 'especes')
            montant: Transaction amount
        """
        # Refresh dashboard totals
        from datetime import date

        today = date.today().isoformat()
        self._refresh_all_data(today)

        # Reload products (triggers data_loaded signal)
        self.load_products()

    def on_transaction_finalised(self, mode: str = "", montant: int = 0) -> None:
        """English alias for transaction finalised handler."""
        self._on_transaction_finalisee(mode, montant)

    # ==================== Safe (Coffre) Management ====================

    def update_safe(self, total_billetage: int) -> tuple[int, str]:
        """Update the safe total by adding the billetage amount.

        Args:
            total_billetage: Amount to add to the safe.

        Returns:
            Tuple of (new_total, display_text)
        """
        nouveau_total = self.total_coffre + total_billetage
        self.total_coffre = nouveau_total

        # Format for display
        display_text = format_grouped_int(nouveau_total)

        logger.info(
            "Safe updated: added %s, new total: %s",
            format_grouped_int(total_billetage),
            display_text,
        )

        return nouveau_total, display_text

    def get_safe_balance(self) -> tuple[int, str]:
        """Get current safe balance.

        Returns:
            Tuple of (total, display_text)
        """
        display_text = format_grouped_int(self.total_coffre)
        return self.total_coffre, display_text

    def manage_safe(self, total_billetage: int) -> None:
        """Manage safe: transfer billetage total to safe, persist, and emit update.

        Args:
            total_billetage: Billetage amount to add to safe.
        """
        if total_billetage <= 0:
            return

        self.total_coffre += total_billetage

        # Persist to database
        self.db_manager.set_parameter("COFFRE_TOTAL", str(self.total_coffre))

        # Emit signal for view update
        display_text = format_grouped_int(self.total_coffre)
        self.safe_balance_updated.emit(self.total_coffre, display_text)

        logger.info(
            "Safe updated: added %s, new total: %s",
            format_grouped_int(total_billetage),
            display_text,
        )

        # Refresh dashboard totals
        from datetime import date

        today = date.today().isoformat()
        self._refresh_all_data(today)

    def on_billetage_updated(self, total: int) -> None:
        """Handle billetage update from view.

        Args:
            total: Billetage total amount
        """
        self.billetage_total_updated.emit(total)

    def refresh_totals(self) -> None:
        """Refresh dashboard totals for today."""
        from datetime import date

        today = date.today().isoformat()
        self._refresh_all_data(today)

    def refresh_totaux(self) -> None:
        """Refresh dashboard totals (French alias for compatibility)."""
        self.refresh_totals()

    # ==================== Reports ====================

    def get_oasis_report(self, jour: str) -> list[dict[str, Any]]:
        """Get Oasis report for a given day.

        Args:
            jour: Date in ISO format (YYYY-MM-DD)

        Returns:
            List of report rows as dictionaries.
        """
        report_data = self.reports_presenter.get_oasis_report(jour)
        return [{"categorie": row.categorie, "total_prc": row.total_prc} for row in report_data]

    def get_guest_report(self, jour: str) -> list[dict[str, Any]]:
        """Get Guest report for a given day.

        Args:
            jour: Date in ISO format (YYYY-MM-DD)

        Returns:
            List of report rows as dictionaries.
        """
        detail_rows, _ = self.reports_presenter.get_guest_report(jour)
        return [
            {
                "categorie": row.categorie,
                "produit": row.produit,
                "qte": row.qte,
                "val": row.val,
            }
            for row in detail_rows
        ]

    # ==================== Data Loading ====================

    def load_products(self) -> None:
        """Start the data loader thread to load products."""
        if self._loader_thread is not None and self._loader_thread.isRunning():
            self._loader_thread.quit()
            self._loader_thread.wait(1500)

        self._loader_thread = DataLoaderThread(self.db_manager)
        self._loader_thread.data_loaded.connect(self._on_products_loaded)
        self._loader_thread.start()
        logger.debug("Product loader thread started")

    def _on_products_loaded(self, produits: list[dict[str, Any]]) -> None:
        """Handle products loaded from database.

        Args:
            produits: List of product dictionaries.
        """
        logger.debug("Products loaded: %d items", len(produits))
        self.data_loaded.emit(produits)

    def quit_loader(self) -> None:
        """Stop the data loader thread."""
        if self._loader_thread is not None and self._loader_thread.isRunning():
            self._loader_thread.quit()
            self._loader_thread.wait(1500)
            logger.debug("Product loader thread stopped")

    # ==================== Verification Date ====================

    def update_verification_date(self, produit_id: int, date_verification: str) -> None:
        """Update the last verification date for a product.

        Args:
            produit_id: The product ID to update
            date_verification: The verification date string (YYYY-MM-DD)
        """
        try:
            self.db_manager.update_derniere_verification(produit_id, date_verification)
            logger.info(
                "Verification date updated for product %s: %s",
                produit_id,
                date_verification,
            )
        except RuntimeError as exc:
            logger.warning(
                "Failed to update verification date for product %s: %s",
                produit_id,
                exc,
            )

    # ==================== Header Zone ====================

    def refresh_header_data(self) -> None:
        """Aggregate header zone data and emit signal.

        Collects: user name, today's transaction count, promo products,
        near-DLV products, and products to remove.
        """
        from datetime import datetime

        today = datetime.now().strftime("%d/%m/%y")
        user_name = self.user.get("nom", "Operateur")
        transaction_count = len(self.db_manager.list_daily_sales(today))

        # Extract product dicts (with stock info) from repository queries
        promo_products = self.db_manager.products.list_products_en_promo()
        near_dlv_products = self.db_manager.products.list_products_near_dlv(30)
        to_remove_products = self.db_manager.products.list_products_to_remove()

        header_data = {
            "date": today,
            "user": user_name,
            "transaction_count": transaction_count,
            "promo_products": promo_products,
            "near_dlv_products": near_dlv_products,
            "to_remove_products": to_remove_products,
        }
        logger.debug(
            "Header data refreshed: %s transactions, %s promo, %s near DLV, %s to remove",
            transaction_count,
            len(promo_products),
            len(near_dlv_products),
            len(to_remove_products),
        )
        self.header_data_updated.emit(header_data)

        # Start global refresh timer after first successful refresh
        if not self._global_refresh_started:
            self._global_refresh_started = True
            self._global_refresh_timer.start()
            logger.debug("Global refresh timer started (90s interval)")

    # ==================== Navigation ====================

    def request_navigation(self, screen: str) -> None:
        """Request navigation to a specific screen.

        Args:
            screen: Screen identifier (e.g., 'movements', 'expenses', 'tracking')
        """
        self.navigation_requested.emit(screen)

    # ==================== Daily Reset ====================

    def handle_cloture_complete(self, cloture_date: str) -> None:
        """Handle cloture completion by executing daily reset.

        Args:
            cloture_date: Date of the completed cloture in ISO format.
        """
        try:
            result = self.daily_reset_service.on_cloture_complete(cloture_date)
            logger.info("Daily reset executed after cloture: %s", result)

            # Refresh the coffre display
            _, display_text = self.get_safe_balance()
            self.safe_balance_updated.emit(self.total_coffre, display_text)
        except Exception as e:
            logger.error("Error executing daily reset after cloture: %s", e)

    # ==================== Cleanup ====================

    def cleanup(self) -> None:
        """Clean up resources before destruction."""
        self.quit_loader()
        self.close_session()
        logger.info("MainController cleaned up")
