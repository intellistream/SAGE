"""Vector Memory Service - 统一向量记忆服务

支持多种 FAISS 索引后端的向量记忆服务，提供灵活的索引选择和配置。

设计原则:
- 统一的向量记忆接口
- 可配置的索引后端（LSH/HNSW/IVF/Flat等）
- Service : Collection = 1 : 1
- 底层使用 MemoryManager + VDBMemoryCollection 存储

支持的索引类型:
- IndexLSH: 局部敏感哈希（TiM论文使用，快速近似检索）
- IndexHNSWFlat: 分层可导航小世界图（高性能，高召回率）
- IndexFlatL2: L2距离暴力搜索（基准，精确但慢）
- IndexFlatIP: 内积暴力搜索（适用于归一化向量）
- IndexIVFFlat: 倒排文件索引（平衡速度与精度）
- IndexIVFPQ: IVF + 乘积量化（压缩存储）

使用示例:
    # TiM (LSH哈希桶)
    service = VectorMemoryService(
        dim=1024,
        index_type="IndexLSH",
        index_config={"nbits": 128}
    )

    # HNSW (高性能)
    service = VectorMemoryService(
        dim=1024,
        index_type="IndexHNSWFlat",
        index_config={"M": 32, "efConstruction": 200}
    )

    # Flat (精确KNN)
    service = VectorMemoryService(
        dim=1024,
        index_type="IndexFlatL2"
    )
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Literal

from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager
from sage.platform.service import BaseService

if TYPE_CHECKING:
    import numpy as np


class VectorMemoryService(BaseService):
    """统一向量记忆服务

    支持多种 FAISS 索引后端，通过配置选择最适合的索引类型。
    底层使用 MemoryManager + VDBMemoryCollection 存储。

    Attributes:
        dim: 向量维度
        index_type: 索引类型 (默认 "IndexFlatL2")
        index_config: 索引特定配置参数
        collection_name: NeuroMem collection 名称
        index_name: 索引名称（用于多索引场景）
    """

    # 索引类型默认配置
    DEFAULT_INDEX_CONFIGS = {
        "IndexLSH": {"nbits": 128, "rotate_data": True, "train_thresholds": False},
        "IndexHNSWFlat": {"M": 32, "efConstruction": 200, "efSearch": 64},
        "IndexFlatL2": {},
        "IndexFlatIP": {},
        "IndexIVFFlat": {"nlist": 100, "nprobe": 10, "metric": "L2"},
        "IndexIVFPQ": {"nlist": 100, "nprobe": 10, "M": 8, "nbits": 8, "metric": "L2"},
    }

    def __init__(
        self,
        dim: int,
        index_type: str = "IndexFlatL2",
        index_config: dict[str, Any] | None = None,
        collection_name: str = "vector_memory",
        index_name: str = "main_index",
    ):
        """初始化向量记忆服务

        Args:
            dim: 向量维度
            index_type: 索引类型，支持：
                - "IndexLSH": LSH哈希（TiM）
                - "IndexHNSWFlat": HNSW（高性能）
                - "IndexFlatL2": L2暴力搜索（精确）
                - "IndexFlatIP": 内积暴力搜索
                - "IndexIVFFlat": IVF倒排索引
                - "IndexIVFPQ": IVF+PQ（压缩）
            index_config: 索引配置参数（覆盖默认值）
                - IndexLSH: {"nbits": 128, "rotate_data": True}
                - IndexHNSWFlat: {"M": 32, "efConstruction": 200, "efSearch": 64}
                - IndexIVFFlat: {"nlist": 100, "nprobe": 10}
            collection_name: NeuroMem collection 名称
            index_name: 索引名称

        Raises:
            ValueError: 如果 index_type 不支持
        """
        super().__init__()

        # 验证 index_type
        if index_type not in self.DEFAULT_INDEX_CONFIGS:
            supported = ", ".join(self.DEFAULT_INDEX_CONFIGS.keys())
            raise ValueError(f"Unsupported index_type: {index_type}. Supported types: {supported}")

        self.dim = dim
        self.index_type = index_type
        self.collection_name = collection_name
        self.index_name = index_name

        # 合并默认配置和用户配置
        default_config = self.DEFAULT_INDEX_CONFIGS[index_type].copy()
        if index_config:
            default_config.update(index_config)
        self.index_config = default_config

        # 初始化 MemoryManager（不指定持久化目录）
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
                    "description": f"Vector memory with {index_type} index",
                }
            )

        if self.collection is None:
            raise RuntimeError("Failed to create VectorMemory collection")

        # 创建索引
        self._create_index()

        # entry_id -> text 映射
        self._id_to_text: dict[str, str] = {}

        self.logger.info(
            f"VectorMemoryService initialized: "
            f"dim={dim}, index_type={index_type}, config={self.index_config}"
        )

    def _create_index(self) -> None:
        """创建 FAISS 索引"""
        if not hasattr(self.collection, "index_info"):
            return

        if self.index_name in self.collection.index_info:
            self.logger.info(f"Index '{self.index_name}' already exists, skipping creation")
            return

        # 构建索引配置
        index_parameter = {"index_type": self.index_type}

        # 添加索引特定参数
        if self.index_type == "IndexLSH":
            index_parameter["LSH_NBITS"] = self.index_config.get("nbits", 128)
            index_parameter["LSH_ROTATE_DATA"] = self.index_config.get("rotate_data", True)
            index_parameter["LSH_TRAIN_THRESHOLDS"] = self.index_config.get(
                "train_thresholds", False
            )
        elif self.index_type == "IndexHNSWFlat":
            index_parameter["HNSW_M"] = self.index_config.get("M", 32)
            index_parameter["HNSW_EF_CONSTRUCTION"] = self.index_config.get("efConstruction", 200)
            index_parameter["HNSW_EF_SEARCH"] = self.index_config.get("efSearch", 64)
        elif self.index_type in ("IndexIVFFlat", "IndexIVFPQ"):
            index_parameter["IVF_NLIST"] = self.index_config.get("nlist", 100)
            index_parameter["IVF_NPROBE"] = self.index_config.get("nprobe", 10)
            index_parameter["IVF_METRIC"] = self.index_config.get("metric", "L2")
            if self.index_type == "IndexIVFPQ":
                index_parameter["PQ_M"] = self.index_config.get("M", 8)
                index_parameter["PQ_NBITS"] = self.index_config.get("nbits", 8)

        result = self.collection.create_index(
            {
                "name": self.index_name,
                "dim": self.dim,
                "backend_type": "FAISS",
                "description": f"{self.index_type} index for vector memory",
                "index_parameter": index_parameter,
            }
        )

        if not result:
            raise RuntimeError(f"Failed to create {self.index_type} index")

    def insert(
        self,
        entry: str,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict | None = None,
        *,
        insert_mode: Literal["active", "passive"] = "passive",
        insert_params: dict | None = None,
    ) -> str:
        """插入文本和对应的向量到索引

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

        Raises:
            TypeError: 如果 entry 不是字符串
            ValueError: 如果 vector 为空
        """
        # 类型检查
        if not isinstance(entry, str):
            raise TypeError(
                f"VectorMemoryService.insert() requires 'entry' to be str, "
                f"got {type(entry).__name__}: {entry}"
            )

        if vector is None:
            raise ValueError("Vector is required for VectorMemoryService")

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
            content=entry,
            index_names=self.index_name,
            vector=vec,
            metadata=insert_metadata,
        )

        self._id_to_text[entry_id] = entry
        self.logger.debug(f"Inserted entry to {self.index_type}: {entry_id[:16]}...")
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
        """通过向量检索相似的文档

        Args:
            query: 查询文本（可选）
            vector: 查询向量
            metadata: 查询参数
            top_k: 返回结果数量
            hints: 检索策略提示（可选，由 PreRetrieval route action 生成）
            threshold: 相似度阈值（可选，过滤低于阈值的结果）

        Returns:
            list[dict]: 检索结果，包含完整的记忆信息
        """
        _ = hints  # 保留用于未来扩展
        if vector is None:
            return []

        import numpy as np

        query_vec = np.array(vector, dtype=np.float32)
        results = self.collection.retrieve(
            query=query_vec,
            index_name=self.index_name,
            top_k=top_k,
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
        """获取统计信息

        Returns:
            dict: 包含以下字段：
                - memory_count: 记忆条目数量
                - dim: 向量维度
                - index_type: 索引类型
                - index_config: 索引配置
                - collection_name: Collection 名称
                - storage: 存储统计（如果支持）
        """
        base_stats = {
            "memory_count": len(self._id_to_text),
            "dim": self.dim,
            "index_type": self.index_type,
            "index_config": self.index_config,
            "collection_name": self.collection_name,
        }

        # 添加存储统计
        if hasattr(self.collection, "get_storage_stats"):
            base_stats["storage"] = self.collection.get_storage_stats()

        return base_stats
