"""Core intent data structures (L3: sage-libs)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sage.libs.agentic.agents.action.tool_selection import ToolPrediction


class UserIntent(Enum):
    """Supported user intents."""

    KNOWLEDGE_QUERY = "knowledge_query"
    SAGE_CODING = "sage_coding"
    SYSTEM_OPERATION = "system_operation"
    GENERAL_CHAT = "general_chat"


class KnowledgeDomain(Enum):
    """Knowledge domains for retrieval-heavy intents."""

    SAGE_DOCS = "sage_docs"
    EXAMPLES = "examples"
    RESEARCH_GUIDANCE = "research_guidance"
    USER_UPLOADS = "user_uploads"


@dataclass
class IntentResult:
    """Intent classification result."""

    intent: UserIntent
    confidence: float
    knowledge_domains: list[KnowledgeDomain] | None = None
    matched_keywords: list[str] = field(default_factory=list)
    raw_prediction: ToolPrediction | None = None
    trace: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")

    def should_search_knowledge(self) -> bool:
        return self.intent == UserIntent.KNOWLEDGE_QUERY

    def get_search_sources(self) -> list[str]:
        if not self.knowledge_domains:
            return [KnowledgeDomain.SAGE_DOCS.value, KnowledgeDomain.EXAMPLES.value]
        return [d.value for d in self.knowledge_domains]

    @property
    def suggested_sources(self) -> list[str]:
        return self.get_search_sources()

    def is_high_confidence(self, threshold: float = 0.7) -> bool:
        return self.confidence >= threshold


INTENT_DISPLAY_NAMES: dict[UserIntent, str] = {
    UserIntent.KNOWLEDGE_QUERY: "知识问答",
    UserIntent.SAGE_CODING: "编程助手",
    UserIntent.SYSTEM_OPERATION: "系统操作",
    UserIntent.GENERAL_CHAT: "普通对话",
}

DOMAIN_DISPLAY_NAMES: dict[KnowledgeDomain, str] = {
    KnowledgeDomain.SAGE_DOCS: "SAGE 文档",
    KnowledgeDomain.EXAMPLES: "代码示例",
    KnowledgeDomain.RESEARCH_GUIDANCE: "研究指导",
    KnowledgeDomain.USER_UPLOADS: "用户资料",
}


def get_intent_display_name(intent: UserIntent) -> str:
    return INTENT_DISPLAY_NAMES.get(intent, intent.value)


def get_domain_display_name(domain: KnowledgeDomain) -> str:
    return DOMAIN_DISPLAY_NAMES.get(domain, domain.value)
