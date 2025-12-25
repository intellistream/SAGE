"""向量记忆服务 - Partitional 类

统一向量记忆服务，支持多种 FAISS 索引后端。

设计原则:
- Service : Collection = 1 : 1
- 使用 VDBMemoryCollection 作为底层存储
- 支持多种索引类型（LSH/HNSW/IVF/Flat等）

Layer: L4 (Middleware)

支持的索引类型:
- IndexLSH: 局部敏感哈希（快速近似检索）
- IndexHNSWFlat: 分层可导航小世界图（高性能，高召回率）
- IndexFlatL2: L2距离暴力搜索（精确但慢）
- IndexFlatIP: 内积暴力搜索（适用于归一化向量）
- IndexIVFFlat: 倒排文件索引（平衡速度与精度）
- IndexIVFPQ: IVF + 乘积量化（压缩存储）
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from sage.kernel.runtime.factory.service_factory import ServiceFactory
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager

from ..base_service import BaseMemoryService

if TYPE_CHECKING:
    import numpy as np


class VectorMemoryService(BaseMemoryService):
    """统一向量记忆服务 - Partitional 类

    支持多种 FAISS 索引后端，通过配置选择最适合的索引类型。

    设计原则：
    - Service : Collection = 1 : 1
    - 使用 VDBMemoryCollection
    - 可配置索引类型和参数
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
            index_type: 索引类型（支持 IndexLSH/IndexHNSWFlat/IndexFlatL2 等）
            index_config: 索引配置参数（覆盖默认值）
            collection_name: NeuroMem collection 名称
            index_name: 索引名称
        """
        super().__init__()

        # 验证 index_type
        if index_type not in self.DEFAULT_INDEX_CONFIGS:
            supported = ", ".join(self.DEFAULT_INDEX_CONFIGS.keys())
            raise ValueError(f"Unsupported index_type: {index_type}. Supported: {supported}")

        self.dim = dim
        self.index_type = index_type
        self.collection_name = collection_name
        self.index_name = index_name

        # 合并默认配置和用户配置
        default_config = self.DEFAULT_INDEX_CONFIGS[index_type].copy()
        if index_config:
            default_config.update(index_config)
        self.index_config = default_config

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

    @classmethod
    def from_config(cls, service_name: str, config: Any) -> ServiceFactory:
        """从配置创建 ServiceFactory

        配置示例:
            services:
              partitional.vector_memory:
                dim: 768
                index_type: IndexHNSWFlat
                index_config:
                  M: 32
                  efConstruction: 200
                collection_name: vector_memory
        """
        dim = config.get(f"services.{service_name}.dim")
        if dim is None:
            raise ValueError(f"Missing config: services.{service_name}.dim")

        index_type = config.get(f"services.{service_name}.index_type", "IndexFlatL2")
        index_config = config.get(f"services.{service_name}.index_config", None)
        collection_name = config.get(
            f"services.{service_name}.collection_name",
            f"vec_{service_name.replace('.', '_')}",
        )
        index_name = config.get(f"services.{service_name}.index_name", "main_index")

        return ServiceFactory(
            service_name=service_name,
            service_class=cls,
            service_kwargs={
                "dim": dim,
                "index_type": index_type,
                "index_config": index_config,
                "collection_name": collection_name,
                "index_name": index_name,
            },
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
        metadata: dict[str, Any] | None = None,
        *,
        insert_mode: Literal["active", "passive"] = "passive",
        insert_params: dict[str, Any] | None = None,
    ) -> str:
        """插入文本和向量"""
        if not isinstance(entry, str):
            raise TypeError(f"entry must be str, got {type(entry).__name__}")

        if vector is None:
            raise ValueError("Vector is required for VectorMemoryService")

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
        self.logger.debug(f"Inserted vector: {stable_id[:16]}...")

        return stable_id

    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """检索向量"""
        if vector is None:
            return []

        import numpy as np

        query_vec = np.array(vector, dtype=np.float32)

        # 从 collection 检索
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
            "index_type": self.index_type,
            "collection_name": self.collection_name,
            "index_name": self.index_name,
        }
