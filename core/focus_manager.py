from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QWidget


class FocusManager:
    """Manages focus restoration for widgets after dialogs close.

    Provides a simple mechanism to track a target widget and restore
    focus to it after blocking operations complete.
    """

    def __init__(self) -> None:
        self._target_widget: QWidget | None = None

    def set_focus_target(self, widget: QWidget | None) -> None:
        """Set the target widget for focus restoration.

        Args:
            widget: The widget to receive focus when restore_focus is called.
        """
        self._target_widget = widget

    def restore_focus(self) -> None:
        """Restore focus to the target widget.

        Uses QTimer.singleShot(0, ...) to defer focus setting to ensure
        the event loop has processed dialog close events.
        """
        if self._target_widget is None:
            return

        def _focus_and_select() -> None:
            if hasattr(self._target_widget, "focus_and_select"):
                self._target_widget.focus_and_select()
            else:
                self._target_widget.setFocus()

        QTimer.singleShot(0, _focus_and_select)

    def has_target(self) -> bool:
        """Check if a focus target is set."""
        return self._target_widget is not None
