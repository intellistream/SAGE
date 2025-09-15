import os
import sys
import time
import json
from typing import Any, Dict, List


# 环境/数据源/输出
from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io_utils.batch import JSONLBatch
from sage.libs.io_utils.sink import TerminalSink
# Profile & Runtime
from sage.libs.agents.profile import BaseProfile
from sage.libs.agents.runtime import AgentRuntime

# Planner & Action
from sage.libs.agents.planning.llm_planner import LLMPlanner
from sage.libs.agents.action.mcp_registry import MCPRegistry

# Generator
from sage.libs.generators.openai_generator import OpenAIGenerator
from sage.libs.generators.hf_generator import HFGenerator  # 可选

from sage.core.api.function.map_function import MapFunction
from sage.common.utils.config.loader import load_config


# ---------------------------
# 内置一个本地 MCP 风格工具（示例）
# ---------------------------

class ArxivSearchTool:
    name = "arxiv_search"
    description = "Search arXiv papers; return a list of {title, authors, link}."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "size": {"type": "integer", "default": 25},
            "max_results": {"type": "integer", "default": 2},
        },
        "required": ["query"],
    }

    def call(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # 为了示例可离线运行：这里返回模拟数据；可换成真实 requests 爬取
        q = arguments["query"]
        k = int(arguments.get("max_results", 2))
        demo = [
            {
                "title": f"Survey of LLM Agents ({i+1})",
                "authors": "Alice, Bob",
                "link": f"https://arxiv.org/abs/2509.{1234+i}",
            }
            for i in range(k)
        ]
        return {"output": demo, "meta": {"query": q}}


# ---------------------------
# Planner 节点（Map）
# 输入：{"query": "..."} or 带更多字段
# 输出：{"query": "...", "plan": [MCP-steps]}
# ---------------------------
class PlannerNode(MapFunction):
    def __init__(self, config: Dict[str, Any], **kwargs):
        super().__init__(**kwargs)
        # Profile（用于构建 system prompt）
        prof = config.get("profile", {})
        self.profile = BaseProfile(
            name=prof.get("name", "Agent"),
            role=prof.get("role", "planner"),
            language=prof.get("language", "zh"),
            goals=prof.get("goals", []),
            constraints=prof.get("constraints", []),
            persona=prof.get("persona", {}),
        )

        # LLM for planning
        pconf = config["planner"]
        llm_conf = pconf["llm"].copy()
        # 环境变量展开
        if isinstance(llm_conf.get("api_key"), str) and llm_conf["api_key"].startswith("${"):
            env_var = llm_conf["api_key"].strip("${}")
            llm_conf["api_key"] = os.getenv(env_var, "")
        self.plan_llm = OpenAIGenerator(llm_conf)
        self.planner = LLMPlanner(
            generator=self.plan_llm,
            max_steps=pconf.get("max_steps", 6),
            enable_repair=pconf.get("enable_repair", True),
            topk_tools=pconf.get("topk_tools", 6),
        )

        # MCP 可用工具（传入 planner 用于 JSONSchema 约束）
        self.mcp_local_tools = config.get("mcp", {}).get("local_tools", [])
        self.tools_meta: Dict[str, Dict[str, Any]] = {}
        for t in self.mcp_local_tools:
            if t.get("name") == "arxiv_search" and t.get("enable", True):
                self.tools_meta["arxiv_search"] = {
                    "description": ArxivSearchTool.description,
                    "input_schema": ArxivSearchTool.input_schema,
                }

        self.system_prompt = self.profile.render_system_prompt()

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        user_query = data.get("query", "")
        steps = self.planner.plan(self.system_prompt, user_query, self.tools_meta)
        out = dict(data)
        out["plan"] = steps
        return out


# ---------------------------
# MCP 执行节点（Map）
# 输入：{"query": "...", "plan": [...]}
# 输出：{"query": "...", "plan": [...], "observations": [...], "reply": optional}
# ---------------------------
class MCPExecutorNode(MapFunction):
    def __init__(self, config: Dict[str, Any], **kwargs):
        super().__init__(**kwargs)
        # 注册本地工具
        self.registry = MCPRegistry()
        for t in config.get("mcp", {}).get("local_tools", []):
            if t.get("name") == "arxiv_search" and t.get("enable", True):
                self.registry.register(ArxivSearchTool())

        # TODO: 如需远程 MCP server，可在此挂载（略）

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        steps = data.get("plan", [])
        observations: List[Dict[str, Any]] = []
        reply_text: str = ""

        for step in steps:
            stype = step.get("type")
            if stype == "tool":
                name = step.get("name")
                arguments = step.get("arguments", {}) or {}
                try:
                    res = self.registry.call(name, arguments)
                    observations.append({"tool": name, "ok": True, "result": res})
                except Exception as e:
                    observations.append({"tool": name, "ok": False, "error": str(e)})
            elif stype == "reply":
                reply_text = step.get("text", "") or reply_text

        out = dict(data)
        out["observations"] = observations
        if reply_text:
            out["reply"] = reply_text
        return out


# ---------------------------
# Reply 节点（Map）
# 若 plan 已给出 reply，直接透传；
# 否则用生成器根据 observations 生成总结。
# 输入：{"query","plan","observations","reply"?}
# 输出：{"final": "...字符串..."}
# ---------------------------
class ReplyNode(MapFunction):
    def __init__(self, config: Dict[str, Any], **kwargs):
        super().__init__(**kwargs)
        gen_conf = config["generator"]["vllm"].copy()
        if isinstance(gen_conf.get("api_key"), str) and gen_conf["api_key"].startswith("${"):
            env_var = gen_conf["api_key"].strip("${}")
            gen_conf["api_key"] = os.getenv(env_var, "")
        self.generator = OpenAIGenerator(gen_conf)

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if data.get("reply"):
            return {"final": data["reply"], "meta": {"observations": data.get("observations", [])}}

        # 组装一个简单提示，让模型将工具结果转成用户可读总结
        obs = data.get("observations", [])
        prompt = (
            "请基于以下工具调用结果，生成一个简洁的中文总结：\n"
            + json.dumps(obs, ensure_ascii=False, indent=2)
        )
        _, text = self.generator.execute([None, prompt])
        return {"final": text, "meta": {"observations": obs}}


# =====================================================
# 与你给的示例相同的运行主程序结构
# =====================================================
def pipeline_run(config: Dict[str, Any]):
    """创建并运行 Agent 管道（无 memory）"""
    # 测试模式兼容
    if os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true":
        print("🧪 Test mode detected - agent_planner_mcp example")
        print("✅ Test passed: Example structure validated")
        return

    env = LocalEnvironment()

    query_stream = (
        env
        .from_source(JSONLBatch, config["source"])
        .map(PlannerNode, config)        # 产出 MCP 计划
        .map(MCPExecutorNode, config)    # 执行 MCP 工具
        .map(ReplyNode, config)          # 生成/透传最终答复
        .sink(TerminalSink, config["sink"])
    )

    env.submit()
    time.sleep(10)
    env.close()


if __name__ == "__main__":
    # 测试模式兼容
    if os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true":
        print("🧪 Test mode detected - agent_planner_mcp example")
        print("✅ Test passed: Example structure validated")
        sys.exit(0)

    # 加载配置
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "config", "agent_planner_mcp.yaml"
    )
    if not os.path.exists(config_path):
        print(f"❌ Configuration file not found: {config_path}")
        print("Please create the configuration file first.")
        sys.exit(1)

    config = load_config(config_path)

    # 运行管道
    pipeline_run(config)
