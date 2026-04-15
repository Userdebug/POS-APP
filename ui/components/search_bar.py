"""Reusable search bar component with debounce and search filtering."""

from __future__ import annotations

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QWidget

DEFAULT_DEBOUNCE_MS: int = 300
DEFAULT_MIN_CHARS: int = 2


class SearchBar(QWidget):
    """Reusable search bar with debounce timer to prevent UI freezes.

    Features:
    - Configurable debounce delay (default 300ms)
    - Minimum character threshold (default 2)
    - Blocks repeated character spam (e.g., 'aaaa', '1111')
    - Clear button support

    Signals:
        search_changed(str): Emitted when search text changes after debounce.
            Empty string when search is cleared.
    """

    search_changed = pyqtSignal(str)

    def __init__(
        self,
        placeholder: str = "Rechercher...",
        debounce_ms: int = DEFAULT_DEBOUNCE_MS,
        min_chars: int = DEFAULT_MIN_CHARS,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the search bar.

        Args:
            placeholder: Placeholder text shown when input is empty.
            debounce_ms: Delay in milliseconds before emitting search.
            min_chars: Minimum characters required to trigger search.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._debounce_ms = debounce_ms
        self._min_chars = min_chars
        self._last_search = ""
        self._current_search = ""

        # Create debounce timer
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timer_timeout)

        self._setup_ui(placeholder)

    def _setup_ui(self, placeholder: str) -> None:
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Search input
        self._input = QLineEdit()
        self._input.setPlaceholderText(placeholder)
        self._input.setMaximumHeight(32)
        self._input.setClearButtonEnabled(True)
        self._input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._input, 1)

        # Store reference for focus handling
        self._input.setProperty("class", "search-input")

    def _on_text_changed(self, text: str) -> None:
        self._current_search = text
        # On ne stoppe plus le timer, on le redémarre systématiquement
        # Cela évite l'exécution immédiate qui fige l'UI
        self._timer.stop()
        self._timer.start(self._debounce_ms)

    def _on_timer_timeout(self) -> None:
        """Emit search signal when debounce timer fires."""
        text = self._current_search.strip().lower()

        # Rule: block repeated characters spam (e.g., 'aaaa', '1111')
        if len(text) > 3 and len(set(text)) == 1:
            return

        # Rule: minimum characters threshold
        if len(text) < self._min_chars:
            text = ""

        # Only emit if search text actually changed
        if text != self._last_search:
            self._last_search = text
            self.search_changed.emit(text)

    @property
    def text(self) -> str:
        """Return current search text."""
        return self._input.text()

    @property
    def search_text(self) -> str:
        """Return the last emitted search text."""
        return self._last_search

    def clear(self) -> None:
        """Clear the search input and reset state."""
        self._input.clear()
        self._last_search = ""
        self._current_search = ""

    def setFocus(self) -> None:
        """Set focus to the search input."""
        self._input.setFocus()

    def focus_and_select(self) -> None:
        """Set focus to the search input and select all text."""
        self._input.setFocus()
        self._input.selectAll()

    def setPlaceholderText(self, text: str) -> None:
        """Set placeholder text."""
        self._input.setPlaceholderText(text)

    def setEnabled(self, enabled: bool) -> None:
        """Enable or disable the search bar."""
        super().setEnabled(enabled)
        self._input.setEnabled(enabled)

    def isEnabled(self) -> bool:
        """Check if search bar is enabled."""
        return self._input.isEnabled()
