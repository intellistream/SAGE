"""Source operators for the video intelligence demo."""

from __future__ import annotations

import os
from typing import Any

import cv2

from sage.common.core.functions.batch_function import BatchFunction


class VideoFrameSource(BatchFunction):
    """Reads frames from a video file as a BatchFunction source."""

    def __init__(
        self,
        video_path: str,
        sample_every_n_frames: int = 3,
        max_frames: int | None = None,
    ) -> None:
        super().__init__()
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        self.video_path = video_path
        self.sample_every = max(1, int(sample_every_n_frames))
        self.max_frames = max_frames if max_frames and max_frames > 0 else None
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open video: {video_path}")

        fps = self.cap.get(cv2.CAP_PROP_FPS) or 0.0
        self.fps = float(fps if fps > 0 else 30.0)
        self.frame_cursor = 0
        self.frames_emitted = 0
        # logger is provided by BaseFunction via ctx

    def execute(self) -> dict[str, Any] | None:
        if not self.cap or not self.cap.isOpened():
            return None

        while True:
            ret, frame = self.cap.read()
            if not ret:
                self.cap.release()
                return None

            current_index = self.frame_cursor
            self.frame_cursor += 1

            if (current_index % self.sample_every) != 0:
                continue  # skip until we hit the sampling cadence

            if self.max_frames and self.frames_emitted >= self.max_frames:
                self.cap.release()
                return None

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            timestamp = current_index / self.fps
            self.frames_emitted += 1

            return {
                "frame_id": int(current_index),
                "timestamp": float(timestamp),
                "fps": self.fps,
                "frame": frame_rgb,
                "video_path": self.video_path,
            }

    def __del__(self) -> None:  # pragma: no cover - defensive cleanup
        if hasattr(self, "cap") and self.cap and self.cap.isOpened():
            self.cap.release()
