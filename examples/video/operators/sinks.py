"""Sink operators for the video intelligence demo."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict

from sage.core.api.function.sink_function import SinkFunction


class TimelineSink(SinkFunction):
    """Persists per-frame insights as JSONL."""

    def __init__(self, output_path: str, preview_every: int = 10) -> None:
        super().__init__()
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.preview_every = max(1, preview_every)
        self.count = 0
        self.file = self.output_path.open("w", encoding="utf-8")

    def execute(self, data: Dict[str, Any]) -> None:
        safe_data = {
            key: value
            for key, value in data.items()
            if key not in {"frame", "pil_image", "resized_image"}
        }
        self.file.write(json.dumps(safe_data, ensure_ascii=False) + "\n")
        self.count += 1

        if self.count % self.preview_every == 0:
            scene = safe_data.get("primary_scene", "Unknown scene")
            objects = ", ".join(safe_data.get("top_object_labels", [])[:3])
            self.logger.info(
                "[timeline] frame=%s scene='%s' objects=%s",
                safe_data.get("frame_id"),
                scene,
                objects or "-",
            )

    def __del__(self) -> None:  # pragma: no cover - defensive cleanup
        if hasattr(self, "file") and self.file and not self.file.closed:
            self.file.close()


class SummarySink(SinkFunction):
    """Collects sliding-window summaries and writes a compact JSON report."""

    def __init__(self, summary_path: str) -> None:
        super().__init__()
        self.summary_path = Path(summary_path)
        self.summary_path.parent.mkdir(parents=True, exist_ok=True)
        self.records: list[Dict[str, Any]] = []

    def execute(self, data: Dict[str, Any]) -> None:
        self.records.append(data)

    def __del__(self) -> None:  # pragma: no cover - defensive cleanup
        if self.records:
            payload = {
                "window_count": len(self.records),
                "summaries": self.records,
            }
            with self.summary_path.open("w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)


class EventStatsSink(SinkFunction):
    """Aggregates event statistics and persists them on teardown."""

    def __init__(self, stats_path: str, log_every: int = 25) -> None:
        super().__init__()
        self.stats_path = Path(stats_path)
        self.stats_path.parent.mkdir(parents=True, exist_ok=True)
        self.counter: Counter[str] = Counter()
        self.total_events = 0
        self.log_every = max(1, log_every)

    def execute(self, event: Dict[str, Any]) -> None:
        event_type = event.get("event_type", "unknown")
        self.counter[event_type] += 1
        self.total_events += 1

        if self.total_events % self.log_every == 0:
            self.logger.info(
                "[events] processed=%d top=%s",
                self.total_events,
                self.counter.most_common(3),
            )

    def __del__(self) -> None:  # pragma: no cover - defensive cleanup
        if self.total_events:
            payload = {
                "total_events": self.total_events,
                "event_counts": dict(self.counter),
            }
            with self.stats_path.open("w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
