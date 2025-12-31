"""SegmentDenoiseAction - SeCom 语义分段 + 压缩去噪

将对话按语义分段，并对每个段落进行压缩去噪。
这是 SeCom 论文的核心特性。

实现要点：
1. 语义分段：使用 LLM 识别话题边界（GPT-4o-mini）
2. 压缩去噪：使用 LLMLingua-2 或 LLM prompt 去除冗余和噪声
3. 数据分离：压缩后的摘要存储在 metadata.summary 中，原始对话保留在 text 字段
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import BasePreInsertAction, PreInsertInput, PreInsertOutput

if TYPE_CHECKING:
    from sage.benchmark.benchmark_memory.experiment.utils import LLMGenerator


class SegmentDenoiseAction(BasePreInsertAction):
    """SeCom 语义分段 + 压缩去噪 Action

    配置参数:
    segmentation:
        method: "semantic_clustering"  # 语义聚类分段
        min_segment_length: 3          # 最小段落长度（轮次）
        max_segment_length: 10         # 最大段落长度
        similarity_threshold: 0.75     # 段内相似度阈值

    denoising_prompt: str             # 压缩去噪的 LLM prompt
    store_summary_in_metadata: bool   # True: 摘要存metadata，原文存text（推荐）
                                       # False: 摘要替换text（当前实现）
    """

    def _init_action(self) -> None:
        """初始化分段和去噪参数"""
        # 分段配置
        seg_config = self.config.get("segmentation", {})
        self.seg_method = seg_config.get("method", "semantic_clustering")
        self.min_segment_length = seg_config.get("min_segment_length", 3)
        self.max_segment_length = seg_config.get("max_segment_length", 10)
        self.similarity_threshold = seg_config.get("similarity_threshold", 0.75)

        # 去噪 prompt
        self.denoising_prompt = self.config.get("denoising_prompt", "")

        # TODO: 实现数据分离支持
        self.store_summary_in_metadata = self.config.get("store_summary_in_metadata", False)

    def set_llm_generator(self, llm_generator: LLMGenerator) -> None:
        """注入 LLM 生成器"""
        self.llm_generator = llm_generator

    def execute(self, input_data: PreInsertInput) -> PreInsertOutput:
        """执行语义分段 + 压缩去噪

        Args:
            input_data: 包含 dialogs 的输入数据

        Returns:
            包含处理后段落的输出
        """
        # 提取对话数据
        dialogs = input_data.data.get("dialogs", [])

        # Step 1: 语义分段
        segments = self._segment_by_semantic(dialogs)

        # Step 2: 压缩去噪
        entries = []
        for i, segment in enumerate(segments):
            original_text = self._format_dialogue(segment)

            # 去噪：使用 LLM 压缩对话
            compressed_text = self._compress_with_llm(original_text)

            # 构建记忆条目
            if self.store_summary_in_metadata:
                # TODO: 实现数据分离 - 压缩摘要存metadata，原文存text
                entry = {
                    "text": original_text,  # 保留原始对话
                    "metadata": {
                        "action": "transform.segment_denoise",
                        "summary": compressed_text,  # 压缩摘要存metadata
                        "segment_index": i,
                        "total_segments": len(segments),
                        "segment_length": len(segment),
                        "method": self.seg_method,
                    },
                }
            else:
                # 当前实现：压缩文本替换原文（会导致QA准确性下降）
                entry = {
                    "text": compressed_text,  # 使用压缩后的文本
                    "metadata": {
                        "action": "transform.segment_denoise",
                        "original_length": len(original_text),
                        "compressed_length": len(compressed_text),
                        "segment_index": i,
                        "total_segments": len(segments),
                        "segment_length": len(segment),
                        "method": self.seg_method,
                    },
                }

            entry = self._set_default_fields(entry)
            entry["insert_method"] = "segment_insert"
            entries.append(entry)

        return PreInsertOutput(
            memory_entries=entries,
            metadata={
                "total_segments": len(segments),
                "method": self.seg_method,
                "store_summary_in_metadata": self.store_summary_in_metadata,
            },
        )

    def _segment_by_semantic(self, dialogs: list[dict[str, str]]) -> list[list[dict[str, str]]]:
        """语义分段：使用 LLM 识别话题边界

        Args:
            dialogs: 对话列表 [{"role": "user"/"assistant", "content": "..."}]

        Returns:
            分段列表，每段是一个对话列表
        """
        if not dialogs:
            return []

        if self.seg_method == "semantic_clustering" and hasattr(self, "llm_generator"):
            return self._segment_with_llm(dialogs)

        # 回退到简单策略
        return self._segment_simple(dialogs)

    def _segment_with_llm(self, dialogs: list[dict[str, str]]) -> list[list[dict[str, str]]]:
        """使用 LLM 进行语义分段（SeCom 原始实现）

        参考 SeCom 的 segment_with_exchange_number.md prompt
        """
        # 构造对话文本（带exchange编号）
        dialogue_text = ""
        for idx, dialog in enumerate(dialogs, start=1):
            role = dialog.get("role", "unknown")
            content = dialog.get("content", "")
            dialogue_text += f"[Exchange {idx}] {role.capitalize()}: {content}\n"

        # SeCom 分段 prompt（优化：直接输出，无额外解释）
        prompt = f"""Segment this dialogue by topic. Output ONLY JSONL (no explanation).

