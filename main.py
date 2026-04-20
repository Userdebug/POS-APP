"""Point d'entree de l'application Qt."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from datetime import datetime


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


def _setup_logging() -> logging.Logger:
    """Configure logging with both console and file output for debugging."""
    # Create logs directory
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(exist_ok=True)

    # Log file path with timestamp
    log_file = log_dir / f"pos_app_{datetime.now().strftime('%Y%m%d')}.log"

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler - INFO level
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler - DEBUG level
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Log the log file location
    logger.info(f"Log file: {log_file}")

    return logger


def _setup_qt_message_handler() -> None:
    """Install Qt message handler to capture Qt warnings and errors."""
    from PyQt6.QtCore import qInstallMessageHandler, QtMsgType

    def qt_message_handler(msg_type: QtMsgType, context, message: str):
        """Handle Qt messages and forward to Python logging."""
        level_map = {
            QtMsgType.QtDebugMsg: logging.DEBUG,
            QtMsgType.QtInfoMsg: logging.INFO,
            QtMsgType.QtWarningMsg: logging.WARNING,
            QtMsgType.QtCriticalMsg: logging.CRITICAL,
            QtMsgType.QtFatalMsg: logging.FATAL,
        }
        level = level_map.get(msg_type, logging.WARNING)

        # Format message with context info
        msg = f"[Qt] {message}"
        if context.file():
            msg += f" | {context.file()}:{context.line()}"

        logging.getLogger("Qt").log(level, msg)

    qInstallMessageHandler(qt_message_handler)


def _setup_exception_handler() -> None:
    """Install global exception handler to log uncaught exceptions."""

    def exception_handler(exc_type, exc_value, exc_traceback):
        """Log uncaught exceptions with traceback."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't log keyboard interrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logging.error(
            "Uncaught exception: %s: %s",
            exc_type.__name__,
            exc_value,
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = exception_handler


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
    _setup_logging()
    _setup_qt_message_handler()
    _setup_exception_handler()

    logging.info("=== POS Application Starting ===")
    logging.info(f"Python: {sys.version}")
    logging.info(f"Platform: {sys.platform}")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(build_stylesheet())

    # Create controller with user context
    controller = MainController(user={"nom": "Caissier 1", "role": "caissier"})

    # Create main window with controller (Passive View pattern)
    window = MainWindow(controller)
    window.show()

    logging.info("=== Main Window Shown ===")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
