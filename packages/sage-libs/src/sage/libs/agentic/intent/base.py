"""Intent recognition interfaces (L3: sage-libs)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable

from sage.libs.agentic.intent.types import IntentResult

logger = logging.getLogger(__name__)


@dataclass
class IntentRecognitionContext:
    message: str
    history: list[dict[str, str]] | None = None
    extra: dict | None = None


class IntentRecognizer(ABC):
    @abstractmethod
    async def classify(
        self, ctx: IntentRecognitionContext
    ) -> IntentResult:  # pragma: no cover - interface
        ...


@dataclass
class ChainedIntentRecognizer(IntentRecognizer):
    recognizers: list[IntentRecognizer]
    min_confidence: float = 0.0
    trace: list[str] = field(default_factory=list)

    async def classify(self, ctx: IntentRecognitionContext) -> IntentResult:
        last_result: IntentResult | None = None
        for recognizer in self.recognizers:
            name = recognizer.__class__.__name__
            try:
                result = await recognizer.classify(ctx)
                result.trace.append(f"{name}:{result.confidence:.2f}")
                self.trace.append(f"{name}:{result.confidence:.2f}")
                last_result = result
                if result.confidence >= self.min_confidence:
                    return result
            except Exception as exc:  # noqa: BLE001
                logger.warning("Intent recognizer %s failed: %s", name, exc)
                self.trace.append(f"{name}:error")
                continue
        if last_result is not None:
            last_result.trace.extend(self.trace)
            return last_result
        raise RuntimeError("No intent recognizer available")


def ensure_list(value: Iterable[IntentRecognizer] | IntentRecognizer) -> list[IntentRecognizer]:
    if isinstance(value, IntentRecognizer):
        return [value]
    return list(value)
