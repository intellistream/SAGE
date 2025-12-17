"""PreInsert Operator - 记忆插入前预处理算子

Pipeline 位置: 第 1 层（插入前）
访问权限: 仅允许检索记忆服务（不允许插入/删除）

采用策略模式，通过 Action 注册表动态选择和执行预处理策略。
"""

from __future__ import annotations

import time
from typing import Any

from sage.benchmark.benchmark_memory.experiment.utils import (
    EmbeddingGenerator,
    LLMGenerator,
)
from sage.common.core import MapFunction

from .base import BasePreInsertAction, PreInsertInput, PreInsertOutput
from .registry import PreInsertActionRegistry


class PreInsert(MapFunction):
    """记忆插入前的预处理算子（重构版）"""

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.service_name = config.get("services.register_memory_service", "short_term_memory")
        self._embedding_generator: EmbeddingGenerator = EmbeddingGenerator.from_config(self.config)
        self._llm_generator: LLMGenerator = LLMGenerator.from_config(self.config)

        action_config = config.get("operators.pre_insert", {})
        self.action_name = action_config.get("action", "none")

        action_type = None
        if self.action_name in ["transform", "extract", "score"]:
            type_key = f"{self.action_name}_type"
            action_type = action_config.get(type_key)

        action_key = f"{self.action_name}.{action_type}" if action_type else self.action_name

        try:
            action_class = PreInsertActionRegistry.get(action_key)
            self.action: BasePreInsertAction = action_class(action_config)
        except ValueError as e:
            print(f"[WARNING] {e}, using NoneAction as fallback")
            from .none_action import NoneAction

            self.action = NoneAction(action_config)

        # 传递generators给action
        if hasattr(self.action, "set_llm_generator"):
            self.action.set_llm_generator(self._llm_generator)
        if hasattr(self.action, "set_embedding_generator"):
            self.action.set_embedding_generator(self._embedding_generator)

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        start_time = time.perf_counter()
        input_data = PreInsertInput(
            data=data,
            config=self.config.get("operators.pre_insert", {}),
            service_name=self.service_name,
        )
        output: PreInsertOutput = self.action.execute(input_data)
        self._generate_embeddings(output.memory_entries)
        data["memory_entries"] = output.memory_entries
        if output.metadata:
            data.setdefault("metadata", {}).update(output.metadata)

        # 计算批次总耗时
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        # 使用输入的 dialogs 数量（而非输出的 memory_entries）
        dialog_count = len(data.dialogs) if hasattr(data, "dialogs") else 1

        # 将批次耗时平均分配到每个对话，返回列表
        if dialog_count > 0:
            per_entry_ms = elapsed_ms / dialog_count
            data.setdefault("stage_timings", {})["pre_insert_ms"] = [per_entry_ms] * dialog_count
        else:
            data.setdefault("stage_timings", {})["pre_insert_ms"] = []

        return data

    def _generate_embeddings(self, entries: list[dict[str, Any]]) -> None:
        if not self._embedding_generator or not self._embedding_generator.is_available():
            return
        for entry in entries:
            if "embedding" in entry and entry["embedding"] is not None:
                continue
            text_for_embed = (
                entry.get("summary", "")
                or entry.get("compressed_text", "")
                or entry.get("chunk_text", "")
                or entry.get("segment_text", "")
                or entry.get("fact", "")
                or entry.get("reconstructed_text", "")
                or entry.get("text", "")
            )
            if text_for_embed:
                try:
                    embedding = self._embedding_generator.embed(text_for_embed)
                    if embedding:
                        entry["embedding"] = embedding
                except Exception as e:
                    print(f"[WARNING] Embedding generation failed: {e}")
