"""Workflow router for Studio/Gateway multi-workflow orchestration.

This keeps routing logic in L3 (sage-libs) so L6 callers only forward payloads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sage.libs.agentic.intent import IntentClassifier, IntentResult, UserIntent


class WorkflowRoute(str, Enum):
    """Supported workflow routes."""

    GENERAL = "general"
    SIMPLE_RAG = "simple_rag"
    AGENTIC = "agentic"
    CODE = "code"


@dataclass
class WorkflowRequest:
    """Routing request payload shared between Studio and Gateway."""

    query: str
    session_id: str | None = None
    history: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    should_index: bool = False
    evidence: list[dict[str, Any]] = field(default_factory=list)
    context: list[str] = field(default_factory=list)


@dataclass
class WorkflowDecision:
    """Routing decision returned to L6 callers."""

    route: WorkflowRoute
    intent: UserIntent
    confidence: float
    matched_keywords: list[str]
    should_index: bool
    metadata: dict[str, Any]


class WorkflowRouter:
    """Lightweight router that maps user intent to workflow route."""

    def __init__(self, intent_classifier: IntentClassifier | None = None):
        self.intent_classifier = intent_classifier or IntentClassifier(mode="llm")

    async def decide(self, request: WorkflowRequest) -> WorkflowDecision:
        intent_result: IntentResult
        try:
            intent_result = await self.intent_classifier.classify(request.query, request.history)
        except Exception:
            intent_result = IntentResult(
                intent=UserIntent.GENERAL_CHAT, confidence=0.5, matched_keywords=[]
            )

        route = self._map_intent_to_route(intent_result.intent)

        return WorkflowDecision(
            route=route,
            intent=intent_result.intent,
            confidence=intent_result.confidence,
            matched_keywords=intent_result.matched_keywords,
            should_index=request.should_index,
            metadata=request.metadata,
        )

    def _map_intent_to_route(self, intent: UserIntent) -> WorkflowRoute:
        if intent == UserIntent.KNOWLEDGE_QUERY:
            return WorkflowRoute.SIMPLE_RAG
        if intent == UserIntent.SAGE_CODING:
            return WorkflowRoute.CODE
        if intent == UserIntent.SYSTEM_OPERATION:
            return WorkflowRoute.AGENTIC
        return WorkflowRoute.GENERAL


__all__ = [
    "WorkflowRoute",
    "WorkflowRequest",
    "WorkflowDecision",
    "WorkflowRouter",
]
