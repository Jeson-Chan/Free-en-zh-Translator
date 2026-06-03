"""Translation history persistence."""

from __future__ import annotations

import json
from pathlib import Path

from translator_app.constants import HISTORY_FILE_NAME, MAX_HISTORY_ITEMS
from translator_app.exceptions import HistoryError
from translator_app.models import HistoryEntry


class HistoryManager:
    """Load and store recent translation history."""

    def __init__(self, root_path: Path) -> None:
        """Store the project root used for the history file."""
        self._history_path = root_path / HISTORY_FILE_NAME

    @property
    def history_path(self) -> Path:
        """Expose the absolute history file path."""
        return self._history_path

    def load_entries(self) -> list[HistoryEntry]:
        """Return all persisted history entries."""
        if not self._history_path.exists():
            return []

        try:
            payload = json.loads(self._history_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HistoryError(
                f"Invalid JSON in history file: {self._history_path}"
            ) from exc
        except OSError as exc:
            raise HistoryError(
                f"Could not read history file: {self._history_path}"
            ) from exc

        if not isinstance(payload, list):
            raise HistoryError("History file must contain a JSON array.")

        try:
            return [HistoryEntry.from_dict(item) for item in payload]
        except KeyError as exc:
            raise HistoryError("History file contains incomplete entries.") from exc

    def add_entry(self, entry: HistoryEntry) -> None:
        """Append a history entry and keep only the most recent items."""
        entries = self.load_entries()
        entries.insert(0, entry)
        trimmed_entries = entries[:MAX_HISTORY_ITEMS]

        try:
            self._history_path.write_text(
                json.dumps(
                    [item.to_dict() for item in trimmed_entries],
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except OSError as exc:
            raise HistoryError(
                f"Could not write history file: {self._history_path}"
            ) from exc

    def clear_entries(self) -> None:
        """Remove all persisted history entries."""
        try:
            self._history_path.write_text("[]", encoding="utf-8")
        except OSError as exc:
            raise HistoryError(
                f"Could not clear history file: {self._history_path}"
            ) from exc
