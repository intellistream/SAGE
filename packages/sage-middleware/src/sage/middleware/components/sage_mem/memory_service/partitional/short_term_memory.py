"""短期记忆服务 - Partitional 类

基于滑动窗口的短期记忆存储，用于保存最近的对话历史。

设计原则:
- Service : Collection = 1 : 1
- 使用 VDBMemoryCollection 作为底层存储
- FIFO 淘汰最旧的记忆

Layer: L4 (Middleware)
"""

from __future__ import annotations

import time
from collections import deque
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

from sage.common.config.output_paths import get_appropriate_sage_dir
from sage.kernel.runtime.factory.service_factory import ServiceFactory
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager

from ..base_service import BaseMemoryService

if TYPE_CHECKING:
    pass


class ShortTermMemoryService(BaseMemoryService):
    """短期记忆服务 - Partitional 类

    基于滑动窗口的记忆服务，自动淘汰最旧的记忆。
    适用于对话历史、最近事件等场景。

    设计原则：
    - Service : Collection = 1 : 1
    - 使用 VDBMemoryCollection
    - FIFO 淘汰策略
    """

    def __init__(
        self,
        max_dialog: int,
        collection_name: str = "stm_collection",
        embedding_dim: int = 1024,
    ):
        """初始化短期记忆服务

        Args:
            max_dialog: 最大对话数量（队列长度）
            collection_name: NeuroMem collection 名称
            embedding_dim: embedding 向量维度（默认 1024，适配 BAAI/bge-m3）
        """
        super().__init__()
        self.max_dialog = max_dialog
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim

        # 初始化 MemoryManager
        self.manager = MemoryManager(self._get_default_data_dir())

        # 创建或获取 VDBMemoryCollection
        if self.manager.has_collection(collection_name):
            self.collection = self.manager.get_collection(collection_name)
            # Handle corrupted state: metadata exists but load failed
            if self.collection is None:
                self.manager.delete_collection(collection_name)
                self.collection = self.manager.create_collection(
                    {
                        "name": collection_name,
                        "backend_type": "VDB",
                        "description": "Short-term memory collection",
                    }
                )
        else:
            self.collection = self.manager.create_collection(
                {
                    "name": collection_name,
                    "backend_type": "VDB",
                    "description": "Short-term memory collection",
                }
            )

        if self.collection is None:
            raise RuntimeError(f"Failed to create VDBMemoryCollection '{collection_name}'")

        # 确保有 global_index
        if hasattr(self.collection, "index_info"):
            if "global_index" not in self.collection.index_info:
                self.collection.create_index(
                    {
                        "name": "global_index",
                        "dim": self.embedding_dim,
                        "backend_type": "FAISS",
                        "description": "Global index for STM",
                    }
                )

        # 维护时间顺序的队列（存储 entry_id 和 timestamp）
        self._order_queue: deque[dict[str, Any]] = deque(maxlen=max_dialog)
        self._id_set: set[str] = set()

        # 尝试从持久化存储恢复队列
        self._restore_queue()

        self.logger.debug(f"ShortTermMemoryService initialized with max_dialog={max_dialog}")

    @classmethod
    def from_config(cls, service_name: str, config: Any) -> ServiceFactory:
        """从配置创建 ServiceFactory

        配置示例:
            services:
              partitional.short_term_memory:
                max_dialog: 10
                embedding_dim: 1024
                collection_name: stm_collection
        """
        max_dialog = config.get(f"services.{service_name}.max_dialog")
        if max_dialog is None:
            raise ValueError(f"Missing config: services.{service_name}.max_dialog")

        embedding_dim = config.get(f"services.{service_name}.embedding_dim", 1024)
        collection_name = config.get(
            f"services.{service_name}.collection_name",
            f"stm_{service_name.replace('.', '_')}",
        )

        return ServiceFactory(
            service_name=service_name,
            service_class=cls,
            service_kwargs={
                "max_dialog": max_dialog,
                "embedding_dim": embedding_dim,
                "collection_name": collection_name,
            },
        )

    def _get_default_data_dir(self) -> str:
        """获取默认数据目录"""
        sage_dir = get_appropriate_sage_dir()
        data_dir = sage_dir / "data" / "stm_memory"
        data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir)

    def _restore_queue(self) -> None:
        """从持久化存储恢复队列"""
        # TODO: 从 collection 恢复队列（按 timestamp 排序）
        pass

    def insert(
        self,
        entry: str,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        *,
        insert_mode: Literal["active", "passive"] = "passive",
        insert_params: dict[str, Any] | None = None,
    ) -> str:
        """插入对话记录（FIFO 淘汰）"""
        if not isinstance(entry, str):
            raise TypeError("entry must be a string")

        # 处理插入模式
        force_insert = False
        if insert_mode == "active" and insert_params:
            force_insert = insert_params.get("force", False)
            if "priority" in insert_params:
                metadata = metadata.copy() if metadata else {}
                metadata["priority"] = insert_params["priority"]

        timestamp = time.time()

        # 如果队列已满，先删除最旧的条目
        if not force_insert:
            while len(self._order_queue) >= self.max_dialog:
                oldest = self._order_queue.popleft()
                old_id = oldest.get("stable_id")
                if old_id:
                    self._id_set.discard(old_id)
                    try:
                        self.collection.delete(old_id)
                    except Exception:
                        pass

        # 准备元数据
        full_metadata = metadata.copy() if metadata else {}
        full_metadata["timestamp"] = timestamp

        # 插入到 NeuroMem collection
        if vector is not None and hasattr(self.collection, "index_info"):
            vec = np.array(vector, dtype=np.float32)
            stable_id = self.collection.insert(
                content=entry,
                index_names="global_index",
                vector=vec,
                metadata=full_metadata,
            )
        else:
            stable_id = self.collection.insert(
                index_names=None, content=entry, metadata=full_metadata
            )

        # 记录到时间队列
        self._order_queue.append(
            {
                "stable_id": stable_id,
                "timestamp": timestamp,
                "text": entry,
            }
        )
        self._id_set.add(stable_id)

        self.logger.debug(
            f"Inserted dialog. Current queue size: {len(self._order_queue)}/{self.max_dialog}"
        )

        return stable_id

    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """检索短期记忆"""
        # 如果有向量，进行语义检索
        if vector is not None and hasattr(self.collection, "index_info"):
            query_vec = np.array(vector, dtype=np.float32)
            results = self.collection.retrieve(
                query=query_vec,
                index_name="global_index",
                top_k=min(top_k, len(self._order_queue)),
                with_metadata=True,
            )

            # 应用相似度阈值过滤（如果 metadata 中指定）
            threshold = metadata.get("min_score") if metadata else None
            if results and threshold is not None:
                results = [
                    r
                    for r in results
                    if r.get("score", 0) >= threshold or r.get("similarity", 0) >= threshold
                ]
            return results if results else []

        # 否则返回按时间顺序的结果
        results = []
        for item in list(self._order_queue)[-top_k:]:
            results.append(
                {
                    "text": item.get("text", ""),
                    "metadata": {"timestamp": item.get("timestamp")},
                    "score": 1.0,
                }
            )
        return results

    def delete(self, item_id: str) -> bool:
        """删除记忆"""
        if item_id not in self._id_set:
            return False

        # 从队列中删除
        self._order_queue = deque(
            [item for item in self._order_queue if item.get("stable_id") != item_id],
            maxlen=self.max_dialog,
        )
        self._id_set.discard(item_id)

        # 从 collection 删除
        try:
            return self.collection.delete(item_id)
        except Exception:
            return False

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        indexes = self.collection.list_indexes() if hasattr(self.collection, "list_indexes") else []
        return {
            "total_count": len(self._order_queue),
            "max_dialog": self.max_dialog,
            "collection_name": self.collection_name,
            "index_count": indexes[0]["item_count"] if indexes else 0,
        }
