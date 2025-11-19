"""Session persistence helpers for SAGE Gateway."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Protocol


class SessionStorage(Protocol):
    """Storage backend for persisting session state."""

    def load(self) -> list[dict]:
        """Return serialized session payloads."""
        ...

    def save(self, sessions: list[dict]) -> None:
        """Persist serialized session payloads."""
        ...


class FileSessionStore:
    """Simple JSON file store for gateway sessions."""

    def __init__(self, path: Path | None = None):
        self._path = path or (Path.home() / ".sage" / "gateway" / "sessions.json")
        self._lock = Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def default(cls) -> "FileSessionStore":
        return cls()

    def load(self) -> list[dict]:
        if not self._path.exists():
            return []
        with self._lock:
            try:
                text = self._path.read_text(encoding="utf-8")
                if not text.strip():
                    return []
                payload = json.loads(text)
                return payload.get("sessions", []) if isinstance(payload, dict) else []
            except json.JSONDecodeError:
                # corrupted file, ignore
                return []

    def save(self, sessions: list[dict]) -> None:
        with self._lock:
            data = {"sessions": sessions}
            self._path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )


__all__ = ["SessionStorage", "FileSessionStore"]
