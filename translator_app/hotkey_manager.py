"""Global hotkey listener management."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal
from pynput import keyboard

from translator_app.exceptions import HotkeyError


class GlobalHotkeyManager(QObject):
    """Register a global hotkey that toggles the floating window."""

    activated = pyqtSignal()

    def __init__(self, hotkey: str) -> None:
        """Store the configured hotkey string."""
        super().__init__()
        self._hotkey = hotkey
        self._listener: Optional[keyboard.GlobalHotKeys] = None

    def start(self) -> None:
        """Start listening for the configured hotkey."""
        try:
            self._listener = keyboard.GlobalHotKeys({self._hotkey: self._on_activated})
            self._listener.start()
        except (ValueError, OSError) as exc:
            raise HotkeyError(
                f"Could not start global hotkey listener for '{self._hotkey}'."
            ) from exc

    def stop(self) -> None:
        """Stop the hotkey listener if it is currently running."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def _on_activated(self) -> None:
        """Emit a Qt signal when the hotkey is pressed."""
        self.activated.emit()

