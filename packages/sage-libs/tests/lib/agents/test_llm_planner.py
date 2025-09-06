# refactor_wxh/MemoRAG/packages/sage-libs/tests/lib/agents/test_llm_planner.py
import json
from sage.libs.agents.planning.llm_planner import LLMPlanner

class DummyGeneratorOK:
    def execute(self, data):
        # data = [user_query, prompt]
        plan = [
            {"type":"tool","name":"calculator","arguments":{"expr":"21*2+5"}},
            {"type":"reply","text":"完成。"}
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
                {"type":"tool","name":"calculator","arguments":{"expr":"1+1"}},
                {"type":"reply","text":"ok"}
            ]
            return (data[0], json.dumps(fixed, ensure_ascii=False))

def test_llm_planner_ok():
    tools = {
        "calculator": {
            "description": "Do math",
            "input_schema": {"type":"object","properties":{"expr":{"type":"string"}},"required":["expr"]},
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
            "input_schema": {"type":"object","properties":{"expr":{"type":"string"}},"required":["expr"]},
        }
    }
    planner = LLMPlanner(generator=DummyGeneratorBadThenFix(), max_steps=3, enable_repair=True)
    plan = planner.plan("SYS", "计算 1+1", tools)
    assert plan and plan[0]["type"] == "tool" and plan[0]["name"] == "calculator"
    assert plan[1]["type"] == "reply"
