"""键值对记忆服务 - Partitional 类

支持精确匹配、模糊匹配和语义匹配。

设计原则:
- Service : Collection = 1 : 1
- 使用 KVMemoryCollection 作为底层存储
- 支持 BM25 等多种检索方式

Layer: L4 (Middleware)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from sage.common.config.output_paths import get_appropriate_sage_dir
from sage.kernel.runtime.factory.service_factory import ServiceFactory
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager

from ..base_service import BaseMemoryService

if TYPE_CHECKING:
    import numpy as np


class KeyValueMemoryService(BaseMemoryService):
    """键值对记忆服务 - Partitional 类

    底层使用 MemoryManager + KVMemoryCollection 存储。
    支持 BM25 等多种检索方式。

    设计原则：
    - Service : Collection = 1 : 1
    - 使用 KVMemoryCollection
    - 支持文本检索
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
            index_type: 索引类型（如 "bm25s"）
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
        collection = None
        if self.manager.has_collection(collection_name):
            collection = self.manager.get_collection(collection_name)
            if collection is None:
                # Collection 元数据存在但磁盘数据丢失，需要清理并重建
                self.logger.warning(
                    f"Collection '{collection_name}' metadata exists but data missing, recreating"
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

    @classmethod
    def from_config(cls, service_name: str, config: Any) -> ServiceFactory:
        """从配置创建 ServiceFactory

        配置示例:
            services:
              partitional.key_value_memory:
                collection_name: kv_memory
                index_name: default_index
                index_type: bm25s
                default_topk: 5
        """
        collection_name = config.get(
            f"services.{service_name}.collection_name",
            f"kv_{service_name.replace('.', '_')}",
        )
        index_name = config.get(f"services.{service_name}.index_name", "default_index")
        index_type = config.get(f"services.{service_name}.index_type", "bm25s")
        default_topk = config.get(f"services.{service_name}.default_topk", 5)

        return ServiceFactory(
            service_name=service_name,
            service_class=cls,
            service_kwargs={
                "collection_name": collection_name,
                "index_name": index_name,
                "index_type": index_type,
                "default_topk": default_topk,
            },
        )

    def _get_default_data_dir(self) -> str:
        """获取默认数据目录"""
        sage_dir = get_appropriate_sage_dir()
        data_dir = sage_dir / "data" / "kv_memory"
        data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir)

    def insert(
        self,
        entry: str,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        *,
        insert_mode: Literal["active", "passive"] = "passive",
        insert_params: dict[str, Any] | None = None,
    ) -> str:
        """插入键值对"""
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
        metadata: dict[str, Any] | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """检索键值对"""
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

        if not results:
            return []

        # 转换为统一格式
        formatted_results = []
        for i, item in enumerate(results):
            if isinstance(item, dict):
                formatted_results.append(
                    {
                        "text": item.get("text", ""),
                        "metadata": item.get("metadata", {}),
                        "score": item.get("score", 1.0 / (1 + i)),
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

    def delete(self, item_id: str) -> bool:
        """删除记忆"""
        try:
            return self.collection.delete(item_id)
        except Exception:
            return False

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        # KVMemoryCollection 可能没有 list_indexes 方法
        total_count = 0
        if hasattr(self.collection, "text_storage"):
            total_count = len(self.collection.text_storage)

        return {
            "total_count": total_count,
            "collection_name": self.collection_name,
            "index_name": self.index_name,
            "index_type": self.index_type,
        }
