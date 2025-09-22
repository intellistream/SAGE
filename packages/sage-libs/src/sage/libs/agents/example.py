# refactor_wxh/MemoRAG/packages/sage-libs/examples/pipeline_demo.py
from __future__ import annotations
import json
import sys
from pathlib import Path

# # 让示例在独立运行时也能找到 src 包
# ROOT = Path(__file__).resolve().parents[2]  # .../packages/sage-libs
# SRC = ROOT / "src"
# sys.path.append(str(SRC))

from sage.libs.agents.profile.profile import BaseProfile
from sage.libs.agents.action.mcp_registry import MCPRegistry
from sage.libs.agents.planning.llm_planner import LLMPlanner
from sage.libs.agents.runtime.agent import AgentRuntime

# ========== 1) 准备一个 MCP 工具（示例：calculator） ==========
class CalculatorTool:
    name = "calculator"
    description = "Do arithmetic on a simple expression, e.g., '21*2+5'. Returns {'output': <str>}."
    input_schema = {
        "type": "object",
        "properties": {
            "expr": {"type": "string", "description": "Arithmetic expression to evaluate"}
        },
        "required": ["expr"],
        "additionalProperties": False
    }
    def call(self, arguments):
        expr = str(arguments.get("expr", "0"))
        # 演示用：生产环境请替换为安全求值
        return {"output": str(eval(expr, {"__builtins__": {}}))}

# （可选）如果你已有 arxiv_search 之类的 MCP 工具，也可以在这里一并注册：
# from sage.libs.tools.arxiv_search_mcp import ArxivSearchMCP
# reg.register(ArxivSearchMCP())

# ========== 2) 准备一个 Generator ==========
#   A) 真实环境 —— 用你的 OpenAIGenerator（建议）：
# from sage.libs.rag.generator import OpenAIGenerator
# gen_conf = {
#     "method": "openai",
#     "model_name": "gpt-4o-mini",
#     "base_url": "http://localhost:8000/v1",
#     "api_key": "your-api-key",
#     "seed": 42,
#     "temperature": 0.7
# }
# generator = OpenAIGenerator(gen_conf)

#   B) 演示/离线环境 —— 用 DummyGenerator 固定返回一个计划（便于无模型也能跑通）
class DummyGeneratorPlan:
    def execute(self, data):
        # data = [user_query, prompt]
        plan = [
            {"type": "tool", "name": "calculator", "arguments": {"expr": "21*2+5"}},
            {"type": "reply", "text": "计算完成，已把结果并入总结。"}
        ]
        return (data[0], json.dumps(plan, ensure_ascii=False))

def main(use_dummy_generator: bool = True):
    # 2) 初始化生成器 & Planner
    if use_dummy_generator:
        generator = DummyGeneratorPlan()
    else:
        raise RuntimeError("Set use_dummy_generator=True or plug in your real OpenAIGenerator.")

    planner = LLMPlanner(generator=generator, max_steps=4, enable_repair=True, topk_tools=6)

    # 3) Profile（人设）
    profile = BaseProfile(
        name="PipelineDemo",
        role="task planner & executor",
        language="zh",
        tone="concise",
        goals=["正确调用工具并汇总结果", "输出结构清晰、简洁的回答"],
        tasks=["解析用户需求→规划→执行工具→汇总回复"]
    )

    # 4) 工具注册（MCP Registry）
    reg = MCPRegistry()
    reg.register(CalculatorTool())
    # reg.register(ArxivSearchMCP())  # 如果你有更多工具，直接注册

    # 5) Runtime（可选 summarizer：可以重用你的 OpenAIGenerator 作为总结器）
    runtime = AgentRuntime(
        profile=profile,
        planner=planner,
        tools=reg,
        summarizer=None,  # 你可以传入 generator 作为总结器：summarizer=generator
        max_steps=6
    )

    # 6) 跑几条请求
    queries = [
        "帮我算一下 21*2+5 ，并总结一下过程",
        # "在 arxiv 找三篇 LLM agents 综述，并算 21*2+5 后告诉我总数"  # 如果有 arxiv_search 工具就可以测这类
    ]
    for q in queries:
        print("\n===================== QUERY =====================")
        print(q)
        print("===================== REPLY =====================")
        out = runtime.step(q)
        print(out)

if __name__ == "__main__":
    main(use_dummy_generator=True)
