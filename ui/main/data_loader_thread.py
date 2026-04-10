"""Thread de chargement asynchrone des produits."""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class DataLoaderThread(QThread):
    """Charge la liste des produits en arriere-plan."""

    data_loaded = pyqtSignal(list)

    def __init__(self, db_manager: Any) -> None:
        super().__init__()
        self.db_manager = db_manager

    def run(self) -> None:
        try:
            produits_db = self.db_manager.list_products()
        except (RuntimeError, sqlite3.Error) as exc:
            logger.error("chargement produits impossible: %s", exc)
            produits_db = []
        self.data_loaded.emit(produits_db)
