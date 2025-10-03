"""Operator collection for the video intelligence demo."""

from .sources import VideoFrameSource
from .preprocessing import FramePreprocessor
from .perception import SceneConceptExtractor, FrameObjectClassifier
from .analytics import TemporalAnomalyDetector, FrameEventEmitter, SlidingWindowSummaryEmitter
from .formatters import FrameLightweightFormatter
from .integrations import SageMiddlewareIntegrator, SummaryMemoryAugmentor
from .sinks import TimelineSink, SummarySink, EventStatsSink

__all__ = [
    "VideoFrameSource",
    "FramePreprocessor",
    "SceneConceptExtractor",
    "FrameObjectClassifier",
    "TemporalAnomalyDetector",
    "FrameEventEmitter",
    "SlidingWindowSummaryEmitter",
    "FrameLightweightFormatter",
    "SageMiddlewareIntegrator",
    "SummaryMemoryAugmentor",
    "TimelineSink",
    "SummarySink",
    "EventStatsSink",
]
