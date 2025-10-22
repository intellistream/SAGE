import os
from typing import Any, Dict, List, Optional, Union

from sage.platform.service import BaseService
from sage.middleware.components.sage_mem.neuromem.memory_collection.vdb_collection import (
    VDBMemoryCollection,
)
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager


class NeuroMemVDBService(BaseService):
    def __init__(self, collection_name: Union[str, List[str]]):
        self.manager = MemoryManager(self._get_default_data_dir())
        self.online_register_collections: Dict[str, VDBMemoryCollection] = {}

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
                if not isinstance(collection, VDBMemoryCollection):
                    raise TypeError(f"Collection '{name}' is not a VDBMemoryCollection")

                self.online_register_collections[name] = collection
                self.logger.info(f"Successfully connected to collection: {name}")

                # 检查是否有global_index，没有就创建一个
                if "global_index" not in collection.indexes:
                    self.logger.info(f"Creating global_index for collection: {name}")
                    collection.create_index(
                        "global_index", description="Global index for all data"
                    )

            except Exception as e:
                self.logger.error(f"Failed to connect to collection '{name}': {str(e)}")
                raise

    def retrieve(
        self,
        query_text: str,
        topk: int = 5,
        collection_name: Optional[str] = None,
        with_metadata: bool = False,
        **kwargs,
    ) -> List[Any]:
        """
        在所有online_register_collections上按照vdb_collection方式检索，默认使用global_index

        Args:
            query_text: 查询文本
            topk: 返回结果数量
            collection_name: 指定collection名称，如果为None则在所有collection上检索
            with_metadata: 是否返回metadata
            **kwargs: 其他检索参数

        Returns:
            检索结果列表
        """
        if not self.online_register_collections:
            self.logger.warning("No collections are registered")
            return []

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
                    query_text,
                    topk=topk,
                    index_name="global_index",
                    with_metadata=with_metadata,
                    **kwargs,
                )

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
                    results = [
                        {"text": result, "source_collection": name}
                        for result in results
                    ]

                all_results.extend(results)
                self.logger.debug(
                    f"Retrieved {len(results)} results from collection: {name}"
                )

            except Exception as e:
                self.logger.error(
                    f"Error retrieving from collection '{name}': {str(e)}"
                )

        # 如果有多个collection的结果，可以按相似度重新排序（这里简化处理）
        return all_results[:topk] if len(all_results) > topk else all_results

    def _create_index(self, collection_name: str, index_name: str, **kwargs):
        """为指定collection创建索引"""
        if collection_name not in self.online_register_collections:
            raise ValueError(f"Collection '{collection_name}' is not registered")

        collection = self.online_register_collections[collection_name]
        collection.create_index(index_name, **kwargs)
        self.logger.info(
            f"Created index '{index_name}' for collection '{collection_name}'"
        )

    @classmethod
    def _get_default_data_dir(cls):
        """获取默认数据目录"""
        cur_dir = os.getcwd()
        data_dir = os.path.join(cur_dir, "data", "neuromem_vdb")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir
