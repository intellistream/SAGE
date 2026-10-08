"""Debug-oriented helper sinks owned by the main SAGE repository."""

from __future__ import annotations

from typing import Any

from .core import SinkFunction


class PrintSink(SinkFunction):
    """Small print sink used by `DataStream.print()`."""

    def __init__(
        self,
        prefix: str = "",
        separator: str = " | ",
        colored: bool = True,
        quiet: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.prefix = prefix
        self.separator = separator
        self.colored = colored
        self.quiet = quiet
        self._first_output = True

    def execute(self, data: Any) -> None:
        formatted = self._format_data(data)
        output = f"{self.prefix}{self.separator}{formatted}" if self.prefix else formatted

        if self._first_output and not self.quiet:
            print(f"🔍 Stream output: {output}")
            print("   (Further outputs logged. Check logs for details.)")
        else:
            print(output)
        self._first_output = False

    def _format_data(self, data: Any) -> str:
        if data is None:
            return "None"
        if isinstance(data, str | int | float | bool):
            return str(data)
        if isinstance(data, dict):
            return ", ".join(f"{k}={v}" for k, v in data.items())
        if isinstance(data, list | tuple):
            if len(data) <= 5:
                return str(data)
            preview = ", ".join(str(x) for x in data[:5])
            return f"[{preview}, ... (+{len(data) - 5} more)]"
        if hasattr(data, "__dict__"):
            attrs = getattr(data, "__dict__", {})
            if attrs:
                attr_str = ", ".join(f"{k}={v}" for k, v in list(attrs.items())[:3])
                return f"{data.__class__.__name__}({attr_str})"
            return f"{data.__class__.__name__}()"
        return str(data)


__all__ = ["PrintSink"]
