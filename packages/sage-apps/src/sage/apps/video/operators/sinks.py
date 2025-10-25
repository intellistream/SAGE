"""Sink operators for the video intelligence demo."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from sage.common.core.functions.sink_function import SinkFunction


class TimelineSink(SinkFunction):
    """Persists per-frame insights as JSONL."""

    def __init__(self, output_path: str, preview_every: int = 10) -> None:
        super().__init__()
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.preview_every = max(1, preview_every)
        self.count = 0
        self.file = self.output_path.open("w", encoding="utf-8")

    def execute(self, data: dict[str, Any]) -> None:
        safe_data = {
            key: value
            for key, value in data.items()
            if key not in {"frame", "pil_image", "resized_image"}
        }
        self.file.write(json.dumps(safe_data, ensure_ascii=False) + "\n")
        self.count += 1

        # Enhanced console output for better visibility
        if self.count % self.preview_every == 0:
            frame_id = safe_data.get("frame_id", "?")
            timestamp = safe_data.get("timestamp_seconds", 0)
            scene = safe_data.get("primary_scene", "Unknown scene")
            objects = ", ".join(safe_data.get("top_object_labels", [])[:3])
            brightness = safe_data.get("brightness", 0)

            print(f"\n{'='*70}")
            print(f"📹 Frame {frame_id} @ {timestamp:.2f}s")
            print(f"   Scene: {scene}")
            print(f"   Objects: {objects or 'none detected'}")
            print(f"   Brightness: {brightness:.1f}")

            # Show scene scores if available
            scene_scores = safe_data.get("scene_scores", {})
            if scene_scores:
                top_scenes = sorted(scene_scores.items(), key=lambda x: x[1], reverse=True)[:3]
                print(f"   Top scenes: {', '.join(f'{s}({v:.2f})' for s, v in top_scenes)}")

            print(f"{'='*70}")

    def __del__(self) -> None:  # pragma: no cover - defensive cleanup
        if hasattr(self, "file") and self.file and not self.file.closed:
            self.file.close()


class SummarySink(SinkFunction):
    """Collects sliding-window summaries and writes a compact JSON report."""

    def __init__(self, summary_path: str) -> None:
        super().__init__()
        self.summary_path = Path(summary_path)
        self.summary_path.parent.mkdir(parents=True, exist_ok=True)
        self.records: list[dict[str, Any]] = []

    def execute(self, data: dict[str, Any]) -> None:
        self.records.append(data)

        # Print summary to console
        window_id = len(self.records)
        summary_text = data.get("summary", "")
        start_time = data.get("window_start_seconds", 0)
        end_time = data.get("window_end_seconds", 0)

        print(f"\n🎬 Summary Window #{window_id} ({start_time:.1f}s - {end_time:.1f}s)")
        print(f"   {summary_text[:200]}{'...' if len(summary_text) > 200 else ''}")

        # Show memory recall if available
        memory_recall = data.get("memory_recall", [])
        if memory_recall:
            print(f"   💭 Memory recalls: {len(memory_recall)} similar moments found")

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

    def execute(self, event: dict[str, Any]) -> None:
        event_type = event.get("event_type", "unknown")
        self.counter[event_type] += 1
        self.total_events += 1

        if self.total_events % self.log_every == 0:
            top_events = self.counter.most_common(3)
            top_str = ", ".join(f"{t}({c})" for t, c in top_events)
            print(f"\n📊 Events processed: {self.total_events}")
            print(f"   Top events: {top_str}")

    def __del__(self) -> None:  # pragma: no cover - defensive cleanup
        if self.total_events:
            payload = {
                "total_events": self.total_events,
                "event_counts": dict(self.counter),
            }
            with self.stats_path.open("w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
