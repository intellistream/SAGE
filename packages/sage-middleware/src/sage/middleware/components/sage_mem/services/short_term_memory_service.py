"""Short-Term Memory Service - 短期记忆服务

基于滑动窗口的短期记忆存储，用于保存最近的对话历史。

设计原则:
- Service : Collection = 1 : 1
- 使用 VDBMemoryCollection 作为底层存储
- FIFO 淘汰最旧的记忆
"""

from __future__ import annotations

import time
from collections import deque
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

from sage.common.config.output_paths import get_appropriate_sage_dir
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager
from sage.platform.service import BaseService

if TYPE_CHECKING:
    pass


class ShortTermMemoryService(BaseService):
    """短期记忆服务

    基于滑动窗口的记忆服务，自动淘汰最旧的记忆。
    适用于对话历史、最近事件等场景。

    底层使用 MemoryManager + VDBMemoryCollection 存储。
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

        self.logger.info(f"ShortTermMemoryService initialized with max_dialog={max_dialog}")

    @classmethod
    def _get_default_data_dir(cls) -> str:
        """获取默认数据目录

        使用 SAGE 标准目录结构: .sage/data/stm_memory
        """
        sage_dir = get_appropriate_sage_dir()
        data_dir = sage_dir / "data" / "stm_memory"
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
        """插入一条对话记录到短期记忆中

        支持两种插入模式：
        - passive: 由服务自行决定存储方式（默认，FIFO 行为）
        - active: 根据 insert_params 指定存储方式

        Args:
            entry: 对话文本字符串
            vector: embedding 向量（可选）
            metadata: 元数据（可选）
            insert_mode: 插入模式 ("active" | "passive")
            insert_params: 主动插入参数
                - priority: 优先级（可用于跳过 FIFO 限制）
                - force: 是否强制插入（跳过容量检查）

        Returns:
            str: 插入的条目 ID
        """
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

        # 如果队列已满，先删除最旧的条目（force_insert 跳过容量检查）
        if not force_insert:
            while len(self._order_queue) >= self.max_dialog:
                oldest = self._order_queue.popleft()
                old_id = oldest.get("stable_id")  # 使用 stable_id 而不是 entry_id
                if old_id:
                    self._id_set.discard(old_id)
                    # 从底层 collection 删除
                    try:
                        self.collection.delete(old_id)
                    except Exception:
                        pass  # 忽略删除错误

        # 准备元数据
        full_metadata = metadata.copy() if metadata else {}
        full_metadata["timestamp"] = timestamp

        # 插入到 NeuroMem collection，使用返回的 stable_id
        if vector is not None and hasattr(self.collection, "index_info"):
            vec = np.array(vector, dtype=np.float32)
            stable_id = self.collection.insert(
                content=entry,
                index_names="global_index",
                vector=vec,
                metadata=full_metadata,
            )
        else:
            # 没有向量时，只存储到 BaseMemoryCollection（index_names=None）
            stable_id = self.collection.insert(
                index_names=None, content=entry, metadata=full_metadata
            )

        # 记录到时间队列，使用 collection 返回的 stable_id
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
        metadata: dict | None = None,
        top_k: int = 10,
        hints: dict | None = None,
        threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """检索短期记忆中的对话

        Args:
            query: 查询文本（可选，用于语义检索）
            vector: 查询向量（可选，用于向量检索）
            metadata: 查询条件（可选）
            top_k: 返回结果数量
            hints: 检索策略提示（可选，由 PreRetrieval route action 生成）
                   当前版本暂未使用，保留用于未来扩展
            threshold: 相似度阈值（可选，过滤低于阈值的结果）

        Returns:
            list[dict]: 检索结果列表 [{"text": ..., "metadata": ..., "score": ...}, ...]
        """
        # 后续可根据 hints 调整检索策略
        _ = hints  # 暂时忽略，避免 unused variable 警告
        # 如果有向量，进行语义检索
        if vector is not None and hasattr(self.collection, "index_info"):
            query_vec = np.array(vector, dtype=np.float32)
            results = self.collection.retrieve(
                query=query_vec,
                index_name="global_index",
                top_k=min(top_k, len(self._order_queue)),
                with_metadata=True,
            )
            # 应用相似度阈值过滤
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
                    "metadata": {
                        "timestamp": item.get("timestamp"),
                        "stable_id": item.get("stable_id"),
                    },
                    "score": None,
                }
            )
        return results

    def delete(self, item_id: str) -> bool:
        """删除指定的记忆条目

        Args:
            item_id: 记忆条目 ID (stable_id)

        Returns:
            bool: 是否删除成功
        """
        if item_id not in self._id_set:
            return False

        # 从队列中删除
        self._order_queue = deque(
            [item for item in self._order_queue if item.get("stable_id") != item_id],
            maxlen=self.max_dialog,
        )
        self._id_set.discard(item_id)

        # 从底层 collection 删除
        try:
            self.collection.delete(item_id)
        except Exception:
            pass

        self.logger.debug(f"Deleted entry {item_id} from STM")
        return True

    def get_stats(self) -> dict[str, Any]:
        """获取服务统计信息"""
        return {
            "memory_count": len(self._order_queue),
            "max_capacity": self.max_dialog,
            "utilization": len(self._order_queue) / self.max_dialog if self.max_dialog > 0 else 0,
            "collection_name": self.collection_name,
        }

    def clear(self) -> bool:
        """清空所有短期记忆"""
        # 清空队列
        self._order_queue.clear()
        self._id_set.clear()

        # 重新创建 collection
        self.manager.delete_collection(self.collection_name)
        self.collection = self.manager.create_collection(
            {
                "name": self.collection_name,
                "backend_type": "VDB",
                "description": "Short-term memory collection",
            }
        )

        if self.collection is not None and hasattr(self.collection, "create_index"):
            self.collection.create_index(
                {
                    "name": "global_index",
                    "dim": self.embedding_dim,
                    "backend_type": "FAISS",
                    "description": "Global index for STM",
                }
            )

        self.logger.info("Cleared all short-term memories")
        return True
