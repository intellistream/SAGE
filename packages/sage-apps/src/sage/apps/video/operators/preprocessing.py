"""Preprocessing operators for the video intelligence demo."""

from __future__ import annotations

from typing import Any

import numpy as np
from PIL import Image

from sage.common.core.functions.map_function import MapFunction


class FramePreprocessor(MapFunction):
    """Converts numpy frames to PIL, resizes, and extracts basic metrics."""

    def __init__(self, target_size: int = 336) -> None:
        super().__init__()
        self.target_size = target_size

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        frame = data.get("frame")
        if frame is None:
            return data

        pil_image = Image.fromarray(frame)
        data["pil_image"] = pil_image
        data["brightness"] = float(np.mean(frame))

        if self.target_size:
            data["resized_image"] = pil_image.resize((self.target_size, self.target_size))
        else:
            data["resized_image"] = pil_image

        return data
