"""Label metrique reutilisable pour l'entete du dashboard."""

from PyQt6.QtWidgets import QLabel, QWidget


class MetricLabel(QLabel):
    """Petit composant de presentation pour les indicateurs chiffrés."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setProperty("metric", True)
        self.setStyleSheet("font-weight: bold; color: #f9fafb; padding: 4px;")
