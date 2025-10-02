"""Shared utilities for pipeline-as-service examples.

This module provides lightweight queue-based primitives that allow the
registered pipeline service to exchange messages with driver pipelines.
"""

from __future__ import annotations

import queue
from dataclasses import dataclass
from typing import Any, Dict, Optional

from sage.kernel.runtime.communication.router.packet import StopSignal


@dataclass
class PipelineRequest:
    """A request enqueued by a driver pipeline."""

    payload: Dict[str, Any]
    response_queue: "queue.Queue[Dict[str, Any]]"


@dataclass
class PipelinePayload:
    """Message wrapper used inside the service-backed pipeline."""

    order: Dict[str, Any]
    response_queue: "queue.Queue[Dict[str, Any]]"
    features: Optional[Dict[str, Any]] = None
    enriched: Optional[Dict[str, Any]] = None
    scoring: Optional[Dict[str, Any]] = None


class PipelineBridge:
    """Bidirectional bridge between driver pipelines and the service pipeline."""

    def __init__(self) -> None:
        self._requests: "queue.Queue[PipelineRequest | StopSignal]" = queue.Queue()
        self._closed: bool = False

    def submit(self, payload: Dict[str, Any]) -> "queue.Queue[Dict[str, Any]]":
        if self._closed:
            raise RuntimeError("Pipeline bridge is closed")

        response_queue: "queue.Queue[Dict[str, Any]]" = queue.Queue(maxsize=1)
        request = PipelineRequest(payload=payload, response_queue=response_queue)
        self._requests.put(request)
        return response_queue

    def next(self, timeout: float = 0.1):
        if self._closed and self._requests.empty():
            return StopSignal("pipeline-service-shutdown")

        try:
            return self._requests.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._requests.put(StopSignal("pipeline-service-shutdown"))


__all__ = ["PipelineRequest", "PipelinePayload", "PipelineBridge"]
