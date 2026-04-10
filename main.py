"""Point d'entree de l'application Qt."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


def _ensure_project_on_path() -> None:
    project_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(project_dir))


def _configure_headless_qt_if_needed() -> None:
    # Evite le crash Qt dans les environnements sans display/sandbox.
    is_headless_unix = (
        os.name != "nt" and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY")
    )
    is_ci_sandbox = os.environ.get("CODEX_CI") == "1"
    if is_ci_sandbox or is_headless_unix:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"


_ensure_project_on_path()
_configure_headless_qt_if_needed()

from PyQt6.QtWidgets import QApplication

from controllers.main_controller import MainController
from main_window import MainWindow

try:
    from styles.app_stylesheet import build_stylesheet
except ImportError:

    def build_stylesheet() -> str:
        return ""


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(build_stylesheet())

    # Create controller with user context
    controller = MainController(user={"nom": "Caissier 1", "role": "caissier"})

    # Create main window with controller (Passive View pattern)
    window = MainWindow(controller)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
