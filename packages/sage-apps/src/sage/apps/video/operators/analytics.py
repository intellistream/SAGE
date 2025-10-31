"""Analytics operators for the video intelligence demo."""

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Iterable
from typing import Any

import torch

from sage.common.core import FlatMapFunction, MapFunction
from sage.common.utils.logging.custom_logger import CustomLogger

try:
    from transformers import pipeline as hf_pipeline
except ImportError:  # pragma: no cover - optional dependency
    hf_pipeline = None


class TemporalAnomalyDetector(MapFunction):
    """Detects lighting shifts and abrupt scene switches."""

    def __init__(self, brightness_delta_threshold: float = 35.0) -> None:
        super().__init__()
        self.threshold = max(1.0, brightness_delta_threshold)
        self.prev_brightness: float | None = None
        self.prev_scene: str | None = None

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        brightness = data.get("brightness")
        primary_scene = data.get("primary_scene")

        anomalies: list[dict[str, Any]] = []
        if brightness is not None and self.prev_brightness is not None:
            delta = abs(brightness - self.prev_brightness)
            if delta >= self.threshold:
                anomalies.append(
                    {
                        "type": "lighting_shift",
                        "delta": float(delta),
                    }
                )
        self.prev_brightness = brightness

        if primary_scene and self.prev_scene and primary_scene != self.prev_scene:
            anomalies.append(
                {
                    "type": "scene_transition",
                    "from": self.prev_scene,
                    "to": primary_scene,
                }
            )
        if primary_scene:
            self.prev_scene = primary_scene

        data["anomalies"] = anomalies
        return data


class FrameEventEmitter(FlatMapFunction):
    """Emits structured events for downstream keyed aggregation."""

    def __init__(self, min_confidence: float = 0.25) -> None:
        super().__init__()
        self.min_confidence = min_confidence

    def execute(self, data: dict[str, Any]) -> Iterable[dict[str, Any]]:
        frame_id = data.get("frame_id")
        timestamp = data.get("timestamp")
        events: list[dict[str, Any]] = []

        for concept in data.get("scene_concepts", []):
            if concept["score"] < self.min_confidence:
                continue
            events.append(
                {
                    "event_type": "scene_concept",
                    "label": concept["label"],
                    "score": concept["score"],
                    "frame_id": frame_id,
                    "timestamp": timestamp,
                }
            )

        for prediction in data.get("object_predictions", []):
            if prediction["score"] < self.min_confidence:
                continue
            events.append(
                {
                    "event_type": "object",
                    "label": prediction["label"],
                    "score": prediction["score"],
                    "frame_id": frame_id,
                    "timestamp": timestamp,
                }
            )

        for anomaly in data.get("anomalies", []):
            events.append(
                {
                    "event_type": anomaly.get("type", "anomaly"),
                    "frame_id": frame_id,
                    "timestamp": timestamp,
                    **{k: v for k, v in anomaly.items() if k != "type"},
                }
            )

        return events


class SlidingWindowSummaryEmitter(FlatMapFunction):
    """Produces natural-language summaries for sliding windows of frames."""

    def __init__(
        self,
        window_seconds: float,
        stride_seconds: float,
        max_frames: int,
        summarizer_model: str | None,
        max_summary_tokens: int,
    ) -> None:
        super().__init__()
        self.window_seconds = max(1.0, float(window_seconds))
        self.stride_seconds = max(0.5, float(stride_seconds))
        self.max_frames = max(10, int(max_frames))
        self.max_summary_tokens = max(32, int(max_summary_tokens))
        self.window: deque[dict[str, Any]] = deque()
        self.last_emit_timestamp: float | None = None
        self.summary_index = 0

        self.summarizer = None
        if summarizer_model:
            if hf_pipeline is None:
                logger = CustomLogger(
                    outputs=[("console", "INFO")], name="SlidingWindowSummaryEmitter"
                )
                logger.warning(
                    "transformers is not installed; summariser '%s' cannot be loaded. Falling back to template summaries.",
                    summarizer_model,
                )
            else:
                try:
                    device = 0 if torch.cuda.is_available() else -1
                    self.summarizer = hf_pipeline(
                        "summarization",
                        model=summarizer_model,
                        device=device,
                    )
                except Exception as exc:  # pragma: no cover - optional model
                    logger = CustomLogger(
                        outputs=[("console", "INFO")],
                        name="SlidingWindowSummaryEmitter",
                    )
                    logger.warning(
                        "Failed to load summariser '%s': %s. Falling back to template summaries.",
                        summarizer_model,
                        exc,
                    )
                    self.summarizer = None

    def execute(self, data: dict[str, Any]) -> Iterable[dict[str, Any]]:
        record = {
            "frame_id": data.get("frame_id"),
            "timestamp": data.get("timestamp"),
            "primary_scene": data.get("primary_scene"),
            "scene_concepts": data.get("scene_concepts", []),
            "object_predictions": data.get("object_predictions", []),
            "anomalies": data.get("anomalies", []),
        }
        self.window.append(record)

        while self.window and (
            record["timestamp"] - self.window[0]["timestamp"] > self.window_seconds
            or len(self.window) > self.max_frames
        ):
            self.window.popleft()

        should_emit = (
            self.last_emit_timestamp is None
            or (record["timestamp"] - self.last_emit_timestamp) >= self.stride_seconds
        )

        if not should_emit or not self.window:
            return []

        self.last_emit_timestamp = record["timestamp"]
        self.summary_index += 1
        return [self._build_summary()]

    def _build_summary(self) -> dict[str, Any]:
        start_ts = self.window[0]["timestamp"]
        end_ts = self.window[-1]["timestamp"]

        all_concepts = Counter()
        all_objects = Counter()
        anomalies = Counter()
        captions: list[str] = []

        for entry in self.window:
            for concept in entry.get("scene_concepts", []):
                all_concepts[concept["label"]] += concept["score"]
            for obj in entry.get("object_predictions", []):
                all_objects[obj["label"]] += obj["score"]
            for anomaly in entry.get("anomalies", []):
                anomalies[anomaly.get("type", "anomaly")] += 1
            if entry.get("primary_scene"):
                captions.append(entry["primary_scene"])

        def _top(counter: Counter, limit: int = 5) -> list[str]:
            return [label for label, _ in counter.most_common(limit)]

        composed_text = " " + " ".join(captions)
        if self.summarizer and composed_text.strip():
            try:
                raw_summary = self.summarizer(
                    composed_text,
                    max_length=self.max_summary_tokens,
                    min_length=max(20, self.max_summary_tokens // 3),
                    do_sample=False,
                )[0]["summary_text"].strip()
            except Exception:  # pragma: no cover - fallback path
                raw_summary = self._fallback_summary(_top(all_concepts, 3), _top(all_objects, 5))
        else:
            raw_summary = self._fallback_summary(_top(all_concepts, 3), _top(all_objects, 5))

        return {
            "summary_id": self.summary_index,
            "start_timestamp": float(start_ts),
            "end_timestamp": float(end_ts),
            "duration_seconds": float(end_ts - start_ts),
            "top_scene_concepts": _top(all_concepts, 5),
            "top_objects": _top(all_objects, 5),
            "anomaly_counts": dict(anomalies),
            "generated_summary": raw_summary,
        }

    @staticmethod
    def _fallback_summary(concepts: list[str], objects: list[str]) -> str:
        concept_text = ", ".join(concepts) if concepts else "diverse scenes"
        object_text = ", ".join(objects) if objects else "generic objects"
        return f"Window highlights {concept_text}. Frequent objects include {object_text}."
