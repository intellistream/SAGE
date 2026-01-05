"""
Agent Runtime (Middleware Layer)

This component acts as a Dynamic Pipeline Orchestrator.
It takes a user query, generates a dynamic execution plan (DAG), and executes it using available tools.
"""

from __future__ import annotations

import logging
import time
from typing import Any

# Import from L3 (Libs) - Allowed dependency direction (L4 -> L3)
from sage.libs.agentic.agents.action.mcp_registry import MCPRegistry
from sage.libs.agentic.agents.planning import PlanStep, SimpleLLMPlanner
from sage.libs.agentic.agents.profile.profile import BaseProfile

logger = logging.getLogger(__name__)


def _missing_required(arguments: dict[str, Any], input_schema: dict[str, Any]) -> list[str]:
    """基于 MCP JSON Schema 做最小必填参数校验。"""
    req = (input_schema or {}).get("required") or []
    return [k for k in req if k not in arguments]


class AgentRuntime:
    """
    Production-Ready Runtime (Middleware Layer):
    - Input: user_query
    - Process: Planner generates JSON plan -> Step-by-step execution -> Optional LLM summary -> Return
    - Features: Safety checks, Error handling, Structured logging/output
    """

    def __init__(
        self,
        profile: BaseProfile,
        planner: SimpleLLMPlanner,
        tools: MCPRegistry,
        summarizer=None,
        max_steps: int = 6,
    ):
        self.profile = profile
        self.planner = planner
        self.tools = tools
        self.summarizer = summarizer
        self.max_steps = max_steps

    def step_stream(self, user_query: str):
        """
        Execute a single turn of conversation with streaming feedback.

        Yields:
            Dict containing event type and data
        """
        logger.info(f"AgentRuntime (Middleware) step_stream started for query: {user_query}")

        observations: list[dict[str, Any]] = []
        plan: list[PlanStep] = []

        # 1) 生成计划（流式）
        try:
            # 检查 planner 是否支持流式
            if hasattr(self.planner, "plan_stream"):
                for event in self.planner.plan_stream(
                    profile_system_prompt=self.profile.render_system_prompt(),
                    user_query=user_query,
                    tools=self.tools.describe(),
                ):
                    if event["type"] == "thought":
                        yield {"type": "planning_thought", "content": event["content"]}
                    elif event["type"] == "plan":
                        plan = event["steps"]
                        yield {"type": "plan_generated", "plan": plan}
            else:
                # 降级到非流式
                yield {"type": "planning_thought", "content": "正在生成计划..."}
                plan = self.planner.plan(
                    profile_system_prompt=self.profile.render_system_prompt(),
                    user_query=user_query,
                    tools=self.tools.describe(),
                )
                yield {"type": "plan_generated", "plan": plan}

            logger.info(f"Plan generated with {len(plan)} steps")
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            yield {"type": "error", "content": f"Planning failed: {str(e)}"}
            return

        reply_text: str | None = None

        # 2) 逐步执行
        for i, step in enumerate(plan[: self.max_steps]):
            logger.debug(f"Executing step {i}: {step}")

            if step.get("type") == "reply":
                reply_text = step.get("text", "").strip()
                logger.info("Plan reached reply step")
                yield {"type": "reply", "content": reply_text}
                break

            if step.get("type") == "tool":
                name = step.get("name")
                arguments = step.get("arguments", {}) or {}

                yield {"type": "tool_start", "tool": name, "arguments": arguments}

                # Safety Check: Validate arguments against schema
                tools_meta = self.tools.describe()
                tool_desc = tools_meta.get(name) if isinstance(name, str) else None

                if not tool_desc:
                    error_msg = f"Tool '{name}' not found in registry"
                    logger.warning(error_msg)
                    obs = {
                        "step": i,
                        "tool": name,
                        "ok": False,
                        "error": error_msg,
                        "arguments": arguments,
                    }
                    observations.append(obs)
                    yield {"type": "tool_error", "tool": name, "error": error_msg}
                    continue

                schema = tool_desc.get("input_schema", {}) if tool_desc else {}
                miss = _missing_required(arguments, schema)

                if miss:
                    error_msg = f"Missing required fields: {miss}"
                    logger.warning(f"Tool '{name}' validation failed: {error_msg}")
                    obs = {
                        "step": i,
                        "tool": name,
                        "ok": False,
                        "error": error_msg,
                        "arguments": arguments,
                    }
                    observations.append(obs)
                    yield {"type": "tool_error", "tool": name, "error": error_msg}
                    continue

                t0 = time.time()
                try:
                    logger.info(f"Calling tool '{name}' with args: {arguments}")
                    out = self.tools.call(name, arguments)  # type: ignore[arg-type]
                    latency = int((time.time() - t0) * 1000)

                    obs = {
                        "step": i,
                        "tool": name,
                        "ok": True,
                        "latency_ms": latency,
                        "result": out,
                    }
                    observations.append(obs)
                    logger.info(f"Tool '{name}' success ({latency}ms)")
                    yield {"type": "tool_result", "tool": name, "result": out}

                except Exception as e:
                    latency = int((time.time() - t0) * 1000)
                    logger.error(f"Tool '{name}' failed: {e}")
                    obs = {
                        "step": i,
                        "tool": name,
                        "ok": False,
                        "latency_ms": latency,
                        "error": str(e),
                        "arguments": arguments,
                    }
                    observations.append(obs)
                    yield {"type": "tool_error", "tool": name, "error": str(e)}

        # 3) 汇总输出
        final_reply = ""

        if reply_text:
            final_reply = reply_text
        elif not observations:
            final_reply = "（没有可执行的步骤或工具返回空结果）"
        elif self.summarizer:
            yield {"type": "planning_thought", "content": "正在汇总执行结果..."}
            # 用你的生成器来生成自然语言总结
            profile_hint = self.profile.render_system_prompt()
            prompt = f"""请将以下工具步骤结果用中文简洁汇总给用户，保留关键信息和结论。

[Profile]
{profile_hint}

[Observations]
{observations}

只输出给用户的总结文本。"""
            messages = [
                {
                    "role": "system",
                    "content": "你是一个严谨的助理。只输出中文总结，不要额外解释。",
                },
                {"role": "user", "content": prompt},
            ]
            try:
                _, summary = self.summarizer.execute([None, messages])
                final_reply = summary.strip()
                yield {"type": "reply", "content": final_reply}
            except Exception as e:
                logger.error(f"Summarization failed: {e}")
                final_reply = "Summarization failed."
                yield {"type": "error", "content": "Summarization failed."}
        else:
            # 简单模板
            lines = []
            for obs in observations:
                if obs.get("ok"):
                    lines.append(f"#{obs['step'] + 1} 工具 {obs['tool']} 成功：{obs.get('result')}")
                else:
                    lines.append(f"#{obs['step'] + 1} 工具 {obs['tool']} 失败：{obs.get('error')}")
            final_reply = "\n".join(lines)
            yield {"type": "reply", "content": final_reply}

        yield {
            "type": "completed",
            "observations": observations,
            "plan": plan,
            "reply": final_reply,
        }

    def step(self, user_query: str) -> dict[str, Any]:
        """
        Execute a single turn of conversation.

        Returns:
            Dict containing:
            - reply: The final text response
            - observations: List of execution steps and results
            - plan: The original plan
        """
        # 兼容旧接口，收集流式结果
        result = {"reply": "", "observations": [], "plan": []}

        for event in self.step_stream(user_query):
            if event["type"] == "completed":
                result["reply"] = event.get("reply", "")
                result["observations"] = event.get("observations", [])
                result["plan"] = event.get("plan", [])

        return result

    def execute(self, data: Any) -> dict[str, Any]:
        """
        Unified Entry Point.

        Args:
            data: str (query) or dict (config + query)

        Returns:
            Dict containing 'reply', 'observations', 'plan'
        """
        # 形态 1：直接字符串
        if isinstance(data, str):
            return self.step(data)

        # 形态 2：字典
        if isinstance(data, dict):
            user_query = data.get("user_query") or data.get("query")
            if not isinstance(user_query, str) or not user_query.strip():
                raise ValueError(
                    "AgentRuntime.execute(dict) 需要提供 'user_query' 或 'query'（非空字符串）。"
                )

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
                except Exception:
                    # 失败则回退，不中断主流程
                    self.profile = original_profile

            try:
                return self.step(user_query)
            finally:
                # 还原
                self.max_steps = original_max
                self.profile = original_profile

        raise TypeError("AgentRuntime.execute 仅接受 str 或 dict 两种输入。")
