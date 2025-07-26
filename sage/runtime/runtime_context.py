import os
import threading
from typing import TYPE_CHECKING
import ray
from ray.actor import ActorHandle
from typing import List,Dict,Optional, Any, Union
from sage.service.memory.memory_collection.base_collection import BaseMemoryCollection
from sage.service.memory.memory_collection.vdb_collection import VDBMemoryCollection
from sage.utils.custom_logger import CustomLogger
from sage.utils.actor_wrapper import ActorWrapper

if TYPE_CHECKING:
    from sage.jobmanager.execution_graph import ExecutionGraph, GraphNode
    from sage.core.transformation.base_transformation import BaseTransformation
    from sage.core.api.base_environment import BaseEnvironment 
    from sage.jobmanager.job_manager import JobManager
    from sage.runtime.service.service_caller import ServiceManager
    from sage.core.function.source_function import StopSignal
# task, operator和function "形式上共享"的运行上下文

class RuntimeContext:
    # 定义不需要序列化的属性
    __state_exclude__ = ["_logger", "env", "_env_logger_cache"]
    def __init__(self, graph_node: 'GraphNode', transformation: 'BaseTransformation', env: 'BaseEnvironment', jobmanager: Union['JobManager', 'ActorHandle'] = None):
        
        self.name:str = graph_node.name

        self.env_name = env.name
        self.env_base_dir:str = env.env_base_dir
        self.env_uuid = env.uuid
        self.env_console_log_level = env.console_log_level  # 保存环境的控制台日志等级

        self.memory_collection:Any = transformation.memory_collection

        self.parallel_index:int = graph_node.parallel_index
        self.parallelism:int = graph_node.parallelism

        self._logger:Optional[CustomLogger] = None

        self.is_spout = transformation.is_spout

        self.delay = 0.01
        self.stop_signal_num = graph_node.stop_signal_num
        
        # 添加JobManager引用，去actor化后的直接引用
        self.jobmanager = jobmanager
        
        # 添加共享的停止事件，供operator和router使用
        self._stop_event = threading.Event()
        
        # 停止信号计数相关（从SinkOperator移到这里）
        self.received_stop_signals = set()
        self.stop_signal_count = 0
        
        # 服务调用相关
        self._service_manager: Optional['ServiceManager'] = None
        self._dispatcher_services: Optional[Dict[str, Any]] = None  # 将由dispatcher设置
    
    @property
    def service_manager(self) -> 'ServiceManager':
        """懒加载服务管理器"""
        if self._service_manager is None:
            from sage.runtime.service.service_caller import ServiceManager
            self._service_manager = ServiceManager(self)
        return self._service_manager


    def retrieve(self,  query: Optional[str] = None, collection_config: Optional[Dict] = None) -> List[str]:
        """
        智能选择检索方式：Ray Actor远程调用或本地对象调用
        """
        if self.memory_collection is None:
            return []

        # 优先处理Ray Actor
        if self._is_ray_actor(self.memory_collection):
            return self._retrieve_from_ray_actor(self.memory_collection, query, collection_config)

        # 处理本地对象
        return self._retrieve_from_local_object(self.memory_collection, query, collection_config)
    
    def _retrieve_from_local_object(self, obj, query: str = None, collection_config: Optional[Dict] = None) -> List[
        str]:
        """
        处理本地对象的检索逻辑
        """
        self.logger.debug(f"Retrieving from local object: {type(obj).__name__}")
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


    def _is_ray_actor(self, obj) -> bool:
        """检测执行模式"""
        if isinstance(obj, ActorHandle):
            return 1
        elif hasattr(obj, 'remote'):
            return 1
        else:
            return 0
        # return hasattr(obj, '_actor_id') and hasattr(obj, '_remote')



    def _retrieve_from_ray_actor(self, actor, query: str = None, collection_config: Optional[Dict] = None) -> List[str]:
        """
        从Ray Actor同步检索，保留集合类型判断逻辑
        """
        try:
            if not self._is_ray_actor(actor):
                return []

        
            coll_type = "vdb"

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
                    indexes_future = actor.list_index.remote()
                    indexes = ray.get(indexes_future)
                    index_names = [index["name"] for index in indexes]  # 过滤掉空字符串
                    self.logger.debug(f"Available index names: {index_names}")                   
                    if index_names:
                        index_name = index_names[0]
                        self.logger.info(f"Using default index: {index_name}")
                    else:
                        self.logger.warning("No index available in VDB collection")
                        return []

                # 获取默认topk（如果需要）
                # if topk is None:
                #     default_topk_future = actor.get_default_topk.remote()
                #     topk = remote.get(default_topk_future) or 3
                if topk is None:
                    topk = getattr(actor, "default_topk", 3)
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
            documents: List[str],
            collection_config: Optional[Dict] = None
    ) -> List[str]:
        """
        根据集合类型智能调用对应的存储方法
        """
        stored_ids = []
        if self.memory_collection is None:
            return stored_ids

        # 处理Ray Actor类型的集合
        if self._is_ray_actor(self.memory_collection):
            return self._store_to_ray_actor(self.memory_collection, documents, collection_config)

        # 检测集合类型
        coll_type = self._detect_collection_type(self.memory_collection)

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
                    if hasattr(self.memory_collection, "default_index_name"):
                        index_names = [self.memory_collection.default_index_name]
                        self.logger.debug(f"Using default index: {index_names[0]}")
                    elif hasattr(self.memory_collection, "indexes") and self.memory_collection.indexes:
                        index_names = [list(self.memory_collection.indexes.keys())[0]]
                        self.logger.info(f"Using first available index: {index_names[0]}")
                    else:
                        self.logger.warning("No index available for VDB storage")
                        return stored_ids

                for doc in documents:
                    if isinstance(metadata, list) and len(metadata) == len(documents):
                        doc_meta = metadata[documents.index(doc)]
                    else:
                        doc_meta = metadata

                    doc_id = self.memory_collection.insert(
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
                        doc_id = self.memory_collection.insert(
                            raw_text=doc,
                            metadata=doc_meta
                        )
                    except TypeError:
                        # 回退到不带元数据的插入
                        doc_id = self.memory_collection.insert(raw_text=doc)
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


    @property
    def logger(self) -> CustomLogger:
        """懒加载logger"""
        if self._logger is None:
            self._logger = CustomLogger([
                ("console", self.env_console_log_level),  # 使用环境设置的控制台日志等级
                (os.path.join(self.env_base_dir, f"{self.name}_debug.log"), "DEBUG"),  # 详细日志
                (os.path.join(self.env_base_dir, "Error.log"), "ERROR"),  # 错误日志
                (os.path.join(self.env_base_dir, f"{self.name}_info.log"), "INFO")  # 错误日志
            ],
            name = f"{self.name}",
        )
        return self._logger

    def set_dispatcher_services(self, services: Dict[str, Any]):
        """设置dispatcher管理的服务实例（由dispatcher调用）"""
        self._dispatcher_services = services

    def get_service(self, service_name: str) -> Any:
        """
        获取服务实例
        
        Args:
            service_name: 服务名称
            
        Returns:
            服务实例
            
        Raises:
            ValueError: 当服务不存在时
        """
        if self._dispatcher_services is None:
            raise RuntimeError("Services not available - dispatcher not initialized")
        
        if service_name not in self._dispatcher_services:
            available_services = list(self._dispatcher_services.keys())
            raise ValueError(f"Service '{service_name}' not found. Available services: {available_services}")
        
        return self._dispatcher_services[service_name]

    def call_service(self, service_name: str, method_name: str, *args, **kwargs) -> Any:
        """
        调用服务方法
        
        Args:
            service_name: 服务名称
            method_name: 方法名称
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            方法调用结果
        """
        service = self.get_service(service_name)
        
        # 检查是否是ActorWrapper包装的Ray服务
        if hasattr(service, '_actor') and hasattr(service, 'is_alive'):
            # 这是一个ActorWrapper，需要使用remote调用
            import ray
            method = getattr(service, method_name)
            if hasattr(method, 'remote'):
                # 远程调用
                future = method.remote(*args, **kwargs)
                return ray.get(future)
            else:
                # 本地方法调用
                return method(*args, **kwargs)
        else:
            # 本地服务，直接调用
            return service.call_method(method_name, *args, **kwargs)

    def list_services(self) -> List[str]:
        """列出所有可用的服务名称"""
        if self._dispatcher_services is None:
            return []
        return list(self._dispatcher_services.keys())

    @property
    def stop_event(self) -> threading.Event:
        """获取共享的停止事件"""
        return self._stop_event
    
    def set_stop_signal(self):
        """设置停止信号"""
        self._stop_event.set()
    
    def is_stop_requested(self) -> bool:
        """检查是否请求停止"""
        return self._stop_event.is_set()
    
    def clear_stop_signal(self):
        """清除停止信号"""
        self._stop_event.clear()
        # 同时清除停止信号计数
        self.received_stop_signals.clear()
        self.stop_signal_count = 0
    
    def handle_stop_signal(self, stop_signal: 'StopSignal') -> bool:
        """
        在task层处理停止信号计数
        返回True表示收到了所有预期的停止信号
        """
        if stop_signal.name in self.received_stop_signals:
            self.logger.debug(f"Already received stop signal from {stop_signal.name}")
            return False
        
        self.received_stop_signals.add(stop_signal.name)
        self.logger.info(f"Task {self.name} received stop signal from {stop_signal.name}")

        self.stop_signal_count += 1
        if self.stop_signal_count >= self.stop_signal_num:
            self.logger.info(f"Task {self.name} received all expected stop signals ({self.stop_signal_count}/{self.stop_signal_num})")
            
            # 通知JobManager停止整个流水线
            if self.jobmanager:
                try:
                    self.logger.info(f"Task {self.name} notifying JobManager to stop pipeline")
                    self.jobmanager.receive_stop_signal(self.env_uuid)
                except Exception as e:
                    self.logger.error(f"Failed to notify JobManager: {e}", exc_info=True)
            
            return True
        else:
            self.logger.info(f"Task {self.name} stop signal count: {self.stop_signal_count}/{self.stop_signal_num}")
            return False
