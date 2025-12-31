# -*- coding: utf-8 -*-
"""
多主题摘要生成（Multi-Topic Summarization）

基于 MemoryOS 论文实现的对话主题拆分和摘要生成功能。
使用 LLM 将多主题对话拆分为独立的主题段落，每个段落包含：
- 主题标签（theme）
- 对话内容（dialogue）
- 关键词（keywords）
- 主题摘要（summary）

References:
    MemoryOS: Memory OS of AI Agent (arXiv:2506.06326)
    https://github.com/BAI-LAB/MemoryOS
"""

import json
import logging
from typing import Any

from sage.benchmark.benchmark_memory.experiment.libs.pre_insert.base import BasePreInsertAction

logger = logging.getLogger(__name__)


MULTI_SUMMARY_PROMPT = """You are an intelligent assistant for analyzing conversations. Given multiple rounds of dialogue, your task is to:

1. Identify different topics in the conversation
2. Split the dialogue into segments by topic
3. For each segment, extract:
   - Theme: The main topic of this segment
   - Dialogue: The conversation content related to this theme
   - Keywords: 3-5 key terms that represent this topic
   - Summary: A brief summary (1-2 sentences) of this topic segment

Input dialogue:
{dialogue}

Output format (JSON):
{{
  "segments": [
    {{
      "theme": "topic name",
      "dialogue": ["user message 1", "assistant response 1", ...],
      "keywords": ["keyword1", "keyword2", ...],
      "summary": "Brief summary of this topic"
    }},
    ...
  ]
}}

Please output ONLY the JSON object, no additional text."""


