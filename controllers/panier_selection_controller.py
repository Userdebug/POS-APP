"""Controleur pur pour la navigation/selection des lignes panier."""

from __future__ import annotations

from dataclasses import dataclass

from ui.zone_panier.mode_utils import _normalize_mode


@dataclass(frozen=True)
class ReceptionNextAction:
    add_new_row: bool
    next_row: int | None


class PanierSelectionController:
    """Centralise les regles de selection de lignes selon le mode et le contexte."""

    @staticmethod
    def refresh_basket_target(
        *,
        row_count: int,
        previous_active_row: int,
        has_brouillon: bool,
    ) -> int | None:
        if row_count <= 0:
            return None
        if has_brouillon:
            return row_count - 1
        # After validation (no brouillon), always select the last row (newly added line)
        return row_count - 1

    @staticmethod
    def refresh_invoice_target(*, row_count: int, previous_active_row: int) -> int | None:
        if row_count <= 0:
            return None
        if 0 <= previous_active_row < row_count:
            return previous_active_row
        return row_count - 1

    @staticmethod
    def next_cash_register_row(*, current_row: int, row_count: int) -> int | None:
        if current_row < 0 or row_count <= 0:
            return None
        return min(current_row + 1, row_count - 1)

    @staticmethod
    def next_reception_action(*, current_row: int, items_count: int) -> ReceptionNextAction:
        if items_count <= 0:
            return ReceptionNextAction(add_new_row=True, next_row=None)
        if current_row < 0:
            current_row = 0
        next_row = current_row + 1
        if next_row >= items_count:
            return ReceptionNextAction(add_new_row=True, next_row=None)
        return ReceptionNextAction(add_new_row=False, next_row=next_row)

    @staticmethod
    def validation_enabled(
        *,
        mode: str,
        has_brouillon: bool,
        has_achats_brouillon: bool,
        panier_row_count: int,
        panier_current_row: int,
        facture_row_count: int,
        facture_current_row: int,
    ) -> bool:
        """Check if validation is enabled for the current mode.

        Unified logic for both Caisse and Reception modes - both use draft line mechanism.
        """
        # Normalize mode (e.g., "caisse" -> "vente", "reception" -> "achat")
        mode = _normalize_mode(mode)

        if mode == "vente":
            # Vente mode: validate draft line or selected row
            if has_brouillon:
                return True
            return panier_row_count > 0 and 0 <= panier_current_row < panier_row_count

        # Achat mode: now also uses draft line (same as Vente)
        if mode == "achat":
            if has_achats_brouillon:
                return True
            return facture_row_count > 0 and 0 <= facture_current_row < facture_row_count

        return False

    @staticmethod
    def can_validate_quantity(
        *,
        produit_id: int | None,
        requested_qte: int,
        available_stock: int,
    ) -> tuple[bool, str]:
        """Check if a quantity can be validated based on available stock.

        Args:
            produit_id: The product ID (None for new products)
            requested_qte: The quantity requested
            available_stock: The current stock available

        Returns:
            Tuple of (can_validate, error_message)
            - can_validate: True if validation is allowed, False if stock is insufficient
            - error_message: Error message if validation not allowed
        """
        # Allow new products (no ID) without stock check
        if not produit_id:
            return True, ""

        # Allow zero or negative quantities
        if requested_qte <= 0:
            return True, ""

        # Check stock
        if requested_qte > available_stock:
            msg = f"Stock insuffisant! Actuel: {available_stock}, Demandé: {requested_qte}"
            return False, msg

        return True, ""
