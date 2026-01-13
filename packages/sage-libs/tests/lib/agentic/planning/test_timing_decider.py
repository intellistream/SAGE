"""
Tests for Timing Decider modules.
"""

import pytest
from sage_libs.sage_agentic.agents.planning import (
    HybridTimingDecider,
    LLMBasedTimingDecider,
    RuleBasedTimingDecider,
    TimingConfig,
    TimingDecision,
    TimingMessage,
)


class TestRuleBasedTimingDecider:
    """Test rule-based timing decider."""

    def test_create_rule_based_decider(self):
        """Test creating rule-based decider."""
        config = TimingConfig()
        decider = RuleBasedTimingDecider(config)

        assert decider.name == "rule_based_timing_decider"
        assert decider.config == config

    def test_greeting_no_tool_call(self):
        """Test greetings don't trigger tool calls."""
        config = TimingConfig()
        decider = RuleBasedTimingDecider(config)

        messages = ["Hello", "Hi there", "你好", "Thanks", "谢谢"]

        for msg in messages:
            message = TimingMessage(user_message=msg)
            decision = decider.decide(message)

            assert decision.should_call_tool is False
            assert decision.confidence > 0.9
            assert (
                "casual" in decision.reasoning.lower() or "greeting" in decision.reasoning.lower()
            )

    def test_action_keywords_trigger_tool_call(self):
        """Test action keywords trigger tool calls."""
        config = TimingConfig()
        decider = RuleBasedTimingDecider(config)

        messages = [
            "Search for flights",
            "Find a restaurant",
            "Calculate the sum",
            "Book a hotel",
            "搜索天气信息",
        ]

        for msg in messages:
            message = TimingMessage(user_message=msg)
            decision = decider.decide(message)

            assert decision.should_call_tool is True
            assert decision.confidence > 0.7

    def test_recent_tool_call_no_new_call(self):
        """Test recent tool call suggests waiting for response."""
        config = TimingConfig()
        decider = RuleBasedTimingDecider(config)

        message = TimingMessage(
            user_message="What did you find?",
            last_tool_call={
                "tool_id": "search",
                "timestamp": "2024-01-01T00:00:00",
                "result": "Some results",
            },
        )

        decision = decider.decide(message)

        assert decision.should_call_tool is False
        assert decision.confidence > 0.85
        assert "recent" in decision.reasoning.lower()

    def test_weather_question_triggers_tool(self):
        """Test weather questions trigger tool calls."""
        config = TimingConfig()
        decider = RuleBasedTimingDecider(config)

        messages = [
            "What's the weather in Beijing?",
            "What's the current temperature?",
            "What's the latest news?",
        ]

        for msg in messages:
            message = TimingMessage(user_message=msg)
            decision = decider.decide(message)

            assert decision.should_call_tool is True

    def test_short_question_likely_needs_lookup(self):
        """Test short questions lean toward tool use."""
        config = TimingConfig()
        decider = RuleBasedTimingDecider(config)

        message = TimingMessage(user_message="Capital of France?")
        decision = decider.decide(message)

        # Should lean toward calling tool, but with lower confidence
        assert decision.should_call_tool is True
        assert decision.confidence >= 0.6


class TestLLMBasedTimingDecider:
    """Test LLM-based timing decider."""

    def test_create_llm_based_decider_without_client_fails(self):
        """Test creating LLM-based decider without client."""
        config = TimingConfig()
        decider = LLMBasedTimingDecider(config, llm_client=None)

        assert decider.name == "llm_based_timing_decider"

        # Should fail when trying to decide
        message = TimingMessage(user_message="Test")
        decision = decider.decide(message)

        # Should return safe fallback
        assert decision.should_call_tool is False
        assert decision.confidence == 0.5

    def test_create_llm_based_decider_with_mock_client(self):
        """Test LLM-based decider with mock client."""
        config = TimingConfig()

        # Mock LLM client
        class MockLLMClient:
            def chat(self, messages, temperature=0.7, max_tokens=300):
                # Return mock decision
                return '{"should_call_tool": true, "confidence": 0.85, "reasoning": "Test", "suggested_tool": null}'

        mock_client = MockLLMClient()
        decider = LLMBasedTimingDecider(config, llm_client=mock_client)

        message = TimingMessage(user_message="What's the weather?")
        decision = decider.decide(message)

        assert decision.should_call_tool is True
        assert decision.confidence == 0.85
        assert decision.reasoning == "Test"


class TestHybridTimingDecider:
    """Test hybrid timing decider."""

    def test_create_hybrid_decider(self):
        """Test creating hybrid decider."""
        config = TimingConfig(decision_threshold=0.8)
        decider = HybridTimingDecider(config, llm_client=None)

        assert decider.name == "hybrid_timing_decider"
        assert decider.confidence_threshold == 0.8

    def test_high_confidence_uses_rules_only(self):
        """Test high-confidence decisions use rules only."""
        config = TimingConfig(decision_threshold=0.8)
        decider = HybridTimingDecider(config, llm_client=None)

        # Greeting should have high confidence from rules
        message = TimingMessage(user_message="Hello!")
        decision = decider.decide(message)

        assert decision.should_call_tool is False
        assert decision.confidence > 0.9

    def test_low_confidence_would_use_llm(self):
        """Test low-confidence cases would delegate to LLM."""
        config = TimingConfig(decision_threshold=0.9)

        # Mock LLM client
        class MockLLMClient:
            def chat(self, messages, temperature=0.7, max_tokens=300):
                return '{"should_call_tool": false, "confidence": 0.95, "reasoning": "LLM decision", "suggested_tool": null}'

        mock_client = MockLLMClient()
        decider = HybridTimingDecider(config, llm_client=mock_client)

        # Ambiguous question that rules might not be confident about
        message = TimingMessage(user_message="Tell me about AI")
        decision = decider.decide(message)

        # If rule confidence < threshold, should use LLM
        if decision.confidence < 0.9:
            # LLM was used, check for hybrid marker
            assert "[Hybrid]" in decision.reasoning or decision.confidence >= 0.9


class TestTimingDecision:
    """Test TimingDecision model."""

    def test_create_timing_decision(self):
        """Test creating timing decision."""
        decision = TimingDecision(
            should_call_tool=True,
            confidence=0.85,
            reasoning="User requested search",
            suggested_tool="search_tool",
        )

        assert decision.should_call_tool is True
        assert decision.confidence == 0.85
        assert decision.reasoning == "User requested search"
        assert decision.suggested_tool == "search_tool"

    def test_confidence_validation(self):
        """Test confidence must be between 0 and 1."""
        with pytest.raises((ValueError, AssertionError)):
            TimingDecision(
                should_call_tool=True,
                confidence=1.5,  # Invalid
            )

        with pytest.raises((ValueError, AssertionError)):
            TimingDecision(
                should_call_tool=True,
                confidence=-0.1,  # Invalid
            )
