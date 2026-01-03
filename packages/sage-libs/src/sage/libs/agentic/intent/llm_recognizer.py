"""LLM-based intent recognizer."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from sage.common.config.ports import SagePorts
from sage.libs.agentic.intent.base import IntentRecognitionContext, IntentRecognizer
from sage.libs.agentic.intent.types import IntentResult, KnowledgeDomain, UserIntent
from sage.llm import UnifiedInferenceClient

logger = logging.getLogger(__name__)


class LLMIntentRecognizer(IntentRecognizer):
    def __init__(self, control_plane_url: Optional[str] = None) -> None:
        self._client = None
        self._control_plane_url = (
            control_plane_url or f"http://localhost:{SagePorts.GATEWAY_DEFAULT}/v1"
        )
        self._initialize_client()

    def _initialize_client(self) -> None:
        try:
            self._client = UnifiedInferenceClient.create(control_plane_url=self._control_plane_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to initialize LLM client for intent: %s", exc)
            self._client = None

    async def classify(self, ctx: IntentRecognitionContext) -> IntentResult:
        if self._client is None:
            raise RuntimeError("LLM client not available")

        prompt = (
            "You are an intent classifier for the SAGE AI framework.\n"
            "Classify the user's message into one of the following intents:\n\n"
            "1. knowledge_query: Questions requiring knowledge base search (SAGE docs, research papers, examples).\n"
            "2. sage_coding: SAGE framework programming tasks (pipeline generation, debugging, API usage).\n"
            "3. system_operation: System management (start/stop services, check status).\n"
            "4. general_chat: General conversation or unrelated topics.\n\n"
            f"User Message: {ctx.message}\n\nReturn ONLY the intent name (e.g., 'knowledge_query')."
        )

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None, lambda: self._client.chat([{"role": "user", "content": prompt}])
        )

        content = response.strip().lower()
        normalized = content.replace(" ", "_")

        for intent in UserIntent:
            if intent.value in content or intent.value in normalized:
                knowledge_domains = None
                if intent == UserIntent.KNOWLEDGE_QUERY:
                    knowledge_domains = [KnowledgeDomain.SAGE_DOCS, KnowledgeDomain.EXAMPLES]
                return IntentResult(
                    intent=intent,
                    confidence=0.9,
                    knowledge_domains=knowledge_domains,
                    matched_keywords=[],
                )

        logger.warning(
            "LLM output '%s' did not match intents, falling back to low confidence", content
        )
        return IntentResult(intent=UserIntent.GENERAL_CHAT, confidence=0.3)
