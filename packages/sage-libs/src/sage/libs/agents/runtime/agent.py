# refactor_wxh/MemoRAG/packages/sage-libs/src/sage/libs/agents/runtime/agent.py
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from ..action.mcp_registry import MCPRegistry
from ..planning.llm_planner import LLMPlanner, PlanStep
from ..profile.profile import BaseProfile
from sage.libs.agents.memory import memory_service_adapter
from sage.core.api.function.map_function import MapFunction


def _missing_required(
    arguments: Dict[str, Any], input_schema: Dict[str, Any]
) -> List[str]:
    """基于 MCP JSON Schema 做最小必填参数校验。"""
    req = (input_schema or {}).get("required") or []
    return [k for k in req if k not in arguments]


class AgentRuntime(MapFunction):
    """
    最小可用 Runtime：
    - 输入：user_query
    - 流程：Planner 产出 JSON 计划 -> 逐步执行 -> 可选用 LLM 汇总 -> 返回
    TODO:
    1.Safety
    """

    def __init__(
        self,
        profile: BaseProfile,
        planner: LLMPlanner,
        tools: MCPRegistry,
        summarizer=None,
        memory: Optional[memory_service_adapter.MemoryServiceAdapter] = None,
        max_steps: int = 6,
    ):
        self.profile = profile
        self.planner = planner
        self.tools = tools
        self.memory = memory
        self.summarizer = summarizer  # 复用你的 generator 也行：execute([None, prompt]) -> (None, text)
        self.max_steps = max_steps

    def step(self, user_query: str) -> str:
        # 1) 生成计划（MCP 风格）
        plan: List[PlanStep] = self.planner.plan(
            profile_system_prompt=self.profile.render_system_prompt(),
            user_query=user_query,
            tools=self.tools.describe(),
        )

        observations: List[Dict[str, Any]] = []
        reply_text: Optional[str] = None

        # 2) 逐步执行
        for i, step in enumerate(plan[: self.max_steps]):
            if step.get("type") == "reply":
                reply_text = step.get("text", "").strip()
                break

            if step.get("type") == "tool":
                name = step.get("name")
                arguments = step.get("arguments", {}) or {}

                tools_meta = self.tools.describe()
                tool_desc = tools_meta.get(name) if isinstance(name, str) else None

                schema = tool_desc.get("input_schema", {}) if tool_desc else {}

                miss = _missing_required(arguments, schema)
                if miss:
                    observations.append(
                        {
                            "step": i,
                            "tool": name,
                            "ok": False,
                            "error": f"Missing required fields: {miss}",
                            "arguments": arguments,
                        }
                    )
                    continue

                t0 = time.time()
                try:
                    out = self.tools.call(name, arguments)  # type: ignore[arg-type]
                    observations.append(
                        {
                            "step": i,
                            "tool": name,
                            "ok": True,
                            "latency_ms": int((time.time() - t0) * 1000),
                            "result": out,
                        }
                    )
                except Exception as e:
                    observations.append(
                        {
                            "step": i,
                            "tool": name,
                            "ok": False,
                            "latency_ms": int((time.time() - t0) * 1000),
                            "error": str(e),
                        }
                    )

        # 3) 汇总输出（优先 Planner 自带的 reply；否则用模板/可选 LLM 总结）
        if reply_text:
            return reply_text

        # 没有 reply 步：用模板或 summarizer 组织答案
        if not observations:
            return "（没有可执行的步骤或工具返回空结果）"

        if self.summarizer:
            # 用你的生成器来生成自然语言总结
            profile_hint = self.profile.render_system_prompt()
            prompt = f"""请将以下工具步骤结果用中文简洁汇总给用户，保留关键信息和结论。

[Profile]
{profile_hint}

[Observations]
{observations}

只输出给用户的总结文本。"""
            _, summary = self.summarizer.execute([None, prompt])
            return summary.strip()

        # 简单模板
        lines = []
        for obs in observations:
            if obs.get("ok"):
                lines.append(
                    f"#{obs['step']+1} 工具 {obs['tool']} 成功：{obs.get('result')}"
                )
            else:
                lines.append(
                    f"#{obs['step']+1} 工具 {obs['tool']} 失败：{obs.get('error')}"
                )
        return "\n".join(lines)

    def execute(self, data: Any) -> str:
        """
        统一入口，支持两种形态：
        1) str：被视为 user_query
        2) dict：
           {
             "user_query" | "query": str,          # 必填
             "max_steps": int,                     # 可选：仅本次调用覆写
             "profile_overrides": { ... }          # 可选：一次性覆写 profile 字段（使用 BaseProfile.merged）
           }
        返回：最终给用户的字符串回复
        """
        # 形态 1：直接字符串
        if isinstance(data, str):
            return self.step(data)

        # 形态 2：字典
        if isinstance(data, dict):
            user_query = data.get("user_query") or data.get("query")
            if not isinstance(user_query, str) or not user_query.strip():
                raise ValueError("AgentRuntime.execute(dict) 需要提供 'user_query' 或 'query'（非空字符串）。")

            # 临时覆写 max_steps
            original_max = self.max_steps
            if "max_steps" in data:
                ms = data["max_steps"]
                if not isinstance(ms, int) or ms <= 0:
                    raise ValueError("'max_steps' 必须是正整数。")
                self.max_steps = ms

            # 临时覆写 profile（一次性，不污染实例）
            original_profile = self.profile
            if "profile_overrides" in data and isinstance(data["profile_overrides"], dict):
                try:
                    self.profile = self.profile.merged(**data["profile_overrides"])
                except Exception as e:
                    # 失败则回退，不中断主流程
                    self.profile = original_profile

            try:
                return self.step(user_query)
            finally:
                # 还原
                self.max_steps = original_max
                self.profile = original_profile

        raise TypeError("AgentRuntime.execute 仅接受 str 或 dict 两种输入。")
