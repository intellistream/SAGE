"""Keyword-based intent recognizer."""

from __future__ import annotations

import logging
from typing import Iterable

from sage.libs.agentic.intent import catalog
from sage.libs.agentic.intent.base import IntentRecognitionContext, IntentRecognizer
from sage.libs.agentic.intent.types import IntentResult, KnowledgeDomain, UserIntent

logger = logging.getLogger(__name__)


class KeywordIntentRecognizer(IntentRecognizer):
    def __init__(self) -> None:
        self._selector = None
        self._initialize_selector()

    @staticmethod
    def _build_result(intent: UserIntent, confidence: float, matched_keywords: Iterable[str] = ()):  # type: ignore[type-arg]
        """Construct an IntentResult with knowledge domain enrichment when applicable."""
        knowledge_domains = None
        if intent == UserIntent.KNOWLEDGE_QUERY:
            tool = catalog.get_intent_tool(intent)
            if tool and tool.knowledge_domains:
                knowledge_domains = [KnowledgeDomain(d) for d in tool.knowledge_domains]

        return IntentResult(
            intent=intent,
            confidence=confidence,
            knowledge_domains=knowledge_domains,
            matched_keywords=list(matched_keywords),
        )

    def _initialize_selector(self) -> None:
        try:
            from sage.libs.agentic.agents.action.tool_selection import (
                KeywordSelector,
                SelectorResources,
            )
            from sage.libs.agentic.agents.action.tool_selection.schemas import (
                KeywordSelectorConfig,
            )

            tools_loader = catalog.IntentToolsLoader(catalog.INTENT_TOOLS)
            resources = SelectorResources(tools_loader=tools_loader, embedding_client=None)
            config = KeywordSelectorConfig(
                name="intent_keyword",
                top_k=1,
                min_score=0.0,
                method="tfidf",
                lowercase=True,
                remove_stopwords=False,
                ngram_range=(1, 2),
            )
            self._selector = KeywordSelector.from_config(config, resources)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Keyword selector unavailable, falling back to simple match: %s", exc)
            self._selector = None

    async def classify(self, ctx: IntentRecognitionContext) -> IntentResult:
        # Heuristic boost: installation/docs/tutorial queries should map to knowledge query.
        message_lower = ctx.message.lower()
        knowledge_triggers = (
            "安装",
            "install",
            "文档",
            "docs",
            "documentation",
            "教程",
            "guide",
            "使用",
            "setup",
            "配置",
            "config",
        )
        matched_triggers = [kw for kw in knowledge_triggers if kw in message_lower]
        # If the query mentions SAGE plus any install/docs trigger, force knowledge query.
        mentions_sage = "sage" in message_lower
        if (
            matched_triggers
            or mentions_sage
            and any(kw in ctx.message for kw in knowledge_triggers)
        ):
            trigger_list = matched_triggers or [
                kw for kw in knowledge_triggers if kw in ctx.message
            ]
            return self._build_result(UserIntent.KNOWLEDGE_QUERY, 0.9, trigger_list)

        if self._selector is None:
            return self._classify_simple(ctx.message)

        from sage.libs.agentic.agents.action.tool_selection.schemas import ToolSelectionQuery

        query = ToolSelectionQuery(
            sample_id="intent_classification",
            instruction=ctx.message,
            context={"history": ctx.history} if ctx.history else {},
            candidate_tools=[tool.tool_id for tool in catalog.INTENT_TOOLS],
        )
        predictions = self._selector.select(query, top_k=1)
        if not predictions:
            return IntentResult(intent=UserIntent.GENERAL_CHAT, confidence=0.3)

        top = predictions[0]
        try:
            intent = UserIntent(top.tool_id)
        except ValueError:
            return IntentResult(intent=UserIntent.GENERAL_CHAT, confidence=0.3)

        matched_keywords = top.metadata.get("matched_keywords", []) if top.metadata else []

        return IntentResult(
            intent=intent,
            confidence=top.score,
            knowledge_domains=self._build_result(
                intent, top.score, matched_keywords
            ).knowledge_domains,
            matched_keywords=matched_keywords,
            raw_prediction=top,
        )

    def _classify_simple(self, message: str) -> IntentResult:
        message_lower = message.lower()
        best_intent = UserIntent.GENERAL_CHAT
        best_score = 0.0
        matched_keywords: list[str] = []

        for tool in catalog.INTENT_TOOLS:
            score = 0.0
            matches = []
            for keyword in tool.keywords:
                if keyword.lower() in message_lower:
                    score += 1.0
                    matches.append(keyword)
            normalized_score = min(score * 0.5, 1.0) if tool.keywords else 0.0
            if normalized_score > best_score:
                best_score = normalized_score
                try:
                    best_intent = UserIntent(tool.tool_id)
                except ValueError:
                    continue
                matched_keywords = matches

        return self._build_result(
            intent=best_intent,
            confidence=best_score if best_score > 0 else 0.3,
            matched_keywords=matched_keywords,
        )
