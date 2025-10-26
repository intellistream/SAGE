# refactor_wxh/MemoRAG/packages/sage-libs/tests/lib/agents/test_llm_planner.py
import json

from sage.libs.agents.planning.llm_planner import LLMPlanner


class DummyGeneratorOK:
    def execute(self, data):
        # data = [user_query, prompt] or [user_query, messages]
        plan = [
            {"type": "tool", "name": "calculator", "arguments": {"expr": "21*2+5"}},
            {"type": "reply", "text": "完成。"},
        ]
        return (data[0], json.dumps(plan, ensure_ascii=False))


class DummyGeneratorBadThenFix:
    def __init__(self):
        self.n = 0

    def execute(self, data):
        self.n += 1
        if self.n == 1:
            # 非法输出（无JSON）
            return (data[0], "First I will use calculator, then reply.")
        else:
            fixed = [
                {"type": "tool", "name": "calculator", "arguments": {"expr": "1+1"}},
                {"type": "reply", "text": "ok"},
            ]
            return (data[0], json.dumps(fixed, ensure_ascii=False))


def test_llm_planner_ok():
    tools = {
        "calculator": {
            "description": "Do math",
            "input_schema": {
                "type": "object",
                "properties": {"expr": {"type": "string"}},
                "required": ["expr"],
            },
        }
    }
    planner = LLMPlanner(generator=DummyGeneratorOK(), max_steps=3)
    plan = planner.plan("SYS", "计算 21*2+5", tools)
    assert len(plan) == 2
    assert plan[0]["type"] == "tool" and plan[0]["name"] == "calculator"
    assert plan[1]["type"] == "reply"


def test_llm_planner_repair():
    tools = {
        "calculator": {
            "description": "Do math",
            "input_schema": {
                "type": "object",
                "properties": {"expr": {"type": "string"}},
                "required": ["expr"],
            },
        }
    }
    planner = LLMPlanner(generator=DummyGeneratorBadThenFix(), max_steps=3, enable_repair=True)
    plan = planner.plan("SYS", "计算 1+1", tools)
    assert plan and plan[0]["type"] == "tool" and plan[0]["name"] == "calculator"
    assert plan[1]["type"] == "reply"


# New tests for the message format changes in commit 12aec700c63407e1f5d79455b2d64a60a6688e96


class DummyGeneratorWithMessages:
    """Generator that expects new message format."""

    def execute(self, data):
        # data = [user_query, messages] where messages is a list of dicts
        user_query, messages = data

        # Verify message format
        assert isinstance(messages, list)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == user_query

        plan = [
            {"type": "tool", "name": "calculator", "arguments": {"expr": "2+2"}},
            {"type": "reply", "text": "计算完成。"},
        ]
        return (user_query, json.dumps(plan, ensure_ascii=False))


def test_llm_planner_message_format():
    """Test that LLMPlanner uses the new message format."""
    tools = {
        "calculator": {
            "description": "Do math",
            "input_schema": {
                "type": "object",
                "properties": {"expr": {"type": "string"}},
                "required": ["expr"],
            },
        }
    }

    planner = LLMPlanner(generator=DummyGeneratorWithMessages(), max_steps=3)
    plan = planner.plan("System prompt here", "计算 2+2", tools)

    assert len(plan) == 2
    assert plan[0]["type"] == "tool" and plan[0]["name"] == "calculator"
    assert plan[1]["type"] == "reply"


def test_llm_planner_prompt_includes_tool_requirement():
    """Test that the system prompt includes the new tool requirement rule."""

    class MessageCapturingGenerator:
        def __init__(self):
            self.captured_messages = None

        def execute(self, data):
            self.captured_messages = data[1]  # Store the messages
            plan = [
                {"type": "tool", "name": "calculator", "arguments": {"expr": "1+1"}},
                {"type": "reply", "text": "完成"},
            ]
            return (data[0], json.dumps(plan, ensure_ascii=False))

    generator = MessageCapturingGenerator()
    tools = {
        "calculator": {
            "description": "Do math",
            "input_schema": {
                "type": "object",
                "properties": {"expr": {"type": "string"}},
                "required": ["expr"],
            },
        }
    }

    planner = LLMPlanner(generator=generator, max_steps=3)
    planner.plan("Profile prompt", "test query", tools)

    # Check that the system prompt includes the new rule
    system_content = generator.captured_messages[0]["content"]
    assert "Always call at least one tool before replying when tools are provided" in system_content