Constraints: min_length={self.min_segment_length}, max_length={self.max_segment_length}

Dialogue:
{dialogue_text}

JSONL (one line per segment):
{{"segment_id": 1, "start_exchange": X, "end_exchange": Y, "topic_summary": "..."}}
"""

        try:
            # 调用 LLM
            response = self.llm_generator.generate(prompt)

            # 解析 JSONL 输出
            segments = self._parse_llm_segments(response, dialogs)

            if segments:
                return segments

        except Exception as e:
            print(f"[WARNING] LLM segmentation failed: {e}, using simple fallback")

        # LLM 失败，回退到简单策略
        return self._segment_simple(dialogs)

    def _parse_llm_segments(
        self, llm_response: str, dialogs: list[dict[str, str]]
    ) -> list[list[dict[str, str]]]:
        """解析 LLM 返回的 JSONL 分段结果"""
        import json

        segments = []
        try:
            # 逐行解析 JSONL
            for line in llm_response.strip().split("\n"):
                if not line.strip() or not line.startswith("{"):
                    continue

                seg_info = json.loads(line)
                start_idx = seg_info["start_exchange"] - 1  # 转为0-based
                end_idx = seg_info["end_exchange"]  # end是exclusive

                # 提取对应的对话
                segment = dialogs[start_idx:end_idx]
                if segment:
                    segments.append(segment)

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"[WARNING] Failed to parse LLM segment output: {e}")
            return []

        return segments if segments else []

    def _segment_simple(self, dialogs: list[dict[str, str]]) -> list[list[dict[str, str]]]:
        """简单分段策略（回退方案）：按固定长度分段"""
        segments = []
        for i in range(0, len(dialogs), self.max_segment_length):
            segment = dialogs[i : i + self.max_segment_length]
            # 确保至少有 min_segment_length 轮对话
            if len(segment) >= self.min_segment_length or i + len(segment) == len(dialogs):
                segments.append(segment)

        return segments if segments else [dialogs]

    def _compress_with_llm(self, text: str) -> str:
        """使用 LLM 压缩去噪

        Args:
            text: 原始对话段落

        Returns:
            压缩后的文本
        """
        if not self.denoising_prompt or not hasattr(self, "llm_generator"):
            return text  # 无法压缩，返回原文

        try:
            # 构造完整 prompt（优化：直接输出，无解释）
            full_prompt = f"{self.denoising_prompt}\n\nDialogue:\n{text}\n\nCompressed (output ONLY the compressed text, no explanation):"

            # 调用 LLM
            compressed = self.llm_generator.generate(full_prompt)

            return compressed.strip() if compressed else text

        except Exception as e:
            print(f"[WARNING] LLM compression failed: {e}, using original text")
            return text
