# refactor_wxh/MemoRAG/packages/sage-libs/tests/lib/agents/test_runtime_agent.py
import json

from sage.libs.agents.action.mcp_registry import MCPRegistry
from sage.libs.agents.planning.llm_planner import LLMPlanner
from sage.libs.agents.profile.profile import BaseProfile
from sage.libs.agents.runtime.agent import AgentRuntime


# ---- Dummy 生成器：返回固定 JSON 计划 ----
class DummyGeneratorPlan:
    def execute(self, data):
        # 返回一个两步计划：calculator -> reply
        plan = [
            {"type": "tool", "name": "calculator", "arguments": {"expr": "21*2+5"}},
            {"type": "reply", "text": "完成。"},
        ]
        return (data[0], json.dumps(plan, ensure_ascii=False))


# ---- New generator that expects message format ----
class DummyGeneratorWithMessages:
    def execute(self, data):
        # Accept both old format [user_query, prompt] and new format [user_query, messages]
        user_query = data[0]
        second_param = data[1]

        if isinstance(second_param, list):
            # New message format
            messages = second_param
            assert len(messages) >= 1
            if len(messages) == 2:
                assert messages[0]["role"] == "system"
                assert messages[1]["role"] == "user"

        plan = [
            {"type": "tool", "name": "calculator", "arguments": {"expr": "21*2+5"}},
            {"type": "reply", "text": "完成。"},
        ]
        return (user_query, json.dumps(plan, ensure_ascii=False))


# ---- Dummy 工具：calculator ----
class DummyCalc:
    name = "calculator"
    description = "Do math"
    input_schema = {
        "type": "object",
        "properties": {"expr": {"type": "string"}},
        "required": ["expr"],
    }

    def call(self, arguments):
        expr = arguments.get("expr", "0")
        return {"output": str(eval(expr, {"__builtins__": {}}))}


def test_runtime_basic_flow():
    tools = MCPRegistry()
    tools.register(DummyCalc())

    planner = LLMPlanner(generator=DummyGeneratorPlan())
    profile = BaseProfile(language="zh")

    runtime = AgentRuntime(profile=profile, planner=planner, tools=tools, summarizer=None)
    out = runtime.step("计算 21*2+5")
    # 因为计划里包含 reply，runtime 将直接返回 "完成。"
    assert "完成" in out


def test_runtime_no_reply_uses_template_summary():
    class GenNoReply:
        def execute(self, data):
            # 只返回一个工具步，不含 reply
            plan = [{"type": "tool", "name": "calculator", "arguments": {"expr": "41+1"}}]
            return (data[0], json.dumps(plan, ensure_ascii=False))

    tools = MCPRegistry()
    tools.register(DummyCalc())
    runtime = AgentRuntime(
        profile=BaseProfile(language="zh"),
        planner=LLMPlanner(generator=GenNoReply()),
        tools=tools,
        summarizer=None,
    )
    out = runtime.step("算下 41+1")
    assert "成功" in out and "42" in out


# New tests for the message format changes in commit 12aec700c63407e1f5d79455b2d64a60a6688e96


def test_runtime_with_message_format_summarizer():
    """Test AgentRuntime with summarizer using new message format."""

    class SummarizerWithMessages:
        def execute(self, data):
            # data should be [None, messages] for summarizer
            assert data[0] is None
            messages = data[1]
            assert isinstance(messages, list)
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[1]["role"] == "user"

            return (None, "总结: 计算结果是47")

    class GenNoReply:
        def execute(self, data):
            plan = [{"type": "tool", "name": "calculator", "arguments": {"expr": "45+2"}}]
            return (data[0], json.dumps(plan, ensure_ascii=False))

    tools = MCPRegistry()
    tools.register(DummyCalc())

    runtime = AgentRuntime(
        profile=BaseProfile(language="zh"),
        planner=LLMPlanner(generator=GenNoReply()),
        tools=tools,
        summarizer=SummarizerWithMessages(),
    )

    out = runtime.step("计算 45+2")
    assert "总结: 计算结果是47" in out


def test_runtime_memory_disabled():
    """Test that memory functionality is disabled as per the commit changes."""
    tools = MCPRegistry()
    tools.register(DummyCalc())

    planner = LLMPlanner(generator=DummyGeneratorWithMessages())
    profile = BaseProfile(language="zh")

    # The memory parameter should be commented out/disabled
    runtime = AgentRuntime(profile=profile, planner=planner, tools=tools, summarizer=None)

    # Verify memory is not set (should be None or not exist)
    assert not hasattr(runtime, "memory") or runtime.memory is None


def test_runtime_with_new_planner_message_format():
    """Test that runtime works with planner using new message format."""
    tools = MCPRegistry()
    tools.register(DummyCalc())

    planner = LLMPlanner(generator=DummyGeneratorWithMessages())
    profile = BaseProfile(language="zh")

    runtime = AgentRuntime(profile=profile, planner=planner, tools=tools, summarizer=None)

    out = runtime.step("计算 21*2+5")
    # Should work with the new message format in planner
    assert "完成" in out
