"""Key-Value Memory Service - 键值对记忆服务

支持精确匹配、模糊匹配和语义匹配。

设计原则:
- Service : Collection = 1 : 1
- 使用 KVMemoryCollection 作为底层存储
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager
from sage.platform.service import BaseService

if TYPE_CHECKING:
    import numpy as np


class KeyValueMemoryService(BaseService):
    """键值对记忆服务

    底层使用 MemoryManager + KVMemoryCollection 存储。
    支持 BM25 等多种检索方式。
    """

    def __init__(
        self,
        collection_name: str = "kv_memory",
        index_name: str = "default_index",
        index_type: str = "bm25s",
        default_topk: int = 5,
    ):
        """初始化键值对记忆服务

        Args:
            collection_name: NeuroMem collection 名称
            index_name: 索引名称
            index_type: 索引类型 (如 "bm25s")
            default_topk: 默认返回结果数量
        """
        super().__init__()

        self.collection_name = collection_name
        self.index_name = index_name
        self.index_type = index_type
        self.default_topk = default_topk

        # 初始化 MemoryManager
        self.manager = MemoryManager(self._get_default_data_dir())

        # 创建或获取 KVMemoryCollection
        # 注意：has_collection 可能返回 True，但 get_collection 返回 None（磁盘数据丢失）
        # 这种情况下需要删除旧记录并重新创建
        collection = None
        if self.manager.has_collection(collection_name):
            collection = self.manager.get_collection(collection_name)
            if collection is None:
                # Collection 元数据存在但磁盘数据丢失，需要清理并重建
                self.logger.warning(
                    f"Collection '{collection_name}' metadata exists but data is missing, "
                    "will recreate."
                )
                self.manager.delete_collection(collection_name)

        if collection is None:
            collection = self.manager.create_collection(
                {
                    "name": collection_name,
                    "backend_type": "KV",
                    "description": "Key-value memory collection",
                }
            )

        self.collection = collection

        if self.collection is None:
            raise RuntimeError(f"Failed to create KVMemoryCollection '{collection_name}'")

        # 确保有默认索引
        if index_name not in self.collection.indexes:
            self.collection.create_index(
                {
                    "name": index_name,
                    "index_type": index_type,
                    "description": "Default KV index",
                }
            )

        self.logger.info(
            f"KeyValueMemoryService initialized: collection={collection_name}, "
            f"index={index_name}, type={index_type}"
        )

    def get(self, entry_id: str) -> dict[str, Any] | None:
        """获取指定 ID 的记忆条目

        Args:
            entry_id: 条目 ID

        Returns:
            dict: 条目数据（包含 text, metadata 等），不存在返回 None
        """
        if not hasattr(self.collection, "text_storage"):
            return None

        text = self.collection.text_storage.get(entry_id)
        if text is None:
            return None

        metadata = None
        if hasattr(self.collection, "metadata_storage"):
            metadata = self.collection.metadata_storage.get(entry_id)

        return {
            "id": entry_id,
            "text": text,
            "metadata": metadata or {},
        }

    @classmethod
    def _get_default_data_dir(cls) -> str:
        """获取默认数据目录

        使用 SAGE 标准目录结构: .sage/data/kv_memory
        """
        from sage.common.config.output_paths import get_appropriate_sage_dir

        sage_dir = get_appropriate_sage_dir()
        data_dir = sage_dir / "data" / "kv_memory"
        data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir)

    def insert(
        self,
        entry: str,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict | None = None,
        *,
        insert_mode: Literal["active", "passive"] = "passive",
        insert_params: dict | None = None,
    ) -> str:
        """插入键值对

        支持两种插入模式：
        - passive: 由服务自行决定存储方式（默认）
        - active: 根据 insert_params 指定存储方式

        Args:
            entry: 文本内容（作为值存储）
            vector: embedding 向量（可选，KV 模式可能不使用）
            metadata: 元数据（可选）
            insert_mode: 插入模式 ("active" | "passive")
            insert_params: 主动插入参数
                - priority: 优先级

        Returns:
            str: 插入的条目 ID
        """
        if not isinstance(entry, str):
            raise TypeError("entry must be a string")

        # 处理插入模式
        if insert_mode == "active" and insert_params:
            if "priority" in insert_params:
                metadata = metadata.copy() if metadata else {}
                metadata["priority"] = insert_params["priority"]

        # 插入到 KVMemoryCollection
        entry_id = self.collection.insert(
            content=entry, index_names=self.index_name, metadata=metadata
        )

        self.logger.debug(f"Inserted entry to KV memory: {entry_id[:16]}...")
        return entry_id

    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict | None = None,
        top_k: int = 10,
        hints: dict | None = None,
        threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """检索值

        Args:
            query: 查询文本
            vector: 查询向量（KV 模式可能不使用）
            metadata: 查询参数:
                - with_metadata: 是否返回元数据
            top_k: 返回结果数量
            hints: 检索策略提示（可选，由 PreRetrieval route action 生成）
            threshold: 相似度阈值（可选，过滤低于阈值的结果）

        Returns:
            list[dict]: 检索结果 [{"text": ..., "metadata": ..., "score": ...}, ...]
        """
        _ = hints  # 保留用于未来扩展
        _ = threshold  # KV 检索暂不使用相似度阈值
        if query is None:
            return []

        metadata = metadata or {}
        top_k = top_k if top_k > 0 else self.default_topk
        with_metadata = metadata.get("with_metadata", True)

        # 使用 KVMemoryCollection 的检索功能
        results = self.collection.retrieve(
            query=query,
            top_k=top_k,
            with_metadata=with_metadata,
            index_name=self.index_name,
        )

        # 转换为统一格式
        if not results:
            return []

        formatted_results = []
        for i, item in enumerate(results):
            if isinstance(item, dict):
                formatted_results.append(
                    {
                        "text": item.get("text", ""),
                        "metadata": item.get("metadata", {}),
                        "score": 1.0 / (1 + i),  # 简单的排名分数
                    }
                )
            else:
                formatted_results.append(
                    {
                        "text": str(item),
                        "metadata": {},
                        "score": 1.0 / (1 + i),
                    }
                )

        return formatted_results

    def delete(self, entry_id: str) -> bool:
        """删除记忆条目

        Args:
            entry_id: 条目 ID（文本的哈希值）

        Returns:
            bool: 是否删除成功
        """
        try:
            # KVMemoryCollection 的 delete 需要原始文本
            # 这里假设 entry_id 是可以用来获取原始文本的
            text = self.collection.text_storage.get(entry_id)
            if text:
                self.collection.delete(text)
                self.logger.debug(f"Deleted entry {entry_id[:16]}... from KV memory")
                return True
            return False
        except Exception as e:
            self.logger.warning(f"Failed to delete entry {entry_id}: {e}")
            return False

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        all_ids = self.collection.get_all_ids()
        index_count = len(self.collection.indexes) if hasattr(self.collection, "indexes") else 0

        base_stats = {
            "memory_count": len(all_ids),
            "index_count": index_count,
            "collection_name": self.collection_name,
            "index_name": self.index_name,
            "index_type": self.index_type,
        }

        # 添加存储统计
        if hasattr(self.collection, "get_storage_stats"):
            base_stats["storage"] = self.collection.get_storage_stats()

        return base_stats

    def clear(self) -> bool:
        """清空所有记忆"""
        try:
            # 重新创建 collection
            self.manager.delete_collection(self.collection_name)
            self.collection = self.manager.create_collection(
                {
                    "name": self.collection_name,
                    "backend_type": "KV",
                    "description": "Key-value memory collection",
                }
            )

            if self.collection is not None:
                self.collection.create_index(
                    {
                        "name": self.index_name,
                        "index_type": self.index_type,
                        "description": "Default KV index",
                    }
                )

            self.logger.info("Cleared all KV memories")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear KV memory: {e}")
            return False
