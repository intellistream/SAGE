# -*- coding: utf-8 -*-
"""
连续性检查（Continuity Check）
用于在插入对话记忆前，检查当前对话与之前对话的连续性，并为连续对话链生成概述信息。
支持 LLM 和 Simple 两种检查方法。
"""

import json
import logging
import time
from typing import Any, Optional

from sage.benchmark.benchmark_memory.experiment.libs.pre_insert.base import BasePreInsertAction

logger = logging.getLogger(__name__)

# LLM 连续性检查提示词
CONTINUITY_CHECK_PROMPT = """你是一个对话连续性分析专家。请分析以下两段对话是否在逻辑上连续。

前一段对话：
{previous_dialog}

当前对话：
{current_dialog}

时间间隔：{time_gap}秒

请判断这两段对话是否连续，并以JSON格式返回：
{{
    "is_continuous": true/false,
    "confidence": 0.0-1.0,
    "reason": "判断理由"
}}

判断依据：
1. 话题是否相关或延续
2. 时间间隔是否合理（{time_threshold}秒内更可能连续）
3. 上下文是否衔接
4. 人物、事件、情感是否一致
"""

# 对话链概述提示词
META_INFO_PROMPT = """你是一个对话摘要专家。请为以下连续对话链生成简洁的概述信息。

对话链内容：
{dialogue_chain}

请以JSON格式返回概述：
{{
    "summary": "对话链的主要内容概述（50-100字）",
    "main_topics": ["主题1", "主题2", "主题3"],
    "key_entities": ["实体1", "实体2"],
    "sentiment": "整体情感倾向",
    "time_span": "时间跨度描述"
}}
"""


