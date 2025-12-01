"""Vector Hash Memory Service - 向量哈希桶记忆服务

基于 FAISS LSH 的向量哈希桶服务，支持高效的近似最近邻搜索。
使用 VDBMemoryCollection 作为底层存储。
"""

from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING, Any, Literal

from sage.middleware.components.sage_mem.neuromem.memory_collection.vdb_collection import (
    VDBMemoryCollection,
)
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager
from sage.platform.service import BaseService

if TYPE_CHECKING:
    import numpy as np


class VectorHashMemoryService(BaseService):
    """向量哈希桶记忆服务

    基于 FAISS LSH 实现的向量哈希桶服务，支持高效的近似最近邻搜索。
    使用汉明距离作为相似度度量。
    底层使用 MemoryManager + VDBMemoryCollection 存储。
    """

    def __init__(
        self,
        dim: int,
        nbits: int,
        collection_name: str = "vector_hash_memory",
    ):
        """初始化向量哈希桶服务

        Args:
            dim: 向量维度
            nbits: LSH 哈希位数
            collection_name: NeuroMem collection 名称
        """
        super().__init__()

        self.dim = dim
        self.nbits = nbits
        self.collection_name = collection_name

        # 初始化 MemoryManager
        self.manager = MemoryManager(self._get_default_data_dir())

        # 创建 VDB collection
        if self.manager.has_collection(collection_name):
            collection = self.manager.get_collection(collection_name)
            if not isinstance(collection, VDBMemoryCollection):
                raise TypeError(f"Collection '{collection_name}' is not a VDBMemoryCollection")
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
        if isinstance(self.collection, VDBMemoryCollection):
            if "lsh_index" not in self.collection.index_info:
                result = self.collection.create_index(
                    {
                        "name": "lsh_index",
                        "dim": dim,
                        "backend_type": "FAISS",
                        "description": "LSH index for vector hashing",
                        "index_parameter": {
                            "index_type": "IndexLSH",
                            "LSH_NBITS": nbits,
                        },
                    }
                )
                if not result:
                    raise RuntimeError("Failed to create LSH index")

        # entry_id -> text 映射
        self._id_to_text: dict[str, str] = {}

        self.logger.info(f"VectorHashMemoryService initialized: dim={dim}, nbits={nbits}")

    @classmethod
    def _get_default_data_dir(cls) -> str:
        """获取默认数据目录"""
        cur_dir = os.getcwd()
        data_dir = os.path.join(cur_dir, "data", "vector_hash_memory")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir

    def insert(
        self,
        entry: str,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict | None = None,
        *,
        insert_mode: Literal["active", "passive"] = "passive",
        insert_params: dict | None = None,
    ) -> str:
        """插入文本和对应的向量到 LSH 索引

        支持两种插入模式：
        - passive: 由服务自行决定存储方式（默认）
        - active: 根据 insert_params 指定存储方式

        Args:
            entry: 原始文本数据
            vector: 预先生成的向量
            metadata: 元数据（可选）
            insert_mode: 插入模式 ("active" | "passive")
            insert_params: 主动插入参数
                - priority: 优先级

        Returns:
            str: 插入的条目 ID
        """
        if vector is None:
            raise ValueError("Vector is required for VectorHashMemoryService")

        import numpy as np

        # 处理插入模式
        if insert_mode == "active" and insert_params:
            if "priority" in insert_params:
                metadata = metadata.copy() if metadata else {}
                metadata["priority"] = insert_params["priority"]

        # 生成唯一 ID
        entry_id = metadata.get("id", str(uuid.uuid4())) if metadata else str(uuid.uuid4())

        # 准备元数据
        insert_metadata = metadata.copy() if metadata else {}
        insert_metadata["entry_id"] = entry_id

        # 插入数据
        vec = np.array(vector, dtype=np.float32)
        self.collection.insert(
            index_name="lsh_index",
            text=entry,
            vector=vec,
            metadata=insert_metadata,
        )

        self._id_to_text[entry_id] = entry
        self.logger.debug(f"Inserted entry to LSH: {entry_id[:16]}...")
        return entry_id

    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """通过向量检索相似的文档

        Args:
            query: 查询文本（可选）
            vector: 查询向量
            metadata: 查询参数
            top_k: 返回结果数量

        Returns:
            list[dict]: 检索结果
        """
        if vector is None:
            return []

        import numpy as np

        query_vec = np.array(vector, dtype=np.float32)
        results = self.collection.retrieve(
            query_text=query,
            query_vector=query_vec,
            index_name="lsh_index",
            topk=top_k,
            with_metadata=True,
        )

        return results if results else []

    def delete(self, entry_id: str) -> bool:
        """删除指定条目

        Args:
            entry_id: 条目 ID

        Returns:
            bool: 是否删除成功
        """
        if entry_id not in self._id_to_text:
            return False

        try:
            text = self._id_to_text.pop(entry_id)
            self.collection.delete(text)
            self.logger.debug(f"Deleted entry {entry_id[:16]}...")
            return True
        except Exception as e:
            self.logger.warning(f"Failed to delete entry {entry_id}: {e}")
            return False

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "memory_count": len(self._id_to_text),
            "dim": self.dim,
            "nbits": self.nbits,
            "collection_name": self.collection_name,
        }
