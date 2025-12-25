"""向量哈希记忆服务 - Partitional 类

基于 LSH (Locality-Sensitive Hashing) 的向量哈希索引。

设计原则:
- Service : Collection = 1 : 1
- 使用 VDBMemoryCollection + IndexLSH
- 快速近似检索

Layer: L4 (Middleware)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from sage.kernel.runtime.factory.service_factory import ServiceFactory
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager

from ..base_service import BaseMemoryService

if TYPE_CHECKING:
    import numpy as np


class VectorHashMemoryService(BaseMemoryService):
    """向量哈希记忆服务 - Partitional 类

    使用 LSH (Locality-Sensitive Hashing) 索引，提供快速近似检索。
    适用于大规模向量检索场景。

    设计原则：
    - Service : Collection = 1 : 1
    - 使用 VDBMemoryCollection + IndexLSH
    - 快速但可能不精确
    """

    def __init__(
        self,
        dim: int,
        nbits: int = 128,
        rotate_data: bool = True,
        collection_name: str = "vector_hash_memory",
        index_name: str = "lsh_index",
    ):
        """初始化向量哈希记忆服务

        Args:
            dim: 向量维度
            nbits: LSH 哈希位数（越大越精确，但越慢）
            rotate_data: 是否旋转数据（提高性能）
            collection_name: NeuroMem collection 名称
            index_name: 索引名称
        """
        super().__init__()

        self.dim = dim
        self.nbits = nbits
        self.rotate_data = rotate_data
        self.collection_name = collection_name
        self.index_name = index_name

        # 初始化 MemoryManager
        self.manager = MemoryManager()

        # 创建或加载 VDB collection
        if self.manager.has_collection(collection_name):
            collection = self.manager.get_collection(collection_name)
            if collection is None:
                raise RuntimeError(f"Failed to load collection '{collection_name}'")
            self.collection = collection
        else:
            self.collection = self.manager.create_collection(
                {
                    "name": collection_name,
                    "backend_type": "VDB",
                    "description": "Vector hash memory with LSH index",
                }
            )

        if self.collection is None:
            raise RuntimeError("Failed to create VectorHashMemory collection")

        # 创建 LSH 索引
        self._create_lsh_index()

        # entry_id -> text 映射
        self._id_to_text: dict[str, str] = {}

        self.logger.info(
            f"VectorHashMemoryService initialized: "
            f"dim={dim}, nbits={nbits}, rotate_data={rotate_data}"
        )

    @classmethod
    def from_config(cls, service_name: str, config: Any) -> ServiceFactory:
        """从配置创建 ServiceFactory

        配置示例:
            services:
              partitional.vector_hash_memory:
                dim: 768
                nbits: 128
                rotate_data: true
                collection_name: vector_hash_memory
        """
        dim = config.get(f"services.{service_name}.dim")
        if dim is None:
            raise ValueError(f"Missing config: services.{service_name}.dim")

        nbits = config.get(f"services.{service_name}.nbits", 128)
        rotate_data = config.get(f"services.{service_name}.rotate_data", True)
        collection_name = config.get(
            f"services.{service_name}.collection_name",
            f"vhash_{service_name.replace('.', '_')}",
        )
        index_name = config.get(f"services.{service_name}.index_name", "lsh_index")

        return ServiceFactory(
            service_name=service_name,
            service_class=cls,
            service_kwargs={
                "dim": dim,
                "nbits": nbits,
                "rotate_data": rotate_data,
                "collection_name": collection_name,
                "index_name": index_name,
            },
        )

    def _create_lsh_index(self) -> None:
        """创建 LSH 索引"""
        if not hasattr(self.collection, "index_info"):
            return

        if self.index_name in self.collection.index_info:
            self.logger.info(f"Index '{self.index_name}' already exists, skipping creation")
            return

        # 构建 LSH 索引配置
        index_parameter = {
            "index_type": "IndexLSH",
            "LSH_NBITS": self.nbits,
            "LSH_ROTATE_DATA": self.rotate_data,
            "LSH_TRAIN_THRESHOLDS": False,
        }

        result = self.collection.create_index(
            {
                "name": self.index_name,
                "dim": self.dim,
                "backend_type": "FAISS",
                "description": "LSH index for vector hash memory",
                "index_parameter": index_parameter,
            }
        )

        if not result:
            raise RuntimeError("Failed to create LSH index")

    def insert(
        self,
        entry: str,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        *,
        insert_mode: Literal["active", "passive"] = "passive",
        insert_params: dict[str, Any] | None = None,
    ) -> str:
        """插入文本和向量"""
        if not isinstance(entry, str):
            raise TypeError(f"entry must be str, got {type(entry).__name__}")

        if vector is None:
            raise ValueError("Vector is required for VectorHashMemoryService")

        import numpy as np

        # 处理插入模式
        if insert_mode == "active" and insert_params:
            if "priority" in insert_params:
                metadata = metadata.copy() if metadata else {}
                metadata["priority"] = insert_params["priority"]

        # 转换 vector
        vec = np.array(vector, dtype=np.float32)

        # 插入到 collection
        stable_id = self.collection.insert(
            content=entry,
            index_names=self.index_name,
            vector=vec,
            metadata=metadata,
        )

        self._id_to_text[stable_id] = entry
        self.logger.debug(f"Inserted vector to LSH: {stable_id[:16]}...")

        return stable_id

    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """检索向量（LSH 近似检索）"""
        if vector is None:
            return []

        import numpy as np

        query_vec = np.array(vector, dtype=np.float32)

        # 从 collection 检索（LSH 近似）
        results = self.collection.retrieve(
            query=query_vec,
            index_name=self.index_name,
            top_k=top_k,
            with_metadata=True,
        )

        if not results:
            return []

        # 转换为统一格式
        formatted_results = []
        for r in results:
            formatted_results.append(
                {
                    "text": r.get("text", ""),
                    "metadata": r.get("metadata", {}),
                    "score": r.get("score", 0.0),
                }
            )

        return formatted_results

    def delete(self, item_id: str) -> bool:
        """删除记忆"""
        try:
            success = self.collection.delete(item_id)
            if success and item_id in self._id_to_text:
                del self._id_to_text[item_id]
            return success
        except Exception:
            return False

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        indexes = self.collection.list_indexes() if hasattr(self.collection, "list_indexes") else []
        return {
            "total_count": indexes[0]["item_count"] if indexes else 0,
            "dim": self.dim,
            "index_type": "IndexLSH",
            "nbits": self.nbits,
            "rotate_data": self.rotate_data,
            "collection_name": self.collection_name,
            "index_name": self.index_name,
        }