class MultiSummaryAction(BasePreInsertAction):
    """多主题摘要生成 Action"""

    def _init_action(self) -> None:
        """初始化 Action 参数"""
        self.max_themes = self.config.get("max_themes", 5)
        self.min_dialogue_turns = self.config.get("min_dialogue_turns", 3)
        self.enable_keywords = self.config.get("enable_keywords", True)
        self.enable_summary = self.config.get("enable_summary", True)
        self._llm_generator = None

        logger.info(
            f"MultiSummaryAction initialized: max_themes={self.max_themes}, "
            f"min_dialogue_turns={self.min_dialogue_turns}"
        )

    def set_llm_generator(self, generator: Any) -> None:
        """设置 LLM 生成器（由 Operator 调用）"""
        self._llm_generator = generator

    def execute(self, input_data) -> Any:
        """
        执行多主题摘要生成

        Args:
            input_data: PreInsertInput 对象，包含对话数据

        Returns:
            PreInsertOutput 对象，包含处理后的记忆条目
        """
        from sage.benchmark.benchmark_memory.experiment.libs.pre_insert.base import PreInsertOutput

        # 提取数据
        data = input_data.data
        dialogue = data.get("dialogue", {})
        dialogue_history = dialogue.get("messages", [])

        try:
            # 1. 检查对话轮数
            if len(dialogue_history) < self.min_dialogue_turns:
                logger.debug(
                    f"Dialogue too short ({len(dialogue_history)} turns), "
                    f"minimum required: {self.min_dialogue_turns}"
                )
                # 返回原始单条记忆
                return PreInsertOutput(
                    memory_entries=[
                        {
                            "text": dialogue.get("full_text", ""),
                            "metadata": {
                                "dialogue_idx": data.get("dialogue_idx"),
                                "session_id": data.get("session_id"),
                                "num_segments": 0,
                                "status": "skipped",
                            },
                        }
                    ]
                )

            # 2. 格式化对话内容
            formatted_dialogue = self._format_dialogue(dialogue_history)

            # 3. 构建 LLM 提示词
            prompt = MULTI_SUMMARY_PROMPT.format(dialogue=formatted_dialogue)

            # 4. 调用 LLM
            logger.debug(
                f"Calling LLM for multi-topic summarization, dialogue length: {len(dialogue_history)}"
            )
            llm_response = self._llm_generator.generate(prompt)

            # 5. 解析 LLM 响应
            segments = self._parse_llm_response(llm_response)

            # 6. 限制主题数量
            if len(segments) > self.max_themes:
                logger.warning(
                    f"Too many themes detected ({len(segments)}), limiting to {self.max_themes}"
                )
                segments = segments[: self.max_themes]

            # 7. 后处理：确保每个段落包含必要字段
            for segment in segments:
                if not self.enable_keywords:
                    segment.pop("keywords", None)
                if not self.enable_summary:
                    segment.pop("summary", None)

            # 8. 创建记忆条目
            memory_entries = []
            for idx, segment in enumerate(segments):
                # 为每个 segment 创建一个摘要记忆条目
                summary_text = segment.get("summary", "")
                keywords = segment.get("keywords", [])
                theme = segment.get("theme", f"Topic {idx + 1}")

                memory_entries.append(
                    {
                        "text": summary_text,
                        "metadata": {
                            "is_segment_summary": True,  # 标记为 Segment 摘要
                            "theme": theme,
                            "keywords": keywords,
                            "segment_idx": idx,
                            "dialogue_idx": data.get("dialogue_idx"),
                            "session_id": data.get("session_id"),
                            "tier": "mtm",  # 【关键修复】指定插入到 MTM 层
                        },
                    }
                )

            logger.info(f"Multi-summary completed: {len(segments)} segments extracted")
            return PreInsertOutput(
                memory_entries=memory_entries,
                metadata={"num_segments": len(segments), "status": "success"},
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            # 返回原始单条记忆
            from sage.benchmark.benchmark_memory.experiment.libs.pre_insert.base import (
                PreInsertOutput,
            )

            return PreInsertOutput(
                memory_entries=[
                    {
                        "text": dialogue.get("full_text", ""),
                        "metadata": {
                            "dialogue_idx": data.get("dialogue_idx"),
                            "session_id": data.get("session_id"),
                            "error": "json_parse_error",
                        },
                    }
                ]
            )

        except Exception as e:
            logger.error(f"Error in multi-summary execution: {e}", exc_info=True)
            # 返回原始单条记忆
            from sage.benchmark.benchmark_memory.experiment.libs.pre_insert.base import (
                PreInsertOutput,
            )

            return PreInsertOutput(
                memory_entries=[
                    {
                        "text": dialogue.get("full_text", ""),
                        "metadata": {
                            "dialogue_idx": data.get("dialogue_idx"),
                            "session_id": data.get("session_id"),
                            "error": "execution_error",
                        },
                    }
                ]
            )

    def _format_dialogue(self, dialogue_history: list[dict[str, Any]]) -> str:
        """
        格式化对话历史为字符串

        Args:
            dialogue_history: 对话历史列表

        Returns:
            格式化后的对话字符串
        """
        formatted_lines = []
        for idx, turn in enumerate(dialogue_history, 1):
            role = turn.get("role", "unknown")
            content = turn.get("content", "")

            # 格式化为 "Role: content" 形式
            if role == "user":
                formatted_lines.append(f"User: {content}")
            elif role == "assistant":
                formatted_lines.append(f"Assistant: {content}")
            else:
                formatted_lines.append(f"{role.capitalize()}: {content}")

        return "\n".join(formatted_lines)

    def _parse_llm_response(self, llm_response: str) -> list[dict[str, Any]]:
        """
        解析 LLM 返回的 JSON 响应

        Args:
            llm_response: LLM 返回的字符串

        Returns:
            分段列表

        Raises:
            json.JSONDecodeError: JSON 解析失败
            ValueError: 响应格式不符合预期
        """
        # 清理响应：移除可能的 markdown 代码块标记
        response_text = llm_response.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        # 解析 JSON
        parsed = json.loads(response_text)

        # 验证格式
        if not isinstance(parsed, dict) or "segments" not in parsed:
            raise ValueError("LLM response missing 'segments' field")

        segments = parsed["segments"]
        if not isinstance(segments, list):
            raise ValueError("'segments' field must be a list")

        # 验证每个段落的必要字段
        validated_segments = []
        for idx, segment in enumerate(segments):
            if not isinstance(segment, dict):
                logger.warning(f"Segment {idx} is not a dict, skipping")
                continue

            # 必要字段检查
            if "theme" not in segment or "dialogue" not in segment:
                logger.warning(f"Segment {idx} missing required fields, skipping")
                continue

            # 确保 dialogue 是列表
            if not isinstance(segment["dialogue"], list):
                segment["dialogue"] = [str(segment["dialogue"])]

            # 确保 keywords 是列表（如果存在）
            if "keywords" in segment and not isinstance(segment["keywords"], list):
                segment["keywords"] = [str(segment["keywords"])]

            validated_segments.append(segment)

        if not validated_segments:
            raise ValueError("No valid segments found in LLM response")

        return validated_segments

    def _create_single_segment(
        self, dialogue_history: list[dict[str, Any]], reason: str
    ) -> dict[str, Any]:
        """
        创建单一段落（降级方案）

        当 LLM 调用失败或解析失败时，将整个对话作为单一主题返回

        Args:
            dialogue_history: 对话历史列表
            reason: 降级原因

        Returns:
            包含单一段落的结果字典
        """
        logger.warning(f"Falling back to single segment due to: {reason}")

        # 提取所有对话内容
        dialogue_content = []
        for turn in dialogue_history:
            role = turn.get("role", "unknown")
            content = turn.get("content", "")
            dialogue_content.append(f"{role}: {content}")

        # 创建单一段落
        single_segment = {
            "theme": "General Conversation",
            "dialogue": dialogue_content,
        }

        if self.enable_keywords:
            single_segment["keywords"] = ["conversation"]

        if self.enable_summary:
            single_segment["summary"] = f"A conversation with {len(dialogue_history)} turns"

        return {
            "segments": [single_segment],
            "num_segments": 1,
            "status": "fallback",
            "reason": reason,
        }
