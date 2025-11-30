"""
Agent SFT Data Formatter

Converts agent_sft dialog data into training format for LLM fine-tuning.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Iterator, Literal, Optional

logger = logging.getLogger(__name__)


class AgentSFTFormatter:
    """
    将 agent_sft 对话数据转换为 SFT 训练格式

    支持多种输出格式:
    - alpaca: {"instruction": str, "input": str, "output": str}
    - sharegpt: {"conversations": [{"from": str, "value": str}, ...]}
    - chatml: 直接拼接的 ChatML 格式字符串

    Example:
        >>> formatter = AgentSFTFormatter(output_format="alpaca")
        >>> formatted = formatter.format_dialog(dialog)
        >>> print(formatted["instruction"])
    """

    # ChatML 模板
    CHATML_SYSTEM = """你是一个智能助手，擅长使用工具完成复杂任务。

可用工具:
{tool_descriptions}

请按照以下格式回复:
1. 分析用户需求
2. 制定执行计划
3. 调用所需工具
4. 整合结果并回复"""

    TOOL_CALL_FORMAT = """<tool_call>
{{"name": "{tool_name}", "arguments": {arguments}}}
</tool_call>"""

    TOOL_RESULT_FORMAT = """<tool_result>
{result}
</tool_result>"""

    def __init__(
        self,
        output_format: str = "alpaca",
        include_tool_descriptions: bool = True,
        tool_loader: Optional[Any] = None,
        max_tools_in_prompt: int = 20,
        tool_call_style: Literal["generic", "qwen"] = "generic",
    ):
        """
        初始化格式化器

        Args:
            output_format: 输出格式 ("alpaca", "sharegpt", "chatml")
            include_tool_descriptions: 是否在 prompt 中包含工具描述
            tool_loader: 工具元数据加载器 (用于获取工具描述)
            max_tools_in_prompt: prompt 中最多包含的工具数
            tool_call_style: 工具调用格式 (generic / qwen)
        """
        self.output_format = output_format
        self.include_tool_descriptions = include_tool_descriptions
        self.tool_loader = tool_loader
        self.max_tools_in_prompt = max_tools_in_prompt
        self.tool_call_style = tool_call_style

        self._tool_cache: dict[str, dict] = {}

    def format_dialog(self, dialog: Any) -> dict:
        """
        转换单个对话为训练格式

        Args:
            dialog: AgentSFTDialog 对象

        Returns:
            格式化后的训练样本
        """
        if self.output_format == "alpaca":
            return self._format_alpaca(dialog)
        elif self.output_format == "sharegpt":
            return self._format_sharegpt(dialog)
        elif self.output_format == "chatml":
            return self._format_chatml(dialog)
        else:
            raise ValueError(f"Unknown output format: {self.output_format}")

    def format_batch(self, dialogs: list) -> list[dict]:
        """批量格式化对话"""
        return [self.format_dialog(d) for d in dialogs]

    def iter_formatted(self, dialogs: Iterator) -> Iterator[dict]:
        """迭代格式化对话"""
        for dialog in dialogs:
            try:
                yield self.format_dialog(dialog)
            except Exception as e:
                logger.warning(
                    "Failed to format dialog %s: %s",
                    getattr(dialog, "dialog_id", "unknown"),
                    e,
                )
                continue

    def _format_alpaca(self, dialog: Any) -> dict:
        """转换为 Alpaca 格式"""
        # 提取用户请求
        user_query = self._extract_user_query(dialog)

        # 构建指令 (包含工具描述)
        instruction = self._build_instruction(dialog)

        # 构建输出 (助手响应 + 工具调用)
        output = self._build_assistant_output(dialog)

        # 分类任务类型
        task_type = self._classify_task(dialog)

        return {
            "instruction": instruction,
            "input": user_query,
            "output": output,
            "task_type": task_type,
            "dialog_id": getattr(dialog, "dialog_id", None),
            "target_tools": getattr(dialog, "target_tools", []),
            "metadata": getattr(dialog, "metadata", {}),
        }

    def _format_sharegpt(self, dialog: Any) -> dict:
        """转换为 ShareGPT 格式"""
        conversations = []

        # 添加系统提示
        tool_descriptions = self._get_tool_descriptions(getattr(dialog, "target_tools", []))
        system_prompt = self.CHATML_SYSTEM.format(tool_descriptions=tool_descriptions)
        conversations.append({"from": "system", "value": system_prompt})

        # 转换对话轮次
        for turn in getattr(dialog, "turns", []):
            if turn.role == "user":
                conversations.append({"from": "human", "value": turn.content})
            elif turn.role == "assistant":
                conversations.append({"from": "gpt", "value": turn.content})
            elif turn.role == "tool":
                # 工具结果作为 observation
                formatted = self._format_tool_result(
                    getattr(turn, "tool_id", "unknown"),
                    getattr(turn, "result", turn.content),
                )
                conversations.append({"from": "observation", "value": formatted})

        return {
            "conversations": conversations,
            "dialog_id": getattr(dialog, "dialog_id", None),
            "task_type": self._classify_task(dialog),
        }

    def _format_chatml(self, dialog: Any) -> dict:
        """转换为 ChatML 格式字符串"""
        parts = []

        # 系统提示
        tool_descriptions = self._get_tool_descriptions(getattr(dialog, "target_tools", []))
        system_prompt = self.CHATML_SYSTEM.format(tool_descriptions=tool_descriptions)
        parts.append(f"<|im_start|>system\n{system_prompt}<|im_end|>")

        # 对话轮次
        for turn in getattr(dialog, "turns", []):
            if turn.role == "user":
                parts.append(f"<|im_start|>user\n{turn.content}<|im_end|>")
            elif turn.role == "assistant":
                parts.append(f"<|im_start|>assistant\n{turn.content}<|im_end|>")
            elif turn.role == "tool":
                tool_result = getattr(turn, "result", turn.content)
                parts.append(f"<|im_start|>tool\n{tool_result}<|im_end|>")

        return {
            "text": "\n".join(parts),
            "dialog_id": getattr(dialog, "dialog_id", None),
            "task_type": self._classify_task(dialog),
        }

    def _extract_user_query(self, dialog: Any) -> str:
        """提取用户请求"""
        turns = getattr(dialog, "turns", [])
        for turn in turns:
            if turn.role == "user":
                return turn.content
        return getattr(dialog, "goal", "")

    def _build_instruction(self, dialog: Any) -> str:
        """构建指令 (包含任务目标和工具描述)"""
        parts = []

        # 任务目标
        goal = getattr(dialog, "goal", "")
        if goal:
            parts.append(f"任务目标: {goal}")

        # 工具描述
        if self.include_tool_descriptions:
            target_tools = getattr(dialog, "target_tools", [])
            tool_desc = self._get_tool_descriptions(target_tools)
            if tool_desc:
                parts.append(f"\n可用工具:\n{tool_desc}")

        return "\n".join(parts) if parts else "完成用户请求"

    def _build_assistant_output(self, dialog: Any) -> str:
        """构建助手输出 (包含思考过程和工具调用)"""
        output_parts = []

        turns = getattr(dialog, "turns", [])
        for turn in turns:
            if turn.role == "assistant":
                # 助手思考/响应
                content = turn.content
                # 检测是否包含工具调用意图
                if self._contains_tool_intent(content):
                    output_parts.append(f"<think>\n{content}\n</think>")
                else:
                    output_parts.append(content)

            elif turn.role == "tool":
                # 工具调用和结果
                tool_id = getattr(turn, "tool_id", "unknown")
                tool_result = getattr(turn, "result", turn.content)
                tool_content = getattr(turn, "content", "")

                # 格式化工具调用
                tool_call = self._format_tool_call(tool_id, tool_content)
                output_parts.append(tool_call)

                # 格式化工具结果
                result_formatted = self._format_tool_result(tool_id, tool_result)
                output_parts.append(result_formatted)

        return "\n".join(output_parts)

    def _get_tool_descriptions(self, tool_ids: list[str]) -> str:
        """获取工具描述"""
        if not tool_ids or not self.tool_loader:
            return ""

        descriptions = []
        for tool_id in tool_ids[: self.max_tools_in_prompt]:
            if tool_id in self._tool_cache:
                tool = self._tool_cache[tool_id]
            else:
                tool = self.tool_loader.get_tool(tool_id)
                if tool:
                    self._tool_cache[tool_id] = tool

            if tool:
                name = getattr(tool, "name", tool_id)
                desc = getattr(tool, "description", "")
                descriptions.append(f"- {name}: {desc}")

        return "\n".join(descriptions)

    def _format_tool_call(self, tool_id: str, raw_arguments: str) -> str:
        arguments = self._extract_tool_arguments(raw_arguments)

        if self.tool_call_style == "qwen":
            payload = {
                "name": tool_id,
                "arguments": arguments,
            }
            return "<tool_call>\n" + json.dumps(payload, ensure_ascii=False) + "\n</tool_call>"

        return self.TOOL_CALL_FORMAT.format(
            tool_name=tool_id,
            arguments=json.dumps(arguments, ensure_ascii=False),
        )

    def _format_tool_result(self, tool_id: str, raw_result: Any) -> str:
        result_payload = {
            "name": tool_id,
            "result": raw_result,
        }

        if self.tool_call_style == "qwen":
            return (
                "<tool_response>\n"
                + json.dumps(result_payload, ensure_ascii=False)
                + "\n</tool_response>"
            )

        return self.TOOL_RESULT_FORMAT.format(result=raw_result)

    def _extract_tool_arguments(self, content: str) -> dict:
        if not content:
            return {}

        stripped = content.strip()
        if not stripped:
            return {}

        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                return parsed
            return {"value": parsed}
        except json.JSONDecodeError:
            return {"input": stripped}

    def _classify_task(self, dialog: Any) -> str:
        """
        根据对话内容分类任务类型

        Returns:
            任务类型: "tool_selection", "multi_step_planning",
                      "timing_decision", "tool_retrieval"
        """
        metadata = getattr(dialog, "metadata", {})

        # 优先使用 metadata 中的分类
        if "task_type" in metadata:
            return metadata["task_type"]

        turns = getattr(dialog, "turns", [])
        target_tools = getattr(dialog, "target_tools", [])

        # 基于规则的分类
        tool_count = len(target_tools)
        turn_count = len(turns)
        assistant_turns = [t for t in turns if t.role == "assistant"]

        # 多步规划: 多个工具 + 多轮对话
        if tool_count >= 3 or turn_count >= 8:
            return "multi_step_planning"

        # 工具检索: metadata 标记或包含检索关键词
        goal = getattr(dialog, "goal", "").lower()
        if "search" in goal or "find" in goal or "retrieve" in goal:
            return "tool_retrieval"

        # 时机判断: 包含条件判断或等待
        for turn in assistant_turns:
            content = turn.content.lower()
            if any(kw in content for kw in ["if", "when", "wait", "check", "condition"]):
                return "timing_decision"

        # 默认: 工具选择
        return "tool_selection"

    def _contains_tool_intent(self, content: str) -> bool:
        """检测内容是否包含工具调用意图"""
        # 简单的关键词检测
        tool_patterns = [
            r"call\s+\w+",
            r"use\s+\w+\s+tool",
            r"invoke\s+\w+",
            r"execute\s+\w+",
            r"step\s+\d+",
            r"first.*then",
        ]

        content_lower = content.lower()
        for pattern in tool_patterns:
            if re.search(pattern, content_lower):
                return True
        return False


class PreferenceDataFormatter:
    """
    DPO 偏好数据格式化器

    将对话数据转换为偏好对格式:
    {"prompt": str, "chosen": str, "rejected": str}
    """

    def __init__(self, sft_formatter: Optional[AgentSFTFormatter] = None):
        self.sft_formatter = sft_formatter or AgentSFTFormatter()

    def format_preference_pair(
        self,
        prompt: str,
        chosen_response: str,
        rejected_response: str,
        chosen_score: float = 1.0,
        rejected_score: float = 0.0,
    ) -> dict:
        """
        格式化单个偏好对

        Args:
            prompt: 输入提示
            chosen_response: 偏好的响应
            rejected_response: 非偏好的响应
            chosen_score: 偏好响应的分数
            rejected_score: 非偏好响应的分数

        Returns:
            格式化的偏好对
        """
        return {
            "prompt": prompt,
            "chosen": chosen_response,
            "rejected": rejected_response,
            "chosen_score": chosen_score,
            "rejected_score": rejected_score,
            "margin": chosen_score - rejected_score,
        }

    def format_from_ranked_responses(
        self,
        prompt: str,
        responses: list[str],
        scores: list[float],
    ) -> list[dict]:
        """
        从排序的响应列表生成所有偏好对

        Args:
            prompt: 输入提示
            responses: 响应列表
            scores: 对应的分数列表

        Returns:
            所有可能的偏好对列表
        """
        if len(responses) != len(scores):
            raise ValueError("responses and scores must have same length")

        # 按分数排序
        sorted_pairs = sorted(zip(responses, scores), key=lambda x: x[1], reverse=True)

        preference_pairs = []

        # 生成所有 (i, j) 对，其中 score[i] > score[j]
        for i in range(len(sorted_pairs)):
            for j in range(i + 1, len(sorted_pairs)):
                chosen_resp, chosen_score = sorted_pairs[i]
                rejected_resp, rejected_score = sorted_pairs[j]

                # 只有当分数差异显著时才生成偏好对
                if chosen_score - rejected_score > 0.1:
                    preference_pairs.append(
                        self.format_preference_pair(
                            prompt=prompt,
                            chosen_response=chosen_resp,
                            rejected_response=rejected_resp,
                            chosen_score=chosen_score,
                            rejected_score=rejected_score,
                        )
                    )

        return preference_pairs
