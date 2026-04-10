"""Gestion des connexions SQLite pour le POS.

Ce module fournit un contexte de connexion SQLite avec gestion
automatique des transactions (commit/rollback) et des pragmas.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class ConnectionManager:
    """Gestionnaire de connexions SQLite avec transactions automatiques.

    Args:
        db_path: Chemin vers le fichier de base de donnees SQLite.
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def close(self) -> None:
        """Ferme toutes les connexions actives.

        Cette méthode tente de fermer les connexions en checkpointant
        le fichier WAL siactivé.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                # Checkpoint WAL to ensure all data is written
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                pass  # Ignore checkpoint errors
            finally:
                conn.close()
        except Exception:
            pass  # Ignore connection errors

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Contexte de connexion avec commit/rollback automatique.

        Active les cles etrangeres (PRAGMA foreign_keys = ON),
        commite en cas de succes, rollback en cas d'exception,
        et ferme toujours la connexion.

        Yields:
            sqlite3.Connection: Connexion configuree avec row_factory=Row.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            conn.close()
