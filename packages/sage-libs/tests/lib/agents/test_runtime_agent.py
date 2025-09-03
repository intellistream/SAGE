# refactor_wxh/MemoRAG/packages/sage-libs/tests/lib/agents/test_runtime_agent.py
from sage.libs.agents.profile.profile import BaseProfile
from sage.libs.agents.planning.llm_planner import LLMPlanner
from sage.libs.agents.runtime.agent import AgentRuntime
from sage.libs.agents.action.mcp_registry import MCPRegistry

import json

# ---- Dummy 生成器：返回固定 JSON 计划 ----
class DummyGeneratorPlan:
    def execute(self, data):
        # 返回一个两步计划：calculator -> reply
        plan = [
            {"type":"tool","name":"calculator","arguments":{"expr":"21*2+5"}},
            {"type":"reply","text":"完成。"}
        ]
        return (data[0], json.dumps(plan, ensure_ascii=False))

# ---- Dummy 工具：calculator ----
class DummyCalc:
    name = "calculator"
    description = "Do math"
    input_schema = {"type":"object","properties":{"expr":{"type":"string"}},"required":["expr"]}
    def call(self, arguments):
        expr = arguments.get("expr","0")
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
            plan = [{"type":"tool","name":"calculator","arguments":{"expr":"41+1"}}]
            return (data[0], json.dumps(plan, ensure_ascii=False))

    tools = MCPRegistry(); tools.register(DummyCalc())
    runtime = AgentRuntime(
        profile=BaseProfile(language="zh"),
        planner=LLMPlanner(generator=GenNoReply()),
        tools=tools,
        summarizer=None
    )
    out = runtime.step("算下 41+1")
    assert "成功" in out and "42" in out
