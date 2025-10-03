"""Formatting utilities for the video intelligence demo."""

from __future__ import annotations

from typing import Any, Dict

from sage.core.api.function.map_function import MapFunction


class FrameLightweightFormatter(MapFunction):
    """Drops heavy artefacts and adds convenience fields."""

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        data.pop("frame", None)
        data.pop("pil_image", None)
        data.pop("resized_image", None)
        data["top_scene_labels"] = [
            entry["label"] for entry in data.get("scene_concepts", [])
        ]
        data["top_object_labels"] = [
            entry["label"] for entry in data.get("object_predictions", [])
        ]
        return data
