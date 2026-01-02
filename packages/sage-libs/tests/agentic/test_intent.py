import pytest

from sage.libs.agentic.intent import (
    IntentClassifier,
    IntentResult,
    KnowledgeDomain,
    UserIntent,
    get_intent_tool,
)


class TestIntentTypes:
    def test_enum_values(self):
        assert UserIntent.KNOWLEDGE_QUERY.value == "knowledge_query"
        assert KnowledgeDomain.SAGE_DOCS.value == "sage_docs"

    def test_intent_tool_lookup(self):
        tool = get_intent_tool(UserIntent.KNOWLEDGE_QUERY)
        assert tool is not None
        assert "SAGE" in tool.keywords
        assert UserIntent.KNOWLEDGE_QUERY.value == tool.tool_id

    def test_intent_result_validation(self):
        with pytest.raises(ValueError):
            IntentResult(intent=UserIntent.GENERAL_CHAT, confidence=1.5)


class TestKeywordIntentClassifier:
    @pytest.mark.asyncio
    async def test_keyword_classification(self):
        classifier = IntentClassifier(mode="keyword")
        result = await classifier.classify("怎么安装 SAGE")
        assert result.intent == UserIntent.KNOWLEDGE_QUERY
        assert result.should_search_knowledge() is True

    @pytest.mark.asyncio
    async def test_keyword_general_chat(self):
        classifier = IntentClassifier(mode="keyword")
        result = await classifier.classify("hello there")
        assert result.intent in {UserIntent.GENERAL_CHAT, UserIntent.KNOWLEDGE_QUERY}
        # ensure confidence is within range
        assert 0 <= result.confidence <= 1
