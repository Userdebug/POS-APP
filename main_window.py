"""Main Window - Passive View Pattern.

This module implements the Passive View pattern where MainWindow only handles:
- Creating UI widgets
- Connecting signals
- Calling controller methods on user actions
- Updating UI when controller emits signals

All business logic is delegated to MainController.
"""

import logging
from datetime import date
from typing import Any

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from controllers.main_controller import MainController
from core.focus_manager import FocusManager
from ui.components.cash_counter_footer import CashCounterFooter
from ui.components.defilling_ticker_widget import DefillingWidget
from ui.components.header_info_widget import HeaderInfoWidget
from ui.components.reports_widget import ReportsWidget

# from ui.components.sf_table_widget import SFTableWidget  # Disabled for debugging
from ui.components.sidebar_panel import SidebarPanel
from ui.screens.expenses_screen import ExpensesScreen
from ui.screens.movements_screen import EcranMouvements
from ui.zone_actions_etats.actions_states_widget import ZoneActionsEtats
from ui.zone_panier import BasketContainer
from ui.zone_produits.products_widget import ZoneProduits

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Fenetre principale qui orchestre les ecrans de vente et de mouvements.

    Passive View: delegue toute la logique metier au MainController.
    """

    _SF_DATE_DEBUT_PARAM_KEY = "SF_DATE_DEBUT_DEFAULT"

    def __init__(self, controller: MainController) -> None:
        """Initialize MainWindow with controller (Dependency Injection).

        Args:
            controller: MainController instance handling business logic
        """
        super().__init__()
        self.setWindowTitle("Gestion Commerciale")
        self.resize(1280, 800)

        self.controller = controller
        self.user = self.controller.user
        self._total_caisse = 0
        self._current_billetage_total = 0
        self._admin_authenticated = False

        # Stack for navigation
        self.stack = QStackedWidget()
        self.page_principale = QWidget()

        # Root layout
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(5)

        self.sidebar = SidebarPanel()
        root_layout.addWidget(self.sidebar)
        self._setup_sidebar()
        root_layout.addWidget(self.stack, 1)

        # Get denominations from controller
        denominations = self.controller.get_cash_denominations()

        # Zones - use controller's managers
        self.zone_panier = BasketContainer(
            self.controller.panier_manager,
            db_manager=self.controller.db_manager,
            tracking_service=self.controller.tracking_service,
        )
        self.zone_produits = ZoneProduits()

        # Focus manager for search bar restoration after dialogs
        self.focus_manager = FocusManager()
        self.focus_manager.set_focus_target(self.zone_produits.search_input)

        # Get user info for screens
        vendeur_nom = str(self.user.get("nom", "Operateur"))

        self.zone_actions_etats = ZoneActionsEtats(
            db_manager=self.controller.db_manager,
            tracking_service=self.controller.tracking_service,
            reports_presenter=self.controller.reports_presenter,
        )
        self.ecran_mouvements = EcranMouvements(
            db_manager=self.controller.db_manager,
            vendeur_nom=vendeur_nom,
            operateur_id=self.controller.operateur_id,
            session_id=self.controller.session_id,
        )
        self.expenses_screen = ExpensesScreen(self.controller.db_manager, self)

        # Layout principal
        main_layout = QVBoxLayout(self.page_principale)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(2)

        # Header zone widgets
        self.header_info_widget = HeaderInfoWidget()
        self.defilling_widget = DefillingWidget()
        self.header_frame = self._build_header_zone()
        main_layout.addWidget(self.header_frame)

        # Top split: Zone Panier (left) + Zone Produits (right)
        top_split = QHBoxLayout()
        top_split.setContentsMargins(0, 0, 0, 0)
        top_split.setSpacing(5)

        # Zone 2: Panier + SF footer (left side)
        zone_panier_container = QWidget()
        zone_panier_layout = QVBoxLayout(zone_panier_container)
        zone_panier_layout.setContentsMargins(0, 0, 0, 0)
        zone_panier_layout.setSpacing(2)
        zone_panier_layout.addWidget(self.zone_panier, 1)
        zone_panier_layout.addWidget(self._build_sf_table(), 0)

        # Zone 3: Produits (right side)
        top_split.addWidget(zone_panier_container, 4)
        top_split.addWidget(self.zone_produits, 3)
        top_split_widget = QWidget()
        top_split_widget.setLayout(top_split)
        main_layout.addWidget(top_split_widget, 3)

        # Zone 4: Reports & Tools (bottom)
        user_nom = self.user.get("nom", "Utilisateur")
        self.reports_widget = ReportsWidget(
            self.controller.db_manager,
            self.controller.reports_presenter,
            self.controller.operateur_id,
            user_nom,
        )
        zone_reports_tools = QWidget()
        zone_reports_tools.setStyleSheet(
            "QWidget { border: 1px solid #4b5563; border-radius: 4px; }"
        )
        zone_reports_tools_layout = QHBoxLayout(zone_reports_tools)
        zone_reports_tools_layout.setContentsMargins(4, 4, 4, 4)
        zone_reports_tools_layout.setSpacing(5)

        self.billetage_widget = CashCounterFooter(denominations=denominations)
        self.billetage_widget.setMinimumHeight(180)

        zone_reports_tools_layout.addWidget(self.billetage_widget, 1)
        zone_reports_tools_layout.addWidget(self.zone_actions_etats.calculatrice, 2)
        zone_reports_tools_layout.addWidget(self.reports_widget, 6)

        main_layout.addWidget(zone_reports_tools, 2)

        self.stack.addWidget(self.page_principale)
        self.stack.addWidget(self.ecran_mouvements)
        self.setCentralWidget(root)

        # Connect controller signals to passive update methods
        self._connect_controller_signals()

        # Connect child widget signals
        self._connect_signals()

        # Open session and start loading data
        self.controller.open_session()
        self.controller.load_products()

        # Initialize coffre button text with current safe balance
        _, display_text = self.controller.get_safe_balance()
        self.update_safe_balance(display_text)

        # Set focus to search bar on app open
        QTimer.singleShot(100, self.focus_manager.restore_focus)

    def _setup_sidebar(self) -> None:
        """Setup sidebar signal connections."""
        self.sidebar.produits_clicked.connect(self._open_movements)
        self.sidebar.depenses_clicked.connect(self._open_expenses)
        self.sidebar.achats_clicked.connect(self._open_achats)
        self.sidebar.nfr_clicked.connect(self._open_nfr)
        self.sidebar.sf_clicked.connect(self._open_sf)
        self.sidebar.suivi_clicked.connect(self._open_tracking)
        self.sidebar.coffre_clicked.connect(self._open_safe)
        self.sidebar.parametres_clicked.connect(self._open_parameters)
        self.sidebar.admin_clicked.connect(self._open_admin_auth)
        self.sidebar.cloture_clicked.connect(self._open_closure)

    def _build_header_zone(self) -> QFrame:
        """Build header zone with info and ticker widgets.

        Contains:
        - HeaderInfoWidget: Session user, transaction count, metrics
        - DefillingTickerWidget: Near expiry, to remove alerts
        """
        frame = QFrame()
        frame.setMinimumHeight(65)
        frame.setStyleSheet("background-color: #1f2937; border-radius: 4px;")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)
        layout.addWidget(self.header_info_widget, 0)
        layout.addWidget(self.defilling_widget, 0)
        self.defilling_widget.setFixedWidth(580)
        return frame

    def _build_sf_table(self) -> QWidget:
        """Build the SF (Stock Flux) margin table widget."""
        from ui.components.sf_table_widget import SFTableWidget

        self.sf_margin_widget = SFTableWidget(
            db_manager=self.controller.db_manager,
            reports_presenter=self.controller.reports_presenter,
            settings_service=self.controller.db_manager.settings,
        )
        return self.sf_margin_widget

    def _on_header_data_updated(self, data: dict) -> None:
        """Handle header data update from controller - passive update."""
        if hasattr(self, "header_info_widget"):
            self.header_info_widget.update_data(
                user=data.get("user", "Operateur"),
                transaction_count=data.get("transaction_count", 0),
            )
        if hasattr(self, "defilling_widget"):
            self.defilling_widget.update_ticker(
                promo=[],
                near_dlv=data.get("near_dlv_products", []),
                to_remove=data.get("to_remove_products", []),
            )

    def _connect_controller_signals(self) -> None:
        """Connect controller signals to passive update methods."""
        # Connect controller signals to view update methods
        self.controller.totals_updated.connect(self.update_totals)
        self.controller.sales_list_updated.connect(self.reports_widget.update_sales_history)
        self.controller.safe_balance_updated.connect(self._on_safe_updated)
        self.controller.billetage_total_updated.connect(self.update_billetage_total)
        self.controller.data_loaded.connect(self._on_data_loaded)
        self.controller.header_data_updated.connect(self._on_header_data_updated)

        # Defer initial header data refresh to allow DefillingWidget to fully initialize
        # This fixes the race condition where the signal fires before widgets are ready
        QTimer.singleShot(200, lambda: self.controller.refresh_header_data())

    def _on_data_loaded(self, produits_db: list[dict[str, Any]]) -> None:
        """Handle products loaded - passive update."""
        self.zone_produits.set_produits(produits_db)
        self.ecran_mouvements.produits_table.set_produits(produits_db)

        # Defer heavy operations to avoid blocking UI
        QTimer.singleShot(0, lambda: self._update_reports_and_totals())

    def _update_reports_and_totals(self) -> None:
        """Deferred update for reports and totals."""
        today = date.today().isoformat()
        self.reports_widget.update_reports(today)
        self.controller.refresh_totals()

    def _connect_signals(self) -> None:
        """Connecte les signaux des composants enfants aux slots de la fenêtre principale."""
        self.ecran_mouvements.retour_demande.connect(self._ouvrir_principal)

        # Product modification - refresh zone_produits and header data
        self.ecran_mouvements.produit_modifie.connect(self._on_product_modified)

        # Billetage updates - delegate to controller
        self.billetage_widget.billetage_updated.connect(self.controller.on_billetage_updated)

        # Logique métier - delegate to controller
        self.zone_produits.produit_ajoute.connect(self.zone_panier.add_product)
        self.zone_produits.verification_change.connect(self.controller.update_verification_date)
        self.zone_panier.mode_change.connect(self._on_mode_change)
        # Pass mode changes to ZoneProduits for button enable/disable logic
        self.zone_panier.mode_change.connect(self.zone_produits.set_mode)
        self.zone_actions_etats.quantite_depuis_calculatrice.connect(
            self.zone_panier.appliquer_quantite
        )
        # Calculator Valider button - unified validation for both vente et achats  modes
        self.zone_actions_etats.valider_ligne_demande.connect(self._validate_from_calculator)
        self.zone_actions_etats.ouvrir_mouvements_demande.connect(self._open_movements)
        self.zone_actions_etats.ouvrir_depenses_demande.connect(self._open_expenses)
        self.zone_actions_etats.ouvrir_suivi_demande.connect(self._open_tracking)
        self.zone_actions_etats.ouvrir_parametres_demande.connect(self._open_parameters)

        # Connect cloture complete signal - triggers daily reset after cloture
        self.zone_actions_etats.cloture_complete.connect(self.controller.handle_cloture_complete)
        self.zone_actions_etats.fermer_application.connect(self.close)

        self.zone_panier.validation_state_changed.connect(
            self.zone_actions_etats.set_valider_enabled
        )

        # Sales recording - delegate to controller
        self.zone_panier.sales_day_recorded.connect(self.controller.record_sales)
        self.zone_panier.transaction_finalisee.connect(self.controller.on_transaction_finalised)

        # Refresh products list when new product is saved via AddProduitDialog
        self.zone_panier.nouveau_produit_enregistre.connect(self._on_new_product_saved)

        self.zone_actions_etats.set_valider_enabled(self.zone_panier.current_validation_enabled())

        # Connect focus restoration after dialogs/validation
        self.zone_panier.zone_vente.dialog_closed.connect(self.focus_manager.restore_focus)
        self.zone_panier.zone_achat.payment_completed.connect(self.focus_manager.restore_focus)
        self.zone_panier.validation_completed.connect(self.focus_manager.restore_focus)

    def _on_mode_change(self, mode: str) -> None:
        """Handle mode change with minimal UI refresh."""
        try:
            self.controller.update_app_state(mode=mode.lower())
            if hasattr(self, "zone_actions_etats"):
                self.zone_actions_etats.update_ui_for_mode(mode)
            self._deferred_mode_refresh(mode)
        except Exception as e:
            logging.error(f"Mode change error: {e}")

    def _deferred_mode_refresh(self, mode: str) -> None:
        """Lightweight mode switch - only update UI elements, skip table rebuild."""
        try:
            # Only update action button text and validation state (no table rebuild)
            if hasattr(self, "zone_panier"):
                self.zone_panier.active_zone._update_action_button_state()
                self.zone_panier.active_zone._emit_validation_state()

            self._sync_validation_button()

        except Exception as e:
            logging.error(f"Mode refresh error: {e}")

    def _sync_validation_button(self) -> None:
        """Update validation button state without heavy refresh."""
        # Check zone_panier validation and update zone_actions_etats
        if hasattr(self, "zone_panier") and hasattr(self, "zone_actions_etats"):
            self.zone_actions_etats.set_valider_enabled(
                self.zone_panier.current_validation_enabled()
            )

    def _validate_from_calculator(self) -> None:
        """Delegate validation to zone_panier for both modes."""
        if hasattr(self, "zone_panier"):
            self.zone_panier.validate_current_line()

    def _on_product_modified(self, produit: dict) -> None:
        """Handle product modification from mouvements screen - refresh products list and header.

        Uses incremental update instead of full reload to avoid UI stuttering.
        """
        # Use targeted update instead of full reload
        self.zone_produits.update_single_product(produit)
        # Also update the movements screen products table if visible
        if hasattr(self, "ecran_mouvements"):
            self.ecran_mouvements.produits_table.update_produit(produit)
        # Refresh header data to update promo/DLV counts
        self.controller.refresh_header_data()

    def _on_new_product_saved(self, produit: dict) -> None:
        """Handle new product saved from AddProduitDialog - refresh products list.

        Loads products once and uses incremental updates.
        """
        # Load products (this will trigger set_produits which now has change detection)
        self.controller.load_products()
        # Refresh header data - this now uses the controller's method which is optimized

    # ==================== Passive Update Methods ====================
    # These methods ONLY update UI widgets - no business logic

    def update_totals(self, total_depenses: int, total_ventes: int, total_caisse: int) -> None:
        """Passive update: update header metrics and compute ecart.

        Args:
            total_depenses: Total expenses amount
            total_ventes: Total sales amount
            total_caisse: Total cash in register
        """
        self._total_caisse = total_caisse
        self.header_info_widget.update_metrics(
            vente=total_ventes,
            depenses=total_depenses,
            caisse=total_caisse,
        )
        self.update_billetage_total(self._current_billetage_total)

    def update_sales_list(self, sales: list[dict[str, Any]]) -> None:
        """Passive update: delegate sales update to reports widget.

        Args:
            sales: List of sale records
        """
        self.reports_widget.update_sales_history(sales)

    def update_safe_balance(self, display_text: str) -> None:
        """Passive update: update safe button text.

        Args:
            display_text: Formatted safe balance text
        """
        self.sidebar.btn_coffre.setText(display_text)

    def update_billetage_total(self, total: int) -> None:
        """Passive update: compute ecart and update sidebar button.

        Args:
            total: Billetage total
        """
        from core.formatters import format_grouped_int

        self._current_billetage_total = total
        ecart = total - self._total_caisse
        self.sidebar.update_ecart_text(format_grouped_int(ecart))

    def _on_safe_updated(self, new_total: int, display_text: str) -> None:
        """Handle safe update signal from controller.

        Args:
            new_total: New safe total
            display_text: Formatted display text
        """
        self.update_safe_balance(display_text)
        self.billetage_widget.reset()
        self.controller.refresh_totals()

    # ==================== Navigation Methods ====================

    def _open_movements(self) -> None:
        """Affiche l'écran des mouvements de stock."""
        self.sidebar.set_nav_checked("Produits")
        self.stack.setCurrentWidget(self.ecran_mouvements)

    # Alias for backward compatibility
    _ouvrir_movements = _open_movements

    def _open_main(self) -> None:
        """Affiche l'écran de vente principal."""
        self.stack.setCurrentWidget(self.page_principale)

    # Alias for backward compatibility
    _ouvrir_principal = _open_main

    def _open_closure(self) -> None:
        """Ouvre le formulaire de clôture et rafraîchit les indicateurs après validation.

        Uses the simplified cloture workflow with CA Final Entry Dialog.
        """
        self.zone_actions_etats.open_cloture_simple(date.today().isoformat(), self)
        self.controller.refresh_totals()

    # Alias for backward compatibility
    _ouvrir_cloture = _open_closure

    def _open_admin_auth(self) -> None:
        """Open admin authentication dialog."""
        from ui.dialogs.admin_auth_dialog import AdminAuthDialog

        dialog = AdminAuthDialog(self.controller.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.is_authenticated():
            self._admin_authenticated = True
            self.sidebar.enable_admin_buttons()
            self.sidebar.update_ecart_text("Clôture")

    def _open_expenses(self) -> None:
        """Ouvre le dialogue des dépenses."""
        self.sidebar.set_nav_checked("Depenses")
        self.expenses_screen.refresh_data()
        self.expenses_screen.exec()
        self.controller.refresh_totaux()

    # Alias for backward compatibility
    _ouvrir_depenses = _open_expenses

    def _open_achats(self) -> None:
        """Ouvre le resume des achats (factures) du jour."""
        from datetime import date as date_module

        from ui.dialogs.achats_resume_dialog import AchatsResumeDialog

        self.sidebar.set_nav_checked("Achats")
        jour = date_module.today().isoformat()
        dialog = AchatsResumeDialog(parent=self, db_manager=self.controller.db_manager, jour=jour)
        dialog.exec()

    # Alias for backward compatibility
    _ouvrir_achats = _open_achats

    def _open_nfr(self) -> None:
        """Open the NFR report."""
        from ui.dialogs.nfr_report_dialog import NFRReportDialog

        self.sidebar.set_nav_checked("NFR")
        dialog = NFRReportDialog(parent=self, db_manager=self.controller.db_manager)
        dialog.exec()

    def _open_sf(self) -> None:
        """Open the SF report."""
        from PyQt6.QtCore import QDate

        from ui.dialogs.sf_report_dialog import SFReportDialog

        self.sidebar.set_nav_checked("SF")
        # Use date from the margin widget if available, otherwise default to 1 month ago
        start_date = (
            self.sf_margin_widget._date_debut
            if hasattr(self, "sf_margin_widget")
            else QDate.currentDate().addMonths(-1)
        )
        end_date = QDate.currentDate()
        dialog = SFReportDialog(
            parent=self,
            db_manager=self.controller.db_manager,
            start_date=start_date,
            end_date=end_date,
        )
        dialog.exec()

    def _open_tracking(self) -> None:
        """Affiche l'écran SUIVI (Analyse CA et Achats)."""
        from ui.dialogs.suivi_analyse_dialog import SuiviAnalyseDialog

        self.sidebar.set_nav_checked("SUIVI")
        dialog = SuiviAnalyseDialog(parent=self, db_manager=self.controller.db_manager)
        dialog.exec()

    # Alias for backward compatibility
    _ouvrir_suivi = _open_tracking

    def _open_safe(self) -> None:
        """Transfer billetage to safe and update display."""
        from ui.dialogs.coffre_confirmation_dialog import CoffreConfirmationDialog

        total_billetage = self.billetage_widget.get_total()
        if total_billetage <= 0:
            return
        current_coffre, _ = self.controller.get_safe_balance()
        dialog = CoffreConfirmationDialog(self, total_billetage, current_coffre)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.controller.manage_safe(total_billetage)

    def _open_parameters(self) -> None:
        """Ouvre le dialogue des paramètres."""
        from ui.dialogs.parametres_dialog import ParametresDialog

        dialog = ParametresDialog(
            self,
            db_manager=self.controller.db_manager,
            settings_service=self.controller.db_manager.settings,
            financial_service=self.controller.db_manager.financial,
        )
        dialog.exec()

    def _open_categories(self) -> None:
        """Ouvre le dialogue de gestion des catégories."""
        from ui.dialogs.categories_dialog import CategoriesDialog

        dialog = CategoriesDialog(self, category_service=self.controller.db_manager.categories)
        dialog.exec()

    # Alias for backward compatibility
    _ouvrir_parametres = _open_parameters

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        """Libère les ressources UI/DB à la fermeture de la fenêtre."""
        try:
            self.controller.quit_loader()
            self.controller.close_session()
        finally:
            super().closeEvent(a0)