class ContinuityCheckAction(BasePreInsertAction):
    """连续性检查动作类"""

    def _init_action(self) -> None:
        """
        初始化连续性检查动作

        从 self.config 中读取：
            - time_threshold: 时间阈值（秒），超过此值认为不连续
            - check_method: 检查方法 ("llm" 或 "simple")
            - similarity_threshold: Simple方法的相似度阈值
            - max_chain_length: 最大链长度
        """
        self.time_threshold = self.config.get("time_threshold", 3600)  # 默认1小时
        self.check_method = self.config.get("check_method", "llm")
        self.similarity_threshold = self.config.get("similarity_threshold", 0.3)
        self.max_chain_length = self.config.get("max_chain_length", 10)

        logger.info(
            f"ContinuityCheckAction initialized: method={self.check_method}, "
            f"time_threshold={self.time_threshold}s, "
            f"similarity_threshold={self.similarity_threshold}"
        )

    def execute(
        self,
        current_dialog: dict[str, Any],
        previous_dialog: Optional[dict[str, Any]],
        llm_generator: Any,
        **kwargs,
    ) -> dict[str, Any]:
        """
        执行连续性检查

        Args:
            current_dialog: 当前对话
            previous_dialog: 前一个对话（可能为None）
            llm_generator: LLM生成器
            **kwargs: 其他参数

        Returns:
            包含检查结果的字典
        """
        start_time = time.time()
        result = {
            "is_continuous": False,
            "confidence": 0.0,
            "reason": "",
            "pre_page": None,
            "next_page": None,
            "meta_info": None,
            "dialogue_chain": [],
        }

        try:
            # 如果没有前一个对话，则不连续
            if previous_dialog is None:
                result["reason"] = "没有前置对话"
                logger.debug(f"No previous dialog for current: {current_dialog.get('id')}")
                return result

            # 检查连续性
            is_continuous, confidence, reason = self._check_continuity(
                current_dialog, previous_dialog, llm_generator
            )

            result["is_continuous"] = is_continuous
            result["confidence"] = confidence
            result["reason"] = reason

            # 如果连续，建立链接
            if is_continuous:
                current_dialog["pre_page"] = previous_dialog.get("id")
                previous_dialog["next_page"] = current_dialog.get("id")

                result["pre_page"] = previous_dialog.get("id")
                result["next_page"] = current_dialog.get("id")

                # 构建对话链（回溯）
                dialogue_chain = self._build_dialogue_chain(current_dialog, previous_dialog)
                result["dialogue_chain"] = dialogue_chain

                # 生成meta_info（如果链足够长）
                if len(dialogue_chain) >= 2:
                    meta_info = self._generate_meta_info(dialogue_chain, llm_generator)
                    result["meta_info"] = meta_info
                    current_dialog["meta_info"] = meta_info

                logger.info(
                    f"Continuity detected: {previous_dialog.get('id')} -> {current_dialog.get('id')}, "
                    f"confidence={confidence:.2f}, chain_length={len(dialogue_chain)}"
                )
            else:
                logger.debug(f"Not continuous: {reason}")

            execution_time = time.time() - start_time
            logger.debug(f"ContinuityCheck executed in {execution_time:.3f}s")

        except Exception as e:
            logger.error(f"Error in continuity check: {e}", exc_info=True)
            result["reason"] = f"检查失败: {str(e)}"

        return result

    def _check_continuity(
        self, current: dict[str, Any], previous: dict[str, Any], llm_generator: Any
    ) -> tuple:
        """
        检查两个对话的连续性

        Returns:
            (is_continuous, confidence, reason)
        """
        # 计算时间间隔
        current_time = current.get("timestamp", 0)
        previous_time = previous.get("timestamp", 0)
        time_gap = abs(current_time - previous_time)

        # 时间间隔过大，直接判断不连续
        if time_gap > self.time_threshold:
            return False, 0.0, f"时间间隔过大: {time_gap}秒 > {self.time_threshold}秒"

        # 根据方法选择检查策略
        if self.check_method == "llm":
            return self._check_continuity_llm(current, previous, time_gap, llm_generator)
        else:
            return self._check_continuity_simple(current, previous)

    def _check_continuity_llm(
        self, current: dict[str, Any], previous: dict[str, Any], time_gap: float, llm_generator: Any
    ) -> tuple:
        """使用 LLM 检查连续性"""
        try:
            # 格式化对话内容
            current_text = self._format_dialogue_entry(current)
            previous_text = self._format_dialogue_entry(previous)

            # 构建提示词
            prompt = CONTINUITY_CHECK_PROMPT.format(
                previous_dialog=previous_text,
                current_dialog=current_text,
                time_gap=time_gap,
                time_threshold=self.time_threshold,
            )

            # 调用 LLM
            response = llm_generator.generate(prompt)

            # 解析响应
            result_json = json.loads(response)
            is_continuous = result_json.get("is_continuous", False)
            confidence = result_json.get("confidence", 0.0)
            reason = result_json.get("reason", "")

            return is_continuous, confidence, reason

        except Exception as e:
            logger.error(f"LLM continuity check failed: {e}")
            # 降级到 Simple 方法
            return self._check_continuity_simple(current, previous)

    def _check_continuity_simple(self, current: dict[str, Any], previous: dict[str, Any]) -> tuple:
        """使用简单方法（关键词重叠）检查连续性"""
        try:
            # 提取关键词
            current_keywords = self._extract_keywords(current)
            previous_keywords = self._extract_keywords(previous)

            # 计算 Jaccard 相似度
            if not current_keywords or not previous_keywords:
                return False, 0.0, "无法提取关键词"

            intersection = len(current_keywords & previous_keywords)
            union = len(current_keywords | previous_keywords)
            similarity = intersection / union if union > 0 else 0.0

            is_continuous = similarity >= self.similarity_threshold
            reason = f"关键词相似度: {similarity:.2f}"

            return is_continuous, similarity, reason

        except Exception as e:
            logger.error(f"Simple continuity check failed: {e}")
            return False, 0.0, f"检查失败: {str(e)}"

    def _extract_keywords(self, dialog: dict[str, Any]) -> set[str]:
        """提取对话关键词（简单实现：分词+停用词过滤）"""
        keywords = set()

        # 获取对话内容
        content = dialog.get("content", "")
        if isinstance(content, list):
            content = " ".join([msg.get("content", "") for msg in content])

        # 简单分词（按空格和标点）
        import re

        words = re.findall(r"\w+", content.lower())

        # 过滤停用词（简化版）
        stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "this",
            "that",
        }

        keywords = {w for w in words if len(w) > 2 and w not in stopwords}

        return keywords

    def _build_dialogue_chain(
        self, current: dict[str, Any], previous: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """构建对话链（回溯）"""
        chain = [current, previous]

        # 回溯pre_page（限制最大长度）
        temp = previous
        while len(chain) < self.max_chain_length:
            pre_id = temp.get("pre_page")
            if not pre_id:
                break
            # 注意：这里假设可以访问到之前的对话，实际需要从存储中读取
            # 简化实现：仅使用当前和前一个
            break

        return chain

    def _generate_meta_info(
        self, dialogue_chain: list[dict[str, Any]], llm_generator: Any
    ) -> Optional[dict[str, Any]]:
        """为对话链生成概述信息"""
        try:
            # 格式化对话链
            chain_text = "\n\n".join(
                [self._format_dialogue_entry(dialog) for dialog in dialogue_chain]
            )

            # 构建提示词
            prompt = META_INFO_PROMPT.format(dialogue_chain=chain_text)

            # 调用 LLM
            response = llm_generator.generate(prompt)

            # 解析响应
            meta_info = json.loads(response)

            logger.info(f"Generated meta_info for chain of length {len(dialogue_chain)}")
            return meta_info

        except Exception as e:
            logger.error(f"Failed to generate meta_info: {e}")
            return None

    def _format_dialogue_entry(self, dialog: dict[str, Any]) -> str:
        """格式化对话条目为文本"""
        content = dialog.get("content", "")
        if isinstance(content, list):
            lines = []
            for msg in content:
                role = msg.get("role", "unknown")
                text = msg.get("content", "")
                lines.append(f"{role}: {text}")
            content = "\n".join(lines)

        timestamp = dialog.get("timestamp", "")
        dialog_id = dialog.get("id", "unknown")

        return f"[{dialog_id}] @ {timestamp}\n{content}"
