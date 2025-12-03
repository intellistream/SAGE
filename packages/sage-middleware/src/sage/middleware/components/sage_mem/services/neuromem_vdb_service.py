"""NeuroMem VDB Service - VDB 记忆服务

设计原则:
- 支持连接多个现有的 Collection (只读模式)
- 每个 Collection 使用统一接口
"""

import os
import uuid
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager
from sage.platform.service import BaseService

if TYPE_CHECKING:
    from sage.middleware.components.sage_mem.neuromem.memory_collection.base_collection import (
        BaseMemoryCollection,
    )


class NeuroMemVDBService(BaseService):
    def __init__(self, collection_name: str | list[str]):
        super().__init__()
        self.manager = MemoryManager(self._get_default_data_dir())
        self.online_register_collections: dict[str, BaseMemoryCollection] = {}

        # 处理collection_name参数，支持单个字符串或字符串列表
        if isinstance(collection_name, str):
            collection_names = [collection_name]
        else:
            collection_names = collection_name

        # 连接已有的collection，不存在就会报错
        for name in collection_names:
            try:
                collection = self.manager.get_collection(name)
                if collection is None:
                    raise ValueError(f"Collection '{name}' not found")

                self.online_register_collections[name] = collection
                self.logger.info(f"Successfully connected to collection: {name}")

                # 检查是否有global_index，没有就创建一个
                if (
                    hasattr(collection, "index_info")
                    and "global_index" not in collection.index_info
                ):
                    self.logger.info(f"Creating global_index for collection: {name}")
                    index_config = {
                        "name": "global_index",
                        "embedding_model": "default",
                        "dim": 384,
                        "backend_type": "FAISS",
                        "description": "Global index for all data",
                    }
                    collection.create_index(config=index_config)

            except Exception as e:
                self.logger.error(f"Failed to connect to collection '{name}': {str(e)}")
                raise

    def insert(
        self,
        entry: str,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict | None = None,
        *,
        insert_mode: Literal["active", "passive"] = "passive",
        insert_params: dict | None = None,
    ) -> str:
        """插入记忆条目

        支持两种插入模式：
        - passive: 由服务自行决定存储方式（插入到第一个 collection）
        - active: 根据 insert_params 指定存储方式

        Args:
            entry: 文本内容
            vector: embedding 向量（可选）
            metadata: 元数据（可选）
            insert_mode: 插入模式 ("active" | "passive")
            insert_params: 主动插入参数
                - collection: 目标 collection 名称
                - priority: 优先级

        Returns:
            str: 插入的条目 ID
        """
        if not isinstance(entry, str):
            raise TypeError("entry must be a string")

        # 处理插入模式
        collection_name = None
        if insert_mode == "active" and insert_params:
            collection_name = insert_params.get("collection")
            if "priority" in insert_params:
                metadata = metadata.copy() if metadata else {}
                metadata["priority"] = insert_params["priority"]

        # 确定目标 collection
        if collection_name is None:
            collection_name = list(self.online_register_collections.keys())[0]

        if collection_name not in self.online_register_collections:
            raise ValueError(f"Collection '{collection_name}' is not registered")

        collection = self.online_register_collections[collection_name]

        # 生成 ID
        metadata = metadata or {}
        entry_id = metadata.get("id", str(uuid.uuid4()))
        metadata["entry_id"] = entry_id

        # 插入
        if vector is not None:
            vec = np.array(vector, dtype=np.float32)
            collection.insert(
                index_name="global_index",
                raw_data=entry,
                vector=vec,
                metadata=metadata,
            )
        else:
            # 没有向量时，调用父类 BaseMemoryCollection 的 insert
            collection.insert(entry, metadata)

        self.logger.debug(f"Inserted entry to collection '{collection_name}': {entry_id[:16]}...")
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
        """检索记忆

        Args:
            query: 查询文本
            vector: 查询向量（可选）
            metadata: 查询参数（可选），服务特定参数放在此处:
                - collection: 指定 collection 名称
                - with_metadata: 是否返回元数据（默认 True）
            top_k: 返回结果数量
            hints: 检索策略提示（可选，由 PreRetrieval route action 生成）
            threshold: 相似度阈值（可选，过滤低于阈值的结果）

        Returns:
            list[dict]: 检索结果，每个结果包含:
                - text: 文本内容
                - score: 相似度分数
                - metadata: 元数据（可选）
                - entry_id: 条目 ID（如果有）
        """
        _ = hints  # 保留用于未来扩展
        _ = threshold  # 暂不使用相似度阈值
        if not self.online_register_collections:
            self.logger.warning("No collections are registered")
            return []

        if query is None:
            return []

        # 从 metadata 获取额外参数
        metadata = metadata or {}
        collection_name = metadata.get("collection")
        with_metadata = metadata.get("with_metadata", True)

        all_results = []

        # 如果指定了collection_name，只在该collection上检索
        if collection_name:
            if collection_name not in self.online_register_collections:
                raise ValueError(f"Collection '{collection_name}' is not registered")
            collections_to_search = {
                collection_name: self.online_register_collections[collection_name]
            }
        else:
            # 在所有注册的collection上检索
            collections_to_search = self.online_register_collections

        for name, collection in collections_to_search.items():
            try:
                results = collection.retrieve(
                    query,
                    top_k=top_k,
                    index_name="global_index",
                    with_metadata=with_metadata,
                )

                # Handle None results (collection.retrieve can return None)
                if results is None:
                    self.logger.warning(f"No results from collection: {name}")
                    continue

                # 为结果添加来源collection信息
                if with_metadata:
                    for result in results:
                        if isinstance(result, dict):
                            result["source_collection"] = name
                        else:
                            # 如果结果不是dict，转换为dict格式
                            result = {"text": result, "source_collection": name}
                else:
                    # 如果不要metadata，也可以选择添加来源信息
                    results = [{"text": result, "source_collection": name} for result in results]

                all_results.extend(results)
                self.logger.debug(f"Retrieved {len(results)} results from collection: {name}")

            except Exception as e:
                self.logger.error(f"Error retrieving from collection '{name}': {str(e)}")

        # 如果有多个collection的结果，可以按相似度重新排序（这里简化处理）
        return all_results[:top_k] if len(all_results) > top_k else all_results

    def delete(self, entry_id: str) -> bool:
        """删除记忆条目

        Args:
            entry_id: 条目 ID

        Returns:
            bool: 是否删除成功
        """
        # 遍历所有 collection 删除
        for name, collection in self.online_register_collections.items():
            try:
                collection.delete(entry_id)
                self.logger.debug(f"Deleted entry {entry_id[:16]}... from collection '{name}'")
                return True
            except Exception as e:
                self.logger.debug(f"Entry {entry_id[:16]}... not found in collection '{name}': {e}")
                continue

        self.logger.warning(f"Failed to delete entry {entry_id[:16]}... from any collection")
        return False

    def _create_index(self, collection_name: str, index_name: str, **kwargs):
        """为指定collection创建索引"""
        if collection_name not in self.online_register_collections:
            raise ValueError(f"Collection '{collection_name}' is not registered")

        collection = self.online_register_collections[collection_name]
        # create_index expects a config dict, not individual kwargs
        index_config = {"name": index_name, **kwargs}
        collection.create_index(config=index_config)
        self.logger.info(f"Created index '{index_name}' for collection '{collection_name}'")

    @classmethod
    def _get_default_data_dir(cls):
        """获取默认数据目录"""
        cur_dir = os.getcwd()
        data_dir = os.path.join(cur_dir, "data", "neuromem_vdb")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir
