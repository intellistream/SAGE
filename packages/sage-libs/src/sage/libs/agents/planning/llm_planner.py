# sage/libs/agents/planning/llm_planner.py
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from sage.common.core.functions import MapFunction

PlanStep = Dict[
    str, Any
]  # MCP风格：{"type":"tool","name":"...","arguments":{...}} | {"type":"reply","text":"..."}


def _top_k_tools(
    user_query: str, tools: Dict[str, Dict[str, Any]], k: int = 6
) -> Dict[str, Dict[str, Any]]:
    """基于 name/description 的匹配."""
    uq = user_query.lower()
    scored: List[Tuple[str, float]] = []
    for name, meta in tools.items():
        txt = (name + " " + str(meta.get("description", ""))).lower()
        score = 0.0
        for token in re.findall(r"[a-zA-Z0-9_]+", uq):
            if token in txt:
                score += 1.0
        if name.lower() in uq:
            score += 1.5
        scored.append((name, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    keep = [n for n, s in scored[:k] if s > 0] or list(tools.keys())[
        : min(k, len(tools))
    ]
    return {n: tools[n] for n in keep}


def _build_prompt(
    profile_system_prompt: str, user_query: str, tools_subset: Dict[str, Dict[str, Any]]
) -> str:
    """
    把 Profile + 用户问题 + 工具清单 拼成一个强约束提示词，只允许输出 JSON。
    工具清单需包含 MCP 三要素：name/description/input_schema
    """
    tool_list = [
        {
            "name": name,
            "description": meta.get("description", ""),
            "input_schema": meta.get("input_schema", {}),
        }
        for name, meta in tools_subset.items()
    ]
    # 只输出 JSON，且必须是数组
    return f"""<SYSTEM>
You are a planning module. Produce a plan as a JSON array of steps.
Each step is EITHER:
  1) A tool call: {{"type":"tool","name":"<tool_name>","arguments":{{...}}}}
  2) A final reply: {{"type":"reply","text":"..."}}

Rules:
- Always call at least one tool before replying when tools are provided.
- Use ONLY the provided tools (names & schemas below).
- Arguments MUST follow the JSON Schema of the selected tool.
- Return ONLY the JSON array. Do NOT include extra text, code fences, or explanations.
- Keep steps concise. Conclude with a reply step once done.

</SYSTEM>

<PROFILE>
{profile_system_prompt}
</PROFILE>

<USER_QUERY>
{user_query}
</USER_QUERY>

<AVAILABLE_TOOLS>
{json.dumps(tool_list, ensure_ascii=False)}
</AVAILABLE_TOOLS>

Output: JSON array only.
"""


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        # ```json ... ``` or ``` ...
        t = t[3:]
        # 去掉语言标记
        if "\n" in t:
            t = t.split("\n", 1)[1]
        if t.endswith("```"):
            t = t[:-3]
    return t.strip()


def _coerce_json_array(text: str) -> Optional[List[Any]]:
    """
    容错解析：优先直接 loads；失败时尝试截取第一个 '[' 到最后一个 ']' 之间的内容。
    """
    t = _strip_code_fences(text)

    # 方法1：直接解析
    try:
        data = json.loads(t)
        if isinstance(data, list):
            return data
    except Exception:
        pass

    # 方法2：尝试在文本中捕捉一个 JSON 数组
    try:
        start = t.find("[")
        end = t.rfind("]")
        if start != -1 and end != -1 and end > start:
            snippet = t[start : end + 1]
            data = json.loads(snippet)
            if isinstance(data, list):
                return data
    except Exception:
        pass

    # 方法3：尝试使用正则表达式提取 JSON
    try:
        import re

        json_pattern = r"\[(?:[^[\]]*|\[[^\]]*\])*\]"
        matches = re.findall(json_pattern, t, re.DOTALL)
        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, list):
                    return data
            except Exception:
                continue
    except Exception:
        pass

    return None


def _validate_steps(
    steps: List[Dict[str, Any]], tools: Dict[str, Dict[str, Any]]
) -> List[PlanStep]:
    """
    轻量校验：结构正确性 + 工具是否存在 + 必填参数是否齐全（基于 schema.required）。
    不通过时，直接过滤掉错误步；
    """
    valid: List[PlanStep] = []
    for step in steps:
        if not isinstance(step, dict) or "type" not in step:
            continue

        if step["type"] == "reply":
            if isinstance(step.get("text"), str) and step["text"].strip():
                valid.append({"type": "reply", "text": step["text"].strip()})
            continue

        if step["type"] == "tool":
            name = step.get("name")
            args = step.get("arguments", {})
            if (
                not isinstance(name, str)
                or name not in tools
                or not isinstance(args, dict)
            ):
                continue

            # 基于 MCP input_schema 的必填项检查
            schema = tools[name].get("input_schema") or {}
            req = schema.get("required") or []
            if all(k in args for k in req):
                valid.append({"type": "tool", "name": name, "arguments": args})
            # 若缺少必填参数，丢弃该步（可扩展为“补齐参数”的对话步骤）
            continue
    # 保底：没有可执行步时，加一个 reply
    if not valid:
        valid = [{"type": "reply", "text": "（计划不可用）"}]
    return valid


class LLMPlanner(MapFunction):
    """
    用.rag.generator 中的 Generator（OpenAIGenerator / HFGenerator）产出 MCP 风格计划。
    统一接口：plan(profile_prompt, user_query, tools) -> List[PlanStep]
    """

    def __init__(
        self,
        generator,
        max_steps: int = 6,
        enable_repair: bool = True,
        topk_tools: int = 6,
    ):
        """
        :param generator: 你的 OpenAIGenerator 或 HFGenerator 实例（具备 .execute([user_query, prompt])）
        :param max_steps: 返回的最大步骤数
        :param enable_repair: 当 JSON 解析失败时，是否自动修复一次
        :param topk_tools: 传给模型的工具子集大小（减小提示长度与跑偏率）
        """
        self.generator = generator
        self.max_steps = max_steps
        self.enable_repair = enable_repair
        self.topk_tools = topk_tools

    def _ask_llm(self, prompt: str, user_query: str) -> str:
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_query},
        ]
        _, out = self.generator.execute([user_query, messages])
        return out

    def plan(
        self,
        profile_system_prompt: str,
        user_query: str,
        tools: Dict[str, Dict[str, Any]],
    ) -> List[PlanStep]:
        # 1) 缩小工具集合，减少上下文
        tools_subset = _top_k_tools(user_query, tools, k=self.topk_tools)

        # 2) 首次请求
        prompt = _build_prompt(profile_system_prompt, user_query, tools_subset)
        out = self._ask_llm(prompt, user_query)
        steps = _coerce_json_array(out)

        # 调试信息：记录原始输出
        if steps is None:
            print(f"🐛 Debug: 无法解析计划 JSON。原始输出:\n{out[:500]}...")

        # 3) 自动修复（仅一次）
        if steps is None and self.enable_repair:
            repair_prompt = (
                "Your output was invalid. Return ONLY a JSON array of steps. No prose, no fences.\n"
                'Example: [{"type":"tool","name":"...","arguments":{...}}, {"type":"reply","text":"..."}]'
            )
            _, out2 = self.generator.execute(
                [user_query, repair_prompt + "\n\nPrevious output:\n" + out]
            )
            steps = _coerce_json_array(out2)

            # 调试信息：记录修复后的输出
            if steps is None:
                print(f"🐛 Debug: 修复后仍无法解析 JSON。修复输出:\n{out2[:500]}...")

        # 4) 兜底：若仍无法解析，直接把原文作为 reply
        if steps is None:
            print("🐛 Debug: 使用兜底策略，返回原文作为回复")
            return [{"type": "reply", "text": out.strip()[:2000]}][: self.max_steps]

        # 5) 轻量合法化（结构+必填参数）
        steps = _validate_steps(steps, tools_subset)

        # 6) 截断并返回
        return steps[: self.max_steps]

    def _tools_to_manifest(self, tools_like: Any) -> Dict[str, Dict[str, Any]]:
        """
        支持：
        - 直接传工具清单 dict[str, {description,input_schema}]
        - 传 MCPRegistry 实例（具备 .describe()）
        """
        if isinstance(tools_like, dict):
            return tools_like
        if hasattr(tools_like, "describe") and callable(
            getattr(tools_like, "describe")
        ):
            return tools_like.describe()
        raise TypeError(
            "LLMPlanner expects `tools` as a dict manifest or an object with .describe()."
        )

    def execute(self, data: Any) -> List[PlanStep]:
        """
        统一入口，支持以下输入形态（任选其一）：
        1) dict：
           {
             "profile_prompt" | "profile_system_prompt": str,
             "user_query" | "query": str,
             "tools" | "registry": dict 或 具备 .describe() 的对象,
             # 可选： "topk": int    # 仅本次调用的临时 top-k 覆写
           }

        2) 三元组：(profile_prompt: str, user_query: str, tools_or_registry)

        返回：List[PlanStep]
        """
        # --- 形态 1：dict ---
        if isinstance(data, dict):
            profile_prompt = data.get("profile_prompt") or data.get(
                "profile_system_prompt"
            )
            user_query = data.get("user_query") or data.get("query")
            tools_like = data.get("tools") or data.get("registry")
            if (
                not isinstance(profile_prompt, str)
                or not isinstance(user_query, str)
                or tools_like is None
            ):
                raise ValueError(
                    "LLMPlanner.execute(dict) requires 'profile_prompt' (or 'profile_system_prompt'), "
                    "'user_query' (or 'query'), and 'tools' (or 'registry')."
                )

            # 临时 top-k 覆写（不修改实例字段）
            original_topk = self.topk_tools
            if "topk" in data:
                if not isinstance(data["topk"], int) or data["topk"] <= 0:
                    raise ValueError("'topk' must be a positive int.")
                self.topk_tools = data["topk"]

            try:
                tools_manifest = self._tools_to_manifest(tools_like)
                return self.plan(profile_prompt, user_query, tools_manifest)
            finally:
                # 还原
                self.topk_tools = original_topk

        # --- 形态 2：三元组 ---
        if isinstance(data, tuple) and len(data) == 3:
            profile_prompt, user_query, tools_like = data
            if not isinstance(profile_prompt, str) or not isinstance(user_query, str):
                raise TypeError("Tuple form must be (str, str, tools_or_registry).")
            tools_manifest = self._tools_to_manifest(tools_like)
            return self.plan(profile_prompt, user_query, tools_manifest)

        raise TypeError(
            "LLMPlanner.execute expects either a dict with keys "
            "('profile_prompt'/'profile_system_prompt', 'user_query'/'query', 'tools'/'registry') "
            "or a tuple (profile_prompt, user_query, tools_or_registry)."
        )
