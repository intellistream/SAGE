import ray
import asyncio
from typing import List


class MemoryAdapter:
    def __init__(self):
        pass

    def retrieve(self, memory_collection, query: str = None, collection_config: Optional[Dict] = None) -> List[str]:
        """
        根据collection类型智能调用对应的检索方法
        """
        if memory_collection is None:
            return []

        # 获取集合类型配置
        coll_type = self._detect_collection_type(memory_collection)

        # 尝试获取配置中的具体参数
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
                    if hasattr(memory_collection, "indexes") and memory_collection.indexes:
                        index_name = list(memory_collection.indexes.keys())[0]
                        self.logger.info(f"Using default index: {index_name}")
                    else:
                        self.logger.error("No index available in VDB collection")
                        return []

                # 调用VDB检索
                if topk is None:
                    topk = getattr(memory_collection, "default_topk", 3)

                return memory_collection.retrieve(
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
                    return memory_collection.retrieve(
                        with_metadata=with_metadata,
                        metadata_filter_func=metadata_filter_func,
                        **metadata_conditions
                    )
                else:
                    # 默认返回所有内容
                    return memory_collection.retrieve()

            # 其他类型（如KV, Graph）
            else:
                # 尝试直接调用通用的retrieve方法
                if query:
                    try:
                        return memory_collection.retrieve(query)
                    except TypeError:
                        # 如果方法不接受query参数，则回退到无参数调用
                        return memory_collection.retrieve()
                else:
                    return memory_collection.retrieve()

        except Exception as e:
            self.logger.error(f"Retrieve failed for {coll_type} collection: {str(e)}")
            return []

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

    # 其他原有方法保持...
    def _is_ray_actor(self, obj) -> bool:
        """检查对象是否是Ray Actor"""
        return hasattr(obj, '_actor_id') and hasattr(obj, '_remote')

    def _retrieve_from_ray_actor(self, actor, query: str = None, collection_config: Optional[Dict] = None) -> List[str]:
        """从Ray Actor同步检索"""
        try:
            if self._is_ray_actor(actor):
                # 构造远程调用
                if query is not None:
                    future = actor.retrieve.remote(query, collection_config)
                else:
                    future = actor.retrieve.remote(None, collection_config)

                # 同步阻塞获取结果
                return ray.get(future)
            return []
        except Exception as e:
            print(f"Error retrieving from Ray actor: {e}")
            return []

    def _retrieve_from_local_object(self, obj, query: str = None, collection_config: Optional[Dict] = None) -> List[
        str]:
        try:
            # 直接调用对象的retrieve方法
            return self.retrieve(obj, query, collection_config)
        except Exception as e:
            print(f"Error retrieving from local object: {e}")
            return []

    def _run_async_coroutine(self, coro):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(coro, loop)
                return future.result()
            else:
                return asyncio.run(coro)
        except Exception as e:
            print(f"Failed to run async coroutine: {e}")
            return []