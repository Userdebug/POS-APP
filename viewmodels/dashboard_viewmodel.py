"""ViewModel des indicateurs de tableau de bord."""

from dataclasses import dataclass

from core.database import DatabaseManager
from services.suivi_journalier_service import DailyTrackingService


@dataclass
class DashboardTotals:
    total_depenses: int
    total_ventes: int
    total_caisse: int


class DashboardViewModel:
    """Calcule les valeurs metier affichees dans le header principal."""

    def __init__(
        self, db_manager: DatabaseManager, tracking_service: DailyTrackingService | None = None
    ) -> None:
        self.db_manager = db_manager
        self.tracking_service = tracking_service

    def compute_totals_for_day(self, jour: str, total_coffre: int = 0) -> DashboardTotals:
        depenses = int(self.db_manager.total_depenses_jour(jour))
        # Ajouter le total des factures journalières aux dépenses
        factures = int(self.db_manager.total_factures_jour(jour))
        ventes = int(self.db_manager.total_ventes_jour(jour))
        # Dépenses totales = dépenses + factures
        total_depenses = depenses + factures
        caisse = ventes - total_depenses - total_coffre
        return DashboardTotals(
            total_depenses=total_depenses,
            total_ventes=ventes,
            total_caisse=caisse,
        )
