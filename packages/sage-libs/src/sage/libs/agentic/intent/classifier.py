"""Default IntentClassifier for L3 reuse."""

from __future__ import annotations

from sage.libs.agentic.intent.base import (
    ChainedIntentRecognizer,
    IntentRecognitionContext,
    IntentRecognizer,
)
from sage.libs.agentic.intent.catalog import (
    INTENT_TOOLS,
    IntentTool,
    IntentToolsLoader,
    get_all_intent_keywords,
    get_intent_tool,
)
from sage.libs.agentic.intent.factory import build_recognizer_chain
from sage.libs.agentic.intent.keyword_recognizer import KeywordIntentRecognizer
from sage.libs.agentic.intent.llm_recognizer import LLMIntentRecognizer
from sage.libs.agentic.intent.types import (
    DOMAIN_DISPLAY_NAMES,
    INTENT_DISPLAY_NAMES,
    IntentResult,
    KnowledgeDomain,
    UserIntent,
    get_domain_display_name,
    get_intent_display_name,
)


class IntentClassifier:
    """Default classifier backed by a recognizer chain."""

    def __init__(
        self,
        mode: str = "keyword",
        embedding_model: str | None = None,
        fallback_modes: list[str] | None = None,
    ) -> None:
        self.mode = mode
        self.embedding_model = embedding_model
        self._recognizer = build_recognizer_chain(
            primary_mode=mode,
            fallback_modes=fallback_modes or ("keyword",),
            min_confidence=0.0,
        )
        self._initialized = True

    async def classify(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        context: str | None = None,
    ) -> IntentResult:
        ctx = IntentRecognitionContext(message=message, history=history, extra={"context": context})
        return await self._recognizer.classify(ctx)

    @property
    def is_initialized(self) -> bool:
        return self._initialized


__all__ = [
    "UserIntent",
    "KnowledgeDomain",
    "IntentResult",
    "IntentTool",
    "INTENT_TOOLS",
    "INTENT_DISPLAY_NAMES",
    "DOMAIN_DISPLAY_NAMES",
    "IntentToolsLoader",
    "IntentRecognizer",
    "ChainedIntentRecognizer",
    "KeywordIntentRecognizer",
    "LLMIntentRecognizer",
    "IntentClassifier",
    "get_intent_display_name",
    "get_domain_display_name",
    "get_intent_tool",
    "get_all_intent_keywords",
]
