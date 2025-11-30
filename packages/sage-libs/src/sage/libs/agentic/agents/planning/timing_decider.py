"""
Timing Decider

Implements tool call timing judgment using rule-based and LLM-based strategies.
Decides whether agent should call a tool or respond directly to user.
"""

import logging
import re
from pathlib import Path
from typing import Any

from jinja2 import Template

from .base import BaseTimingDecider
from .schemas import TimingConfig, TimingDecision, TimingMessage
from .utils.repair import strip_code_fences

logger = logging.getLogger(__name__)


class RuleBasedTimingDecider(BaseTimingDecider):
    """
    Rule-based timing decider using heuristics.

    Fast, deterministic decision-making based on keyword matching
    and conversation context analysis.

    Heuristics:
    - Explicit action verbs → call tool
    - Questions needing external data → call tool
    - Greetings/acknowledgments → respond directly
    - Follow-up on recent tool call → respond directly
    """

    name: str = "rule_based_timing_decider"

    # Action keywords that indicate tool use
    ACTION_KEYWORDS = {
        "search",
        "find",
        "look up",
        "查找",
        "搜索",
        "calculate",
        "compute",
        "计算",
        "book",
        "reserve",
        "预订",
        "send",
        "email",
        "发送",
        "create",
        "generate",
        "创建",
        "生成",
        "translate",
        "翻译",
        "summarize",
        "总结",
        "analyze",
        "分析",
    }

    # Greeting/casual keywords indicating direct response
    CASUAL_KEYWORDS = {
        "hello",
        "hi",
        "hey",
        "你好",
        "您好",
        "thanks",
        "thank you",
        "谢谢",
        "感谢",
        "ok",
        "okay",
        "好的",
        "明白",
        "bye",
        "goodbye",
        "再见",
        "how are you",
        "你好吗",
    }

    # Question patterns needing external data
    EXTERNAL_DATA_PATTERNS = [
        r"what.*weather",
        r"what.*time",
        r"what.*current",
        r"what.*latest",
        r"how many.*\?",
        r"when.*\?",
        r"where.*\?",
    ]

    def __init__(self, config: TimingConfig):
        """
        Initialize rule-based timing decider.

        Args:
            config: Timing configuration
        """
        super().__init__(config)

    def decide(self, message: TimingMessage) -> TimingDecision:
        """
        Make timing decision using rules.

        Args:
            message: TimingMessage with user input and context

        Returns:
            TimingDecision with call/respond decision
        """
        user_msg = message.user_message.lower()

        # Rule 1: Recent tool call suggests user wants results (highest priority)
        if message.last_tool_call:
            # If tool was called very recently, likely waiting for response
            return TimingDecision(
                should_call_tool=False,
                confidence=0.95,
                reasoning="Tool was recently called, user likely wants results",
            )

        # Rule 2: Check for action keywords
        # Use word boundaries for English, simple contains for Chinese/multi-word
        for keyword in self.ACTION_KEYWORDS:
            # Check if keyword contains Chinese characters
            has_chinese = any("\u4e00" <= c <= "\u9fff" for c in keyword)
            # Multi-word phrases or Chinese: use simple substring match
            if " " in keyword or has_chinese:
                if keyword in user_msg:
                    return TimingDecision(
                        should_call_tool=True,
                        confidence=0.90,
                        reasoning="Action keyword detected indicating tool use",
                    )
            else:
                # Single-word English: use word boundaries to avoid "ok" in "book"
                if re.search(rf"\b{re.escape(keyword)}\b", user_msg, re.IGNORECASE):
                    return TimingDecision(
                        should_call_tool=True,
                        confidence=0.90,
                        reasoning="Action keyword detected indicating tool use",
                    )

        # Rule 3: Check for casual/greeting patterns
        # Same logic: word boundaries for English, substring for Chinese
        for keyword in self.CASUAL_KEYWORDS:
            has_chinese = any("\u4e00" <= c <= "\u9fff" for c in keyword)
            if " " in keyword or has_chinese:
                if keyword in user_msg:
                    return TimingDecision(
                        should_call_tool=False,
                        confidence=0.95,
                        reasoning="Casual conversation or greeting detected",
                    )
            else:
                if re.search(rf"\b{re.escape(keyword)}\b", user_msg, re.IGNORECASE):
                    return TimingDecision(
                        should_call_tool=False,
                        confidence=0.95,
                        reasoning="Casual conversation or greeting detected",
                    )

        # Rule 4: Check for patterns needing external data
        for pattern in self.EXTERNAL_DATA_PATTERNS:
            if re.search(pattern, user_msg, re.IGNORECASE):
                return TimingDecision(
                    should_call_tool=True,
                    confidence=0.80,
                    reasoning="Question requires external/real-time data",
                )

        # Rule 5: Check message length and complexity
        # Short questions often need lookup, long ones might be conversational
        if len(user_msg.split()) < 10 and "?" in user_msg:
            return TimingDecision(
                should_call_tool=True,
                confidence=0.60,
                reasoning="Short question, likely needs information lookup",
            )

        # Default: respond directly for general questions
        return TimingDecision(
            should_call_tool=False,
            confidence=0.70,
            reasoning="General question, likely answerable from knowledge",
        )


