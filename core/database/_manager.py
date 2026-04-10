"""Gestion de la base SQLite de l'application."""

from __future__ import annotations

import logging
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger(__name__)

from core.categories import CategoryRepository, CategoryService
from core.constants import (
    DATE_FORMAT_DAY,
    DATE_FORMAT_MONTH,
)
from core.database.auth_manager import AuthManager
from core.database.connection_manager import ConnectionManager
from core.database.daily_operations import DailyOperations
from core.database.margin_calculator import MarginCalculator
from core.database.parameter_manager import ParameterManager
from core.database.product_repository import ProductRepository
from core.database.schema_initializer import SchemaInitializer
from core.settings import (
    FinancialSettingsService,
    SettingsRepository,
    SettingsService,
)
from core.settings.migration import migrate_legacy_parameters
from repositories import (
    AchatRepository,
    ExpensesRepository,
    FollowupRepository,
    SalesRepository,
    SessionsRepository,
)


class DatabaseManager:

    def __init__(
        self, db_path: str = "database/app.db", schema_path: str = "database/schema.sql"
    ) -> None:
        base_dir = Path(__file__).resolve().parent.parent.parent

        if Path(db_path).is_absolute():
            self.db_path = Path(db_path)
        else:
            self.db_path = base_dir / db_path

        if Path(schema_path).is_absolute():
            self.schema_path = Path(schema_path)
        else:
            self.schema_path = base_dir / schema_path

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = ConnectionManager(self.db_path)
        self._schema = SchemaInitializer(self.schema_path)
        self.auth = AuthManager(self.get_parameter, self.set_parameter)
        self._params = ParameterManager(self._connect)
        # Settings system
        self._settings_repo = SettingsRepository(self._connect)
        self.settings = SettingsService(self._settings_repo)
        self.financial = FinancialSettingsService(self.settings)
        self.settings.initialize_default_categories()
        # Categories system
        self._category_repo = CategoryRepository(self._connect)
        self.categories = CategoryService(self._category_repo)
        self.products = ProductRepository(self._connect, self._resolve_category_ids)
        self.daily_ops = DailyOperations(
            self._connect,
            self._day_bounds,
            self._month_bounds,
            self._today_iso,
            self._current_month_iso,
            self.get_tax,
        )
        self.margins = MarginCalculator(
            self._connect,
            self._day_bounds,
            self._today_iso,
            self.daily_ops.get_daily_closure_ca,
            self.daily_ops.get_daily_closure_by_category,
        )
        self._init_db()
        self.sessions = SessionsRepository(self._connect)
        self.expenses = ExpensesRepository(
            connect=self._connect,
            day_bounds=self._day_bounds,
            today_iso=self._today_iso,
        )
        self.achats = AchatRepository(
            connect=self._connect,
            today_iso=self._today_iso,
        )
        self.sales = SalesRepository(
            connect=self._connect,
            day_bounds=self._day_bounds,
        )
        self.followups = FollowupRepository(
            connect=self._connect,
            today_iso=self._today_iso,
            day_bounds=self._day_bounds,
            resolve_category_ids=self._resolve_category_ids,
            daily_collecte_provider=self.get_daily_category_collecte,
            daily_theoretical_margin_provider=self.get_daily_theoretical_margin_by_category,
            achats_receptions_provider=self.achats.get_purchase_achats_by_category,
            upsert_daily_closure_by_category=self.upsert_daily_closure_by_category,
        )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Delegate to ConnectionManager for connection handling."""
        with self._connection.connect() as conn:
            yield conn

    def _day_bounds(self, day: str) -> tuple[str, str]:
        for fmt in ["%d/%m/%y", "%Y-%m-%d"]:
            try:
                start = datetime.strptime(day, fmt)
                end = start + timedelta(days=1)
                return start.strftime(DATE_FORMAT_DAY), end.strftime(DATE_FORMAT_DAY)
            except ValueError:
                continue
        raise ValueError(f"Unable to parse date: {day}")

    def _month_bounds(self, month: str) -> tuple[str, str]:
        for fmt in ["%d/%m/%y", "%Y-%m-%d"]:
            try:
                start = datetime.strptime(f"{month}-01", fmt)
                next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
                return start.strftime(DATE_FORMAT_DAY), next_month.strftime(DATE_FORMAT_DAY)
            except ValueError:
                continue
        raise ValueError(f"Unable to parse month: {month}")

    def _today_iso(self) -> str:
        return datetime.now().strftime(DATE_FORMAT_DAY)

    def _current_month_iso(self) -> str:
        return datetime.now().strftime(DATE_FORMAT_MONTH)

    @staticmethod
    def _compute_margin_percent(
        reference_value: int,
        margin_value: int,
        *,
        actual_value: int | None,
        zero_if_reference_is_zero: bool = False,
    ) -> float | None:
        return MarginCalculator.compute_margin_percent(
            reference_value,
            margin_value,
            actual_value=actual_value,
            zero_if_reference_is_zero=zero_if_reference_is_zero,
        )

    def _resolve_category_ids(
        self,
        conn: sqlite3.Connection,
        category_names: list[str],
    ) -> dict[str, int]:
        if not category_names:
            return {}
        unique_names = sorted({name for name in category_names if name})
        if not unique_names:
            return {}

        conn.executemany(
            "INSERT INTO categories (nom) VALUES (?) ON CONFLICT(nom) DO NOTHING",
            [(name,) for name in unique_names],
        )

        category_map: dict[str, int] = {}
        chunk_size = 400
        for offset in range(0, len(unique_names), chunk_size):
            chunk = unique_names[offset : offset + chunk_size]
            placeholders = ",".join("?" for _ in chunk)
            rows = conn.execute(
                f"SELECT id, nom FROM categories WHERE nom IN ({placeholders})",
                tuple(chunk),
            ).fetchall()
            for row in rows:
                category_map[str(row["nom"])] = int(row["id"])
        return category_map

    def _init_db(self) -> None:
        try:
            self._schema.init_database(self._connect)
            self.auth.ensure_admin_pin_initialized()
            self.auth.migrate_legacy_admin_pin_if_needed()
            migrate_legacy_parameters(self)
        except (OSError, sqlite3.Error) as exc:
            raise RuntimeError(f"initialisation base impossible: {exc}") from exc

    def get_parameter(self, key: str, default: str | None = None) -> str | None:
        # Try new settings system first
        item = self.settings.get_item(key)
        if item:
            return item.valeur
        # Fallback to legacy parametres table
        return self._params.get(key, default)

    # Alias for backward compatibility
    get_param = get_parameter

    def get_setting(self, key: str, default: str = "") -> str:
        """Récupère une valeur de la table settings (alias pour get_parameter).

        Args:
            key: Clé du paramètre à récupérer
            default: Valeur par défaut si la clé n'existe pas

        Returns:
            La valeur du paramètre ou default si non trouvé
        """
        result = self.get_parameter(key)
        return result if result is not None else default

    def set_parameter(self, key: str, value: str, description: str | None = None) -> None:
        # Try to determine type and use new settings system
        # Infer type based on value format
        if value in ("0", "1") and key not in ("TVA_TAUX",):
            value_type = "boolean"
        elif key == "TVA_TAUX":
            value_type = "float"
        elif key in ("COFFRE_TOTAL", "backup_retention"):
            value_type = "int"
        else:
            value_type = "string"

        # Determine category based on key
        category_map = {
            "TVA_TAUX": "financial",
            "autosave_enabled": "general",
            "backup_dir": "general",
            "backup_retention": "general",
            "APP_MODE": "display",
            "COFFRE_TOTAL": "financial",
            "DAILY_RESET_PENDING": "general",
            "LAST_CLOSED_DATE": "general",
        }
        category_key = category_map.get(key, "general")

        try:
            self.settings.set_item(
                key=key,
                value=value,
                value_type=value_type,
                description=description,
                category_key=category_key,
            )
        except ValueError:
            # Fallback to legacy
            self._params.set(key, value, description)

    def get_tax(self, default: float = 20.0) -> float:
        return self.financial.get_tva_rate(default)

    def set_tax(self, tax_rate: float) -> None:
        self.financial.set_tva_rate(tax_rate)

    def get_admin_pin(self, default: str = "1234") -> str:
        return self.auth.get_admin_pin(default)

    def set_admin_pin(self, pin: str) -> None:
        self.auth.set_admin_pin(pin)

    def verify_admin_pin(self, pin: str) -> bool:
        return self.auth.verify_admin_pin(pin)

    def set_user_registration_code(self, operateur_id: int, code: str) -> None:
        self.auth.set_user_registration_code(operateur_id, code)

    def verify_user_registration_code(self, operateur_id: int, code: str) -> bool:
        return self.auth.verify_user_registration_code(operateur_id, code)

    def open_db_session(self, seller_name: str, access_right: str) -> tuple[int, int]:
        return self.sessions.open_session(seller_name, access_right)

    def close_db_session(self, session_id: int) -> None:
        self.sessions.close_session(session_id)

    # Alias for backward compatibility
    close_session = close_db_session

    def upsert_products(self, produits: list[dict[str, Any]]) -> None:
        self.products.upsert_products(produits)

    def list_products(self) -> list[dict[str, Any]]:
        return self.products.list_products()

    def get_produit_by_id(self, produit_id: int) -> dict[str, Any] | None:
        return self.products.get_produit_by_id(produit_id)

    def update_derniere_verification(self, produit_id: int, date_verification: str) -> None:
        self.products.update_derniere_verification(produit_id, date_verification)

    def toggle_promo(self, produit_id: int, en_promo: bool) -> None:
        self.products.toggle_promo(produit_id, en_promo)

    def ensure_supplier(self, supplier: dict[str, Any] | None) -> int:
        return self.achats.ensure_supplier(supplier)

    def get_supplier_by_code(self, code: str) -> dict[str, Any] | None:
        return self.achats.get_supplier_by_code(code)

    def record_achat_line(
        self,
        *,
        jour: str,
        fournisseur: dict[str, Any] | None,
        numero_facture: str,
        produit_id: int,
        quantite: int,
        pa_unitaire: int,
        prc_unitaire: int,
        pv_unitaire: int,
    ) -> int:
        return self.achats.record_achat_line(
            day=jour,
            supplier=fournisseur,
            invoice_number=numero_facture,
            product_id=produit_id,
            quantity=quantite,
            unit_cost=pa_unitaire,
            unit_price=prc_unitaire,
            retail_price=pv_unitaire,
        )

    # Alias for backward compatibility
    record_reception_line = record_achat_line

    def get_stock_value_by_category(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT
                    COALESCE(c.nom, 'Sans categorie') AS categorie,
                    SUM(p.stock_boutique + p.stock_reserve) AS quantite_totale,
                    SUM((p.stock_boutique + p.stock_reserve) * p.pa) AS valeur_stock
                FROM produits p
                LEFT JOIN categories c ON c.id = p.categorie_id
                GROUP BY COALESCE(c.nom, 'Sans categorie')
                ORDER BY categorie ASC
                """).fetchall()
            return [dict(row) for row in rows]

    def get_daily_category_evolution(self, jour: str | None = None) -> list[dict[str, Any]]:
        return self.daily_ops.get_daily_category_evolution(jour)

    def get_monthly_nfr_by_category(self, mois: str | None = None) -> list[dict[str, Any]]:
        return self.daily_ops.get_monthly_nfr_by_category(mois)

    def set_daily_closure_revenue(self, day: str, ca_ttc_final: int, note: str = "") -> None:
        self.daily_ops.set_daily_closure_revenue(day, ca_ttc_final, note)

    def upsert_daily_closure_by_category(self, jour: str, values: list[dict[str, Any]]) -> None:
        self.daily_ops.upsert_daily_closure_by_category(jour, values)

    def get_daily_closure_by_category(self, jour: str) -> list[dict[str, Any]]:
        return self.daily_ops.get_daily_closure_by_category(jour)

    def get_daily_closure_ca(self, jour: str) -> int | None:
        return self.daily_ops.get_daily_closure_ca(jour)

    def get_daily_theoretical_margin_by_category(
        self, jour: str | None = None
    ) -> list[dict[str, Any]]:
        return self.margins.get_daily_theoretical_margin_by_category(jour)

    def get_daily_margin_summary(self, jour: str | None = None) -> dict[str, int | float | None]:
        return self.margins.get_daily_margin_summary(jour)

    def get_daily_margin_by_category(self, jour: str | None = None) -> list[dict[str, Any]]:
        return self.margins.get_daily_margin_by_category(jour)

    def get_daily_category_collecte(self, jour: str | None = None) -> list[dict[str, Any]]:
        return self.margins.get_daily_category_collecte(jour)

    def get_daily_tracking_by_category(self, day: str | None = None) -> list[dict[str, Any]]:
        return self.followups.get_daily_tracking_by_category(day)

    def _sync_unclosed_day_metrics(self, day: str) -> None:
        self.followups._sync_unclosed_day_metrics(day)

    def get_daily_tracking_by_category_raw(self, day: str) -> list[dict[str, Any]]:
        return self.followups.get_daily_tracking_by_category_raw(day)

    def _initialize_daily_tracking_if_missing(self, day: str) -> None:
        self.followups._initialize_daily_tracking_if_missing(day)

    def upsert_daily_tracking(self, day: str, rows: list[dict[str, Any]]) -> None:
        self.followups.upsert_daily_tracking(day, rows)

    def save_daily_tracking_edits(self, day: str, rows: list[dict[str, Any]]) -> None:
        self.followups.save_daily_tracking_edits(day, rows)

    def get_purchase_achats_by_category(self, day: str | None = None) -> list[dict[str, Any]]:
        return self.achats.get_purchase_achats_by_category(day)

    def list_daily_achats(self, day: str) -> list[dict[str, Any]]:
        return self.achats.list_daily_achats(day)

    def total_daily_achats(self, day: str) -> int:
        return self.achats.total_daily_achats(day)

    def _initialize_daily_tracking_form_if_missing(self, day: str) -> None:
        self.followups._initialize_daily_tracking_form_if_missing(day)

    def get_daily_tracking_form(self, day: str | None = None) -> list[dict[str, Any]]:
        return self.followups.get_daily_tracking_form(day)

    # Alias for backward compatibility
    get_daily_suivi_form = get_daily_tracking_form

    def save_daily_tracking_form_edits(
        self,
        day: str,
        rows: list[dict[str, Any]],
        force_admin: bool = False,
    ) -> None:
        self.followups.save_daily_tracking_form_edits(day, rows, force_admin=force_admin)

    def close_day_from_tracking_form(self, day: str) -> None:
        self.followups.close_day_from_tracking_form(day)

    def close_day_and_prepare_next(
        self,
        jour: str,
        final_ca_by_category: list[dict[str, Any]],
    ) -> None:
        self.followups.close_day_and_prepare_next(jour, final_ca_by_category)

    def get_category_collection_interval(
        self,
        date_debut: str,
        date_fin: str,
    ) -> list[dict[str, Any]]:
        return self.followups.get_category_collection_interval(date_debut, date_fin)

    def record_sale(
        self,
        *,
        produit_id: int,
        produit_nom: str,
        quantite: int,
        prix_unitaire: int,
        session_id: int,
    ) -> dict:
        return self.sales.record_sale(
            produit_id=produit_id,
            produit_nom=produit_nom,
            quantite=quantite,
            prix_unitaire=prix_unitaire,
            session_id=session_id,
        )

    def list_daily_sales(self, day: str) -> list[dict[str, Any]]:
        return self.sales.list_daily_sales(day)

    def delete_sale(self, vente_id: int, operateur_id: int | None = None) -> bool:
        """Supprime une vente par son identifiant."""
        return self.sales.delete_sale(vente_id)

    # Alias for backward compatibility
    list_ventes_jour = list_daily_sales

    def get_oasis_stats(self, jour: str) -> list[dict[str, Any]]:
        return self.sales.get_oasis_stats(jour)

    def get_detailed_daily_sales(self, day: str) -> list[dict[str, Any]]:
        return self.sales.get_detailed_daily_sales(day)

    def get_guest_stats(self, jour: str) -> list[dict[str, Any]]:
        return self.sales.get_guest_stats(jour)

    def next_product_id(self) -> int:
        return self.products.next_product_id()

    def log_movement(
        self,
        *,
        produit_id: int,
        type_mouvement: str,
        quantite: int,
        raison: str | None,
        pa_unitaire: int,
        stock_b_avant: int,
        stock_b_apres: int,
        stock_r_avant: int,
        stock_r_apres: int,
        operateur_id: int,
        session_id: int,
        vendeur_nom: str,
    ) -> None:
        valeur = int(pa_unitaire) * int(quantite)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO mouvements_stock (
                    produit_id, type_mouvement, quantite, raison, valeur,
                    stock_boutique_avant, stock_boutique_apres,
                    stock_reserve_avant, stock_reserve_apres,
                    operateur_id, session_id, vendeur_nom
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(produit_id),
                    str(type_mouvement),
                    int(quantite),
                    raison,
                    valeur,
                    int(stock_b_avant),
                    int(stock_b_apres),
                    int(stock_r_avant),
                    int(stock_r_apres),
                    int(operateur_id),
                    int(session_id),
                    str(vendeur_nom),
                ),
            )

    def log_removed_product(
        self,
        *,
        nom: str,
        categorie: str,
        quantite: int,
        pa_unitaire: int,
        raison: str,
        operateur_id: int,
        session_id: int,
        vendeur_nom: str,
    ) -> None:
        valeur = int(pa_unitaire) * int(quantite)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO historique_produits_enleves (
                    nom, categorie, quantite, valeur, raison,
                    operateur_id, session_id, vendeur_nom
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(nom),
                    str(categorie),
                    int(quantite),
                    valeur,
                    str(raison),
                    int(operateur_id),
                    int(session_id),
                    str(vendeur_nom),
                ),
            )

    def add_expense(
        self, designation: str, valeur: int, remarque: str = "", date_depense: str | None = None
    ) -> None:
        self.expenses.add_expense(
            designation=designation,
            valeur=valeur,
            remarque=remarque,
            date_depense=date_depense,
        )

    def list_daily_expenses(self, day: str | None = None) -> list[dict[str, Any]]:
        return self.expenses.list_daily_expenses(day)

    # Alias for backward compatibility
    list_depenses_jour = list_daily_expenses

    def total_daily_expenses(self, day: str | None = None) -> int:
        return self.expenses.total_daily_expenses(day)

    def total_daily_sales(self, day: str | None = None) -> int:
        if day is None:
            from datetime import date

            day = date.today().isoformat()
        return self.sales.total_daily_sales(day)

    def total_daily_achats(self, day: str | None = None) -> int:
        if day is None:
            from datetime import date

            day = date.today().isoformat()
        return self.achats.total_daily_achats(day)

    # Alias for backward compatibility
    total_depenses_jour = total_daily_expenses
    total_ventes_jour = total_daily_sales
    total_factures_jour = total_daily_achats

    def update_expense(
        self, expense_id: int, designation: str, valeur: int, remarque: str = ""
    ) -> None:
        self.expenses.update_expense(expense_id, designation, valeur, remarque)

    def delete_expense(self, expense_id: int) -> None:
        self.expenses.delete_expense(expense_id)

    def decrement_stock(self, produit_id: int, quantite: int) -> None:
        """Decrements the stock_boutique for a product."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE produits
                SET stock_boutique = stock_boutique - ?
                WHERE id = ?
                """,
                (quantite, produit_id),
            )

    def decrement_stock_batch(self, items: list[dict]) -> None:
        """Batch decrement stock for multiple products in a single SQL statement.

        Args:
            items: List of dicts with 'id' (produit_id) and 'qte' (quantite) keys.
                   Only items with valid produit_id and positive quantite are processed.
        """
        if not items:
            return

        # Filter valid items
        valid_items = [
            (item["qte"], item["id"]) for item in items if item.get("id") and item.get("qte", 0) > 0
        ]

        if not valid_items:
            return

        # Build CASE statement for batch update
        case_parts = ["WHEN id = ? THEN stock_boutique - ?" for _ in valid_items]
        params = []
        for qte, prod_id in valid_items:
            params.extend([prod_id, qte])

        case_sql = " ".join(case_parts)

        with self._connect() as conn:
            conn.execute(
                f"""
                UPDATE produits
                SET stock_boutique = CASE
                    {case_sql}
                    ELSE stock_boutique
                END
                WHERE id IN ({','.join(['?' for _ in valid_items])})
                """,
                params + [prod_id for _, prod_id in valid_items],
            )

    def export_database(self, output_path: str | Path) -> dict[str, Any]:
        """Exporter la base SQLite vers un fichier.

        Args:
            output_path: Chemin du fichier de destination (.db, .sqlite, .sqlite3).

        Returns:
            Dict avec les informations de l'export (taille du fichier, etc.).

        Raises:
            OSError: Si l'export échoue.
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Close any existing connections to ensure data is flushed
        self._connection.close()

        # Copy the database file (and WAL if exists)
        db_path = Path(self.db_path)
        try:
            # Copy main database file
            shutil.copy2(db_path, output_file)

            # Also copy WAL file if it exists
            wal_path = Path(f"{db_path}-wal")
            if wal_path.exists():
                shutil.copy2(wal_path, f"{output_file}-wal")

            # Copy SHM file if it exists
            shm_path = Path(f"{db_path}-shm")
            if shm_path.exists():
                shutil.copy2(shm_path, f"{output_file}-shm")

            logger.info(f"Database exported to {output_file}")
            return {
                "success": True,
                "path": str(output_file),
                "size": output_file.stat().st_size,
            }

        except OSError as e:
            logger.exception(f"Failed to export database: {e}")
            raise OSError(f"Export échoué: {e}") from e

    def import_database(self, input_path: str | Path) -> dict[str, Any]:
        """Importer une base SQLite depuis un fichier.

        Args:
            input_path: Chemin du fichier source (.db, .sqlite, .sqlite3).

        Returns:
            Dict avec les informations de l'import.

        Raises:
            FileNotFoundError: Si le fichier source n'existe pas.
            OSError: Si l'import échoue.
        """
        input_file = Path(input_path)
        if not input_file.exists():
            raise FileNotFoundError(f"Fichier non trouvé: {input_path}")

        # Validate it's a SQLite database
        try:
            with sqlite3.connect(input_file) as test_conn:
                test_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        except sqlite3.Error as e:
            raise ValueError(f"Fichier SQLite invalide: {e}")

        # Close connections before replacing
        self._connection.close()

        db_path = Path(self.db_path)
        backup_path = db_path.with_suffix(db_path.suffix + ".import_backup")

        try:
            # Create backup of current database
            shutil.copy2(db_path, backup_path)

            # Copy the new database over
            shutil.copy2(input_file, db_path)

            # Handle WAL file
            input_wal = Path(f"{input_file}-wal")
            if input_wal.exists():
                shutil.copy2(input_wal, f"{db_path}-wal")

            # Handle SHM file
            input_shm = Path(f"{input_file}-shm")
            if input_shm.exists():
                shutil.copy2(input_shm, f"{db_path}-shm")

            logger.info(f"Database imported from {input_file}")

            # Clean up backup after successful import
            if backup_path.exists():
                backup_path.unlink()

            return {
                "success": True,
                "path": str(input_file),
                "backup": str(backup_path),
            }

        except OSError as e:
            logger.exception(f"Failed to import database: {e}")
            # Restore from backup if import failed
            if backup_path.exists():
                shutil.copy2(backup_path, db_path)
            raise OSError(f"Import échoué: {e}") from e

    def restore_database(self, backup_path: str | Path) -> dict[str, Any]:
        """Restaurer la base SQLite depuis une sauvegarde.

        Args:
            backup_path: Chemin du fichier de sauvegarde (.db, .sqlite, .sqlite3).

        Returns:
            Dict avec les informations de la restauration.

        Raises:
            FileNotFoundError: Si le fichier de sauvegarde n'existe pas.
            OSError: Si la restauration échoue.
        """
        backup_file = Path(backup_path)
        if not backup_file.exists():
            raise FileNotFoundError(f"Sauvegarde non trouvée: {backup_path}")

        # Validate it's a SQLite database
        try:
            with sqlite3.connect(backup_file) as test_conn:
                test_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        except sqlite3.Error as e:
            raise ValueError(f"Fichier de sauvegarde invalide: {e}")

        # Close connections before replacing
        self._connection.close()

        db_path = Path(self.db_path)
        # Create应急 backup before restore
        emergency_backup = db_path.with_suffix(
            db_path.suffix + f".restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        try:
            # Create emergency backup
            shutil.copy2(db_path, emergency_backup)

            # Copy the backup file over
            shutil.copy2(backup_file, db_path)

            # Handle WAL file
            backup_wal = Path(f"{backup_file}-wal")
            if backup_wal.exists():
                shutil.copy2(backup_wal, f"{db_path}-wal")

            # Handle SHM file
            backup_shm = Path(f"{backup_file}-shm")
            if backup_shm.exists():
                shutil.copy2(backup_shm, f"{db_path}-shm")

            logger.info(f"Database restored from {backup_file}")

            return {
                "success": True,
                "path": str(backup_file),
                "emergency_backup": str(emergency_backup),
            }

        except OSError as e:
            logger.exception(f"Failed to restore database: {e}")
            # Restore from emergency backup if restore failed
            if emergency_backup.exists():
                shutil.copy2(emergency_backup, db_path)
            raise OSError(f"Restauration échouée: {e}") from e

    def list_database_backups(self, directory: str | Path | None = None) -> list[dict[str, Any]]:
        """Lister les fichiers de sauvegarde de la base de données.

        Args:
            directory: Répertoire à scanner. Si None, utilise le répertoire de la base.

        Returns:
            Liste des fichiers de sauvegarde avec leurs informations.
        """
        search_dir = Path(directory) if directory else Path(self.db_path).parent

        if not search_dir.exists():
            return []

        backups = []
        for f in sorted(search_dir.glob("*.db"), reverse=True):
            # Exclude emergency backups
            if "restore_" in f.name or "import_backup" in f.name:
                continue

            stat = f.stat()
            backups.append(
                {
                    "filename": f.name,
                    "path": str(f),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )

        return backups
