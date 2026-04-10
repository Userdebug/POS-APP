"""Initialise la base SQLite locale."""

import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.database import DatabaseManager

logger = logging.getLogger(__name__)


def main() -> None:
    manager = DatabaseManager(db_path="database/app.db", schema_path="database/schema.sql")
    logger.info("Base initialisee: %s", manager.db_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    main()
