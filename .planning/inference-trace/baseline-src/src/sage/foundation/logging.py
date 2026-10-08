"""Small in-tree logging helpers for the consolidated SAGE core."""

from __future__ import annotations

import logging
import threading
from typing import Any


class CustomLogger:
    """Lightweight compatibility logger used by in-tree stream/runtime code."""

    _global_console_debug_enabled: bool = True
    _lock = threading.Lock()

    _LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    def __init__(
        self,
        name_or_outputs: str | list[tuple[str, str | int]] | None = None,
        outputs: list[tuple[str, str | int]] | None = None,
        name: str | None = None,
        log_base_folder: str | None = None,
    ) -> None:
        resolved_name = name or (name_or_outputs if isinstance(name_or_outputs, str) else None)
        self.name = resolved_name or "sage"
        self.log_base_folder = log_base_folder
        self.logger = logging.getLogger(self.name)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(handler)
        self.logger.propagate = False

        resolved_outputs = outputs
        if resolved_outputs is None and isinstance(name_or_outputs, list):
            resolved_outputs = name_or_outputs
        if resolved_outputs is None:
            resolved_outputs = [("console", "INFO")]

        levels = [self._extract_level(level) for _, level in resolved_outputs]
        self.logger.setLevel(min(levels) if levels else logging.INFO)

    def _extract_level(self, level: str | int) -> int:
        if isinstance(level, int):
            return level
        return self._LEVELS.get(level.upper(), logging.INFO)

    def update_output_level(self, target_index_or_name: int | str, new_level: str | int) -> None:
        self.logger.setLevel(self._extract_level(new_level))
        for handler in self.logger.handlers:
            handler.setLevel(self._extract_level(new_level))

    def debug(self, *args: Any, **kwargs: Any) -> None:
        if not self.is_global_console_debug_enabled():
            return
        self.logger.debug(*args, **kwargs)

    def info(self, *args: Any, **kwargs: Any) -> None:
        self.logger.info(*args, **kwargs)

    def warning(self, *args: Any, **kwargs: Any) -> None:
        self.logger.warning(*args, **kwargs)

    warn = warning

    def error(self, *args: Any, **kwargs: Any) -> None:
        self.logger.error(*args, **kwargs)

    def critical(self, *args: Any, **kwargs: Any) -> None:
        self.logger.critical(*args, **kwargs)

    @classmethod
    def disable_global_console_debug(cls) -> None:
        with cls._lock:
            cls._global_console_debug_enabled = False

    @classmethod
    def enable_global_console_debug(cls) -> None:
        with cls._lock:
            cls._global_console_debug_enabled = True

    @classmethod
    def is_global_console_debug_enabled(cls) -> bool:
        return cls._global_console_debug_enabled


__all__ = ["CustomLogger"]
