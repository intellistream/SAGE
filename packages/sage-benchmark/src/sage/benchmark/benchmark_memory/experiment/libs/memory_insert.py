"""记忆插入模块 - 负责将对话存储到记忆服务中

支持多种插入方法：
- default: 默认插入
- triple_insert: 三元组插入（图服务）
- chunk_insert: 分块插入
- summary_insert: 摘要插入
- priority_insert: 优先级插入
- multi_index_insert: 多索引插入

支持两种插入模式：
- passive: 被动插入，由服务内部决定如何存储（默认）
- active: 主动插入，根据 insert_params 指定存储方式
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sage.benchmark.benchmark_memory.experiment.utils.dialogue_parser import DialogueParser
from sage.common.core import MapFunction

if TYPE_CHECKING:
    pass


class MemoryInsert(MapFunction):
    """将对话插入记忆服务

    职责：
    1. 接收 PreInsert 输出的 memory_entries
    2. 根据 insert_method 执行具体插入逻辑
    3. 根据 insert_mode 决定调用方式
    4. 调用配置的记忆服务存储
    5. 透传数据给下游
    """

    def __init__(self, config=None):
        """初始化 MemoryInsert

        Args:
            config: RuntimeConfig 对象
        """
        super().__init__()
        self.config = config

        # 明确服务后端
        self.service_name = config.get("services.register_memory_service", "short_term_memory")
        print(f"[DEBUG] MemoryInsert.__init__: self.service_name = {self.service_name}")

        # 从配置读取提取模式
        self.adapter = (
            config.get("services.memory_insert_adapter", "to_dialogs") if config else "to_dialogs"
        )

        # 初始化对话解析器（to_dialogs 模式需要，其他模式可能也需要作为回退）
        self.dialogue_parser = DialogueParser()

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """执行记忆插入

        Args:
            data: 由 PreInsert 输出的数据

        Returns:
            原始数据 + 插入统计
        """
        inserted_ids = []
        failed_count = 0

        for entry_dict in data.get("memory_entries", []):
            try:
                entry_id = self._insert_single_entry(entry_dict)
                if entry_id:
                    inserted_ids.append(entry_id)
            except Exception as e:
                self.logger.warning(f"Insert failed: {e}")
                failed_count += 1

        data["insert_stats"] = {
            "inserted": len(inserted_ids),
            "failed": failed_count,
            "entry_ids": inserted_ids,
        }

        return data

    def _insert_single_entry(self, entry_dict: dict[str, Any]) -> str | None:
        """插入单条记忆条目（所有插入方法逻辑内联）

        Args:
            entry_dict: 记忆条目字典，由 PreInsert 生成

        Returns:
            str | None: 插入的条目 ID，失败返回 None
        """
        # 提取插入配置
        insert_method = entry_dict.get("insert_method", "default")
        insert_mode = entry_dict.get("insert_mode", "passive")
        insert_params = (entry_dict.get("insert_params") or {}).copy()

        # 提取文本内容
        # 根据不同的 transform_type，文本可能存储在不同字段：
        # - refactor: refactor 处理后的文本
        # - text: 原始文本
        # - summary: summarize 生成的摘要
        # - compressed_text: compress 压缩后的文本
        # - chunk_text: chunking 分块后的文本
        # - segment_text: topic_segment 分段后的文本
        if self.adapter == "to_dialogs":
            dialogs = entry_dict.get("dialogs", [])
            entry = self.dialogue_parser.format(dialogs) if dialogs else ""
        else:
            # 按优先级尝试获取文本内容
            entry = (
                entry_dict.get("refactor", "")
                or entry_dict.get("summary", "")
                or entry_dict.get("compressed_text", "")
                or entry_dict.get("chunk_text", "")
                or entry_dict.get("segment_text", "")
                or entry_dict.get("text", "")
            )
            # 如果没有转换后的文本，回退到 dialogs
            if not entry and "dialogs" in entry_dict:
                dialogs = entry_dict.get("dialogs", [])
                entry = self.dialogue_parser.format(dialogs) if dialogs else ""

        if not entry:
            return None

        # 提取向量和元数据
        vector = entry_dict.get("embedding")
        metadata = (entry_dict.get("metadata") or {}).copy()

        # ========== 根据 insert_method 内联处理逻辑 ==========

        if insert_method == "triple_insert":
            # 三元组插入（图服务）
            # 支持两种格式：
            # - "triples": [(s, r, o), ...] - 复数列表格式
            # - "triple": (s, r, o) - 单数格式（来自 PreInsert tri_embed）
            if "triples" in entry_dict:
                metadata["triples"] = entry_dict["triples"]
            elif "triple" in entry_dict:
                # 将单个三元组包装为列表
                metadata["triples"] = [entry_dict["triple"]]
            metadata.setdefault("node_type", "fact")

        elif insert_method == "chunk_insert":
            # 分块插入
            if "chunk_text" in entry_dict:
                entry = entry_dict["chunk_text"]
            if "chunk_index" in entry_dict:
                metadata["chunk_index"] = entry_dict["chunk_index"]
                metadata["total_chunks"] = entry_dict.get("total_chunks", 1)

        elif insert_method == "summary_insert":
            # 摘要插入
            metadata["is_summary"] = True
            if insert_mode == "passive":
                insert_mode = "active"
                insert_params.setdefault("target_tier", "ltm")

        elif insert_method == "priority_insert":
            # 优先级插入
            importance = entry_dict.get("importance_score")
            if importance is not None:
                insert_params["priority"] = importance
                if importance >= 8:
                    insert_params["target_tier"] = "ltm"
                elif importance >= 5:
                    insert_params["target_tier"] = "mtm"
                insert_mode = "active"

        elif insert_method == "multi_index_insert":
            # 多索引插入（混合服务）
            if "embeddings" in entry_dict:
                metadata["vectors"] = entry_dict["embeddings"]
            if "target_indexes" in entry_dict:
                insert_params["target_indexes"] = entry_dict["target_indexes"]
                insert_mode = "active"

        # 统一调用服务
        return self.call_service(
            self.service_name,
            entry=entry,
            vector=vector,
            metadata=metadata,
            insert_mode=insert_mode,
            insert_params=insert_params if insert_params else None,
            method="insert",
            timeout=10.0,
        )