class LLMBasedTimingDecider(BaseTimingDecider):
    """
    LLM-based timing decider using reasoning.

    Uses language model to analyze conversation context and make
    nuanced decisions about tool calling timing.

    Higher accuracy but slower than rule-based approach.
    """

    name: str = "llm_based_timing_decider"

    def __init__(self, config: TimingConfig, llm_client: Any = None):
        """
        Initialize LLM-based timing decider.

        Args:
            config: Timing configuration
            llm_client: LLM client for decision making
        """
        super().__init__(config)
        self.llm_client = llm_client

        # Load prompt template
        self.template = self._load_template()

    @classmethod
    def from_config(
        cls, config: TimingConfig, llm_client: Any = None, **kwargs: Any
    ) -> "LLMBasedTimingDecider":
        """
        Create LLM-based decider from configuration.

        Args:
            config: Timing configuration
            llm_client: LLM client instance
            **kwargs: Additional resources

        Returns:
            Initialized LLMBasedTimingDecider
        """
        return cls(config=config, llm_client=llm_client)

    def _load_template(self) -> Template:
        """
        Load Jinja2 template for timing judgment prompt.

        Returns:
            Loaded Jinja2 Template
        """
        template_path = Path(__file__).parent / "prompt_templates" / "timing_guard.j2"

        try:
            with open(template_path, encoding="utf-8") as f:
                template_str = f.read()
            return Template(template_str)
        except Exception as e:
            logger.warning(f"Failed to load template from {template_path}: {e}")
            # Fallback to minimal template
            fallback = """Decide if agent should call a tool for: {{ user_message }}
Return JSON: {"should_call_tool": true/false, "confidence": 0-1, "reasoning": "...", "suggested_tool": null}"""
            return Template(fallback)

    def _render_prompt(self, message: TimingMessage) -> str:
        """
        Render prompt from template and message.

        Args:
            message: TimingMessage with conversation context

        Returns:
            Rendered prompt string
        """
        try:
            return self.template.render(
                user_message=message.user_message,
                conversation_history=message.conversation_history,
                last_tool_call=message.last_tool_call,
                context=message.context,
            )
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            return f"Should the agent call a tool to answer: {message.user_message}?"

    def _call_llm(self, prompt: str) -> str:
        """
        Call LLM to make timing decision.

        Args:
            prompt: Rendered prompt string

        Returns:
            LLM response text
        """
        if self.llm_client is None:
            raise RuntimeError("LLM client not configured for LLM-based timing decider")

        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a timing judgment system. Decide when to call tools.",
                },
                {"role": "user", "content": prompt},
            ]

            response = self.llm_client.chat(
                messages=messages,
                temperature=0.3,  # Lower temperature for more consistent decisions
                max_tokens=300,
            )

            # Handle different return formats
            if isinstance(response, tuple):
                return response[0]
            elif isinstance(response, str):
                return response
            else:
                return str(response)

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise RuntimeError(f"Failed to make timing decision via LLM: {e}") from e

    def _parse_llm_output(self, output: str) -> dict[str, Any]:
        """
        Parse LLM output into decision dict.

        Args:
            output: Raw LLM output

        Returns:
            Dictionary with decision fields
        """
        import json

        # Strip code fences
        cleaned = strip_code_fences(output)

        # Try direct JSON parsing
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        # Try extracting JSON object with regex
        try:
            # Match {...} pattern
            match = re.search(r"\{[^{}]*\}", cleaned, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                if isinstance(data, dict):
                    return data
        except (json.JSONDecodeError, AttributeError):
            pass

        logger.warning(f"Failed to parse LLM output: {output[:200]}")

        # Fallback: heuristic parsing
        should_call = "true" in output.lower() or "call" in output.lower()

        return {
            "should_call_tool": should_call,
            "confidence": 0.5,
            "reasoning": "Failed to parse LLM output, using fallback",
            "suggested_tool": None,
        }

    def decide(self, message: TimingMessage) -> TimingDecision:
        """
        Make timing decision using LLM reasoning.

        Args:
            message: TimingMessage with user input and context

        Returns:
            TimingDecision with call/respond decision
        """
        try:
            # Render prompt
            prompt = self._render_prompt(message)

            # Call LLM
            llm_output = self._call_llm(prompt)

            # Parse output
            decision_dict = self._parse_llm_output(llm_output)

            # Create TimingDecision
            return TimingDecision(
                should_call_tool=decision_dict.get("should_call_tool", False),
                confidence=decision_dict.get("confidence", 0.5),
                reasoning=decision_dict.get("reasoning", ""),
                suggested_tool=decision_dict.get("suggested_tool"),
            )

        except Exception as e:
            logger.error(f"LLM-based timing decision failed: {e}")

            # Fallback to safe default (don't call tool)
            return TimingDecision(
                should_call_tool=False,
                confidence=0.5,
                reasoning=f"Decision failed: {str(e)}, defaulting to respond",
            )


class HybridTimingDecider(BaseTimingDecider):
    """
    Hybrid timing decider combining rules and LLM.

    Strategy:
    - Use rules for high-confidence cases (fast path)
    - Use LLM for uncertain cases (slow path, higher accuracy)

    Achieves balance between speed and accuracy.
    """

    name: str = "hybrid_timing_decider"

    def __init__(self, config: TimingConfig, llm_client: Any = None):
        """
        Initialize hybrid timing decider.

        Args:
            config: Timing configuration
            llm_client: LLM client for uncertain cases
        """
        super().__init__(config)

        # Initialize both strategies
        self.rule_based = RuleBasedTimingDecider(config)
        self.llm_based = LLMBasedTimingDecider(config, llm_client) if llm_client else None

        # Confidence threshold for using rules alone
        self.confidence_threshold = config.decision_threshold

    @classmethod
    def from_config(
        cls, config: TimingConfig, llm_client: Any = None, **kwargs: Any
    ) -> "HybridTimingDecider":
        """Create hybrid decider from configuration."""
        return cls(config=config, llm_client=llm_client)

    def decide(self, message: TimingMessage) -> TimingDecision:
        """
        Make timing decision using hybrid approach.

        Args:
            message: TimingMessage with user input and context

        Returns:
            TimingDecision with call/respond decision
        """
        # First, try rule-based decision
        rule_decision = self.rule_based.decide(message)

        # If confidence is high, use rule-based result
        if rule_decision.confidence >= self.confidence_threshold:
            return rule_decision

        # Otherwise, use LLM for more accurate decision
        if self.llm_based is not None:
            logger.info(f"Rule confidence {rule_decision.confidence} below threshold, using LLM")

            try:
                llm_decision = self.llm_based.decide(message)
                # Add metadata about hybrid strategy
                llm_decision.reasoning = f"[Hybrid] Rule uncertain ({rule_decision.confidence:.2f}), LLM says: {llm_decision.reasoning}"
                return llm_decision

            except Exception as e:
                logger.warning(f"LLM decision failed, falling back to rules: {e}")
                return rule_decision

        # No LLM available, return rule-based result
        return rule_decision
