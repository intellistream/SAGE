"""Factory helpers to build intent recognizers."""

from __future__ import annotations

from typing import Sequence

from sage.libs.agentic.intent.base import ChainedIntentRecognizer, IntentRecognizer
from sage.libs.agentic.intent.keyword_recognizer import KeywordIntentRecognizer
from sage.libs.agentic.intent.llm_recognizer import LLMIntentRecognizer

RECOGNIZER_BUILDERS = {
    "llm": LLMIntentRecognizer,
    "keyword": KeywordIntentRecognizer,
}


def build_recognizer_chain(
    primary_mode: str = "llm",
    fallback_modes: Sequence[str] | None = None,
    min_confidence: float = 0.0,
) -> ChainedIntentRecognizer:
    modes = [primary_mode]
    if fallback_modes:
        modes.extend(fallback_modes)

    recognizers: list[IntentRecognizer] = []
    for mode in modes:
        builder = RECOGNIZER_BUILDERS.get(mode)
        if builder is None:
            continue
        try:
            recognizers.append(builder())
        except Exception:
            continue

    if not recognizers:
        recognizers.append(KeywordIntentRecognizer())

    return ChainedIntentRecognizer(recognizers=recognizers, min_confidence=min_confidence)
