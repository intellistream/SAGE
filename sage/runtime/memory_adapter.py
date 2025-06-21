import ray
import asyncio
from typing import List,Dict,Optional
from sage.core.neuromem.memory_collection.base_collection import BaseMemoryCollection
from sage.core.neuromem.memory_collection.vdb_collection import VDBMemoryCollection
from sage.core.neuromem.memory_collection.kv_collection import KVMemoryCollection

class MemoryAdapter:
    def __init__(self):
        pass

    def retrieve(self, memory_collection, query: str = None, collection_config: Optional[Dict] = None) -> List[str]:
        """
        智能选择检索方式：Ray Actor远程调用或本地对象调用
        """
        if memory_collection is None:
            return []

        # 优先处理Ray Actor
        if self._is_ray_actor(memory_collection):
            return self._retrieve_from_ray_actor(memory_collection, query, collection_config)

        # 处理本地对象
        return self._retrieve_from_local_object(memory_collection, query, collection_config)

    def _retrieve_from_local_object(self, obj, query: str = None, collection_config: Optional[Dict] = None) -> List[
        str]:
        """
        处理本地对象的检索逻辑
        """
        # 检测集合类型
        coll_type = self._detect_collection_type(obj)

        # 处理配置参数
        if collection_config is None:
            collection_config = {}

        topk = collection_config.get("topk")
        index_name = collection_config.get("index_name")
        with_metadata = collection_config.get("with_metadata", False)
        metadata_filter_func = collection_config.get("metadata_filter_func")
        metadata_conditions = collection_config.get("metadata_conditions", {})

        try:
            # 向量数据库类型集合
            if coll_type == "vdb":
                # 验证必要参数
                if query is None:
                    self.logger.warning("Query is required for VDB collection but not provided")
                    return []

                if index_name is None:
                    # 尝试获取默认索引名
                    if hasattr(obj, "indexes") and obj.indexes:
                        index_name = list(obj.indexes.keys())[0]
                        self.logger.info(f"Using default index: {index_name}")
                    else:
                        self.logger.error("No index available in VDB collection")
                        return []

                # 调用VDB检索
                if topk is None:
                    topk = getattr(obj, "default_topk", 3)

                return obj.retrieve(
                    raw_text=query,
                    topk=topk,
                    index_name=index_name,
                    with_metadata=with_metadata,
                    metadata_filter_func=metadata_filter_func,
                    **metadata_conditions
                )

            # 基本类型集合
            elif coll_type == "base":
                # 检查是否有检索参数覆盖
                if query is not None:
                    self.logger.debug(f"Ignoring query for base collection: {query}")

                # 获取查询参数 (metadata_conditions优先)
                if metadata_conditions:
                    return obj.retrieve(
                        with_metadata=with_metadata,
                        metadata_filter_func=metadata_filter_func,
                        **metadata_conditions
                    )
                else:
                    # 默认返回所有内容
                    return obj.retrieve()

            # 其他类型（如KV, Graph）
            else:
                # 尝试直接调用通用的retrieve方法
                if query:
                    try:
                        return obj.retrieve(query)
                    except TypeError:
                        # 如果方法不接受query参数，则回退到无参数调用
                        return obj.retrieve()
                else:
                    return obj.retrieve()

        except Exception as e:
            self.logger.error(f"Retrieve failed for {coll_type} collection: {str(e)}")
            return []

    def _retrieve_from_ray_actor(self, actor, query: str = None, collection_config: Optional[Dict] = None) -> List[str]:
        """
        从Ray Actor同步检索，保留集合类型判断逻辑
        """
        try:
            if not self._is_ray_actor(actor):
                return []

            # 获取集合类型（通过远程调用）
            coll_type_future = actor._detect_collection_type.remote()
            coll_type = ray.get(coll_type_future)

            # 处理配置参数
            if collection_config is None:
                collection_config = {}

            topk = collection_config.get("topk")
            index_name = collection_config.get("index_name")
            with_metadata = collection_config.get("with_metadata", False)
            metadata_filter_func = collection_config.get("metadata_filter_func")
            metadata_conditions = collection_config.get("metadata_conditions", {})

            # 向量数据库类型集合
            if coll_type == "vdb":
                # 验证必要参数
                if query is None:
                    self.logger.warning("Query is required for VDB collection but not provided")
                    return []

                # 获取默认索引名（如果需要）
                if index_name is None:
                    index_names_future = actor.get_index_names.remote()
                    index_names = ray.get(index_names_future)
                    if index_names:
                        index_name = index_names[0]
                        self.logger.info(f"Using default index: {index_name}")
                    else:
                        self.logger.error("No index available in VDB collection")
                        return []

                # 获取默认topk（如果需要）
                if topk is None:
                    default_topk_future = actor.get_default_topk.remote()
                    topk = ray.get(default_topk_future) or 3

                # 调用VDB检索
                return ray.get(actor.retrieve.remote(
                    raw_text=query,
                    topk=topk,
                    index_name=index_name,
                    with_metadata=with_metadata,
                    metadata_filter_func=metadata_filter_func,
                    **metadata_conditions
                ))

            # 基本类型集合
            elif coll_type == "base":
                # 检查是否有检索参数覆盖
                if query is not None:
                    self.logger.debug(f"Ignoring query for base collection: {query}")

                # 获取查询参数 (metadata_conditions优先)
                if metadata_conditions:
                    return ray.get(actor.retrieve.remote(
                        with_metadata=with_metadata,
                        metadata_filter_func=metadata_filter_func,
                        **metadata_conditions
                    ))
                else:
                    # 默认返回所有内容
                    return ray.get(actor.retrieve.remote())

            # 其他类型（如KV, Graph）
            else:
                # 尝试直接调用通用的retrieve方法
                if query:
                    try:
                        return ray.get(actor.retrieve.remote(query))
                    except TypeError:
                        # 如果方法不接受query参数，则回退到无参数调用
                        return ray.get(actor.retrieve.remote())
                else:
                    return ray.get(actor.retrieve.remote())

        except Exception as e:
            self.logger.error(f"Retrieve failed for Ray Actor ({coll_type} collection): {str(e)}")
            return []

    def _is_ray_actor(self, obj) -> bool:
            return hasattr(obj, '_actor_id') and hasattr(obj, '_remote')


    def _detect_collection_type(self, collection) -> str:
        """自动检测内存集合的类型"""
        if isinstance(collection, VDBMemoryCollection):
            return "vdb"
        elif isinstance(collection, BaseMemoryCollection):
            return "base"
        elif hasattr(collection, "create_index") and callable(collection.create_index):
            return "vdb"
        elif hasattr(collection, "vector_storage"):
            return "vdb"
        elif hasattr(collection, "text_storage") and hasattr(collection, "metadata_storage"):
            return "base"
        else:
            return "unknown"

    def store(
            self,
            collection,
            documents: List[str],
            collection_config: Optional[Dict] = None
    ) -> List[str]:
        """
        根据集合类型智能调用对应的存储方法
        """
        stored_ids = []
        if collection is None:
            return stored_ids

        # 处理Ray Actor类型的集合
        if self._is_ray_actor(collection):
            return self._store_to_ray_actor(collection, documents, collection_config)

        # 检测集合类型
        coll_type = self._detect_collection_type(collection)

        # 获取配置参数
        if collection_config is None:
            collection_config = {}

        metadata = collection_config.get("metadata")
        index_names = collection_config.get("index_names", [])

        try:
            # 向量数据库类型集合
            if coll_type == "vdb":
                # 如果没有提供索引名，尝试获取默认索引
                if not index_names:
                    if hasattr(collection, "default_index_name"):
                        index_names = [collection.default_index_name]
                        self.logger.debug(f"Using default index: {index_names[0]}")
                    elif hasattr(collection, "indexes") and collection.indexes:
                        index_names = [list(collection.indexes.keys())[0]]
                        self.logger.info(f"Using first available index: {index_names[0]}")
                    else:
                        self.logger.warning("No index available for VDB storage")
                        return stored_ids

                for doc in documents:
                    if isinstance(metadata, list) and len(metadata) == len(documents):
                        doc_meta = metadata[documents.index(doc)]
                    else:
                        doc_meta = metadata

                    doc_id = collection.insert(
                        raw_text=doc,
                        metadata=doc_meta,
                        *index_names
                    )
                    stored_ids.append(doc_id)

            # 基本类型集合和其他集合
            else:
                for doc in documents:
                    if isinstance(metadata, list) and len(metadata) == len(documents):
                        doc_meta = metadata[documents.index(doc)]
                    else:
                        doc_meta = metadata

                    # 尝试带元数据的插入
                    try:
                        doc_id = collection.insert(
                            raw_text=doc,
                            metadata=doc_meta
                        )
                    except TypeError:
                        # 回退到不带元数据的插入
                        doc_id = collection.insert(raw_text=doc)
                    stored_ids.append(doc_id)

        except Exception as e:
            self.logger.error(f"Store failed for {coll_type} collection: {str(e)}")

        return stored_ids

    def _store_to_ray_actor(
            self,
            actor,
            documents: List[str],
            collection_config: Optional[Dict] = None
    ) -> List[str]:
        """存储到Ray Actor"""
        try:
            if not self._is_ray_actor(actor):
                return []

            # 获取集合类型
            coll_type_future = actor._detect_collection_type.remote()
            coll_type = ray.get(coll_type_future)

            if collection_config is None:
                collection_config = {}

            # 向量数据库的特殊处理
            if coll_type == "vdb":
                index_names = collection_config.get("index_names", [])

                # 处理默认索引
                if not index_names:
                    # 尝试获取默认索引名
                    if ray.get(actor.has_attribute.remote("default_index_name")):
                        index_names = [ray.get(actor.get_attribute.remote("default_index_name"))]
                        self.logger.debug(f"Using default index: {index_names[0]}")
                    else:
                        # 尝试获取第一个可用索引
                        index_names_future = actor.get_index_names.remote()
                        all_names = ray.get(index_names_future)
                        if all_names:
                            index_names = [all_names[0]]
                            self.logger.info(f"Using first available index: {index_names[0]}")
                        else:
                            self.logger.warning("No index available for Ray actor VDB storage")
                            return []

                collection_config["index_names"] = index_names

            return ray.get(actor.store.remote(documents, collection_config))

        except Exception as e:
            self.logger.error(f"Error storing to Ray actor: {e}")
            return []
