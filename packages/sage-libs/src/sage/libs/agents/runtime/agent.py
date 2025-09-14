# refactor_wxh/MemoRAG/packages/sage-libs/src/sage/libs/agents/runtime/agent.py
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from ..action.mcp_registry import MCPRegistry
from ..planning.llm_planner import LLMPlanner, PlanStep
from ..profile.profile import BaseProfile
from sage.libs.agents.memory import memory_service_adapter



def _missing_required(
    arguments: Dict[str, Any], input_schema: Dict[str, Any]
) -> List[str]:
    """基于 MCP JSON Schema 做最小必填参数校验。"""
    req = (input_schema or {}).get("required") or []
    return [k for k in req if k not in arguments]


class AgentRuntime:
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
