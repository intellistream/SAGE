from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
import os
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING, Type, Union, Any
from sage.kernel.core.api.function.lambda_function import wrap_lambda

# 使用兼容性层安全导入闭源依赖
from sage.kernel.core.api.compatibility import safe_import_kernel_client, safe_import_custom_logger

# 获取闭源模块的类（如果可用，否则使用回退实现）
_JobManagerClient = safe_import_kernel_client()
_CustomLogger = safe_import_custom_logger()

from sage.kernel.core.factory.service_factory import ServiceFactory

if TYPE_CHECKING:
    from sage.kernel.core.api.function.base_function import BaseFunction
    from sage.kernel.core.api.datastream import DataStream
    from sage.kernel.core.transformation.base_transformation import BaseTransformation
    from sage.kernel.core.transformation.source_transformation import SourceTransformation
    from sage.kernel.core.transformation.batch_transformation import BatchTransformation
    from sage.kernel.core.transformation.future_transformation import FutureTransformation
    # 类型提示使用 Any 来避免循环导入问题
    JobManagerClientType = Any
    CustomLoggerType = Any
else:
    JobManagerClientType = _JobManagerClient
    CustomLoggerType = _CustomLogger

    
class BaseEnvironment(ABC):

    __state_exclude__ = ["_engine_client", "client", "jobmanager"]
    # 会被继承，但是不会被自动合并

    def _get_datastream_class(self):
        """Deferred import of DataStream to avoid circular imports"""
        if not hasattr(self, '_datastream_class'):
            from sage.kernel.core.api.datastream import DataStream
            self._datastream_class = DataStream
        return self._datastream_class

    def _get_transformation_classes(self):
        """动态导入transformation类以避免循环导入"""
        if not hasattr(self, '_transformation_classes'):
            from sage.kernel.core.transformation.base_transformation import BaseTransformation
            from sage.kernel.core.transformation.source_transformation import SourceTransformation
            from sage.kernel.core.transformation.batch_transformation import BatchTransformation
            from sage.kernel.core.transformation.future_transformation import FutureTransformation
            
            self._transformation_classes = {
                'BaseTransformation': BaseTransformation,
                'SourceTransformation': SourceTransformation,
                'BatchTransformation': BatchTransformation,
                'FutureTransformation': FutureTransformation
            }
        return self._transformation_classes

    def __init__(self, name: str, config: dict | None, *, platform: str = "local"):

        self.name = name
        self.uuid: Optional[str] # 由jobmanager生成

        self.config: dict = dict(config or {})
        self.platform:str = platform
        # 用于收集所有 BaseTransformation，供 ExecutionGraph 构建 DAG
        self.pipeline: List['BaseTransformation'] = []
        self._filled_futures: dict = {}  
        # 用于收集所有服务工厂，供ExecutionGraph构建服务节点时使用
        self.service_factories: dict = {}  # service_name -> ServiceFactory

        self.env_base_dir: Optional[str] = None  # 环境基础目录，用于存储日志和其他文件
        
        # JobManager 相关
        self._jobmanager: Optional[Any] = None
        
        # Engine 客户端相关
        self._engine_client: Optional[JobManagerClientType] = None
        self.env_uuid: Optional[str] = None
        
        # 日志配置
        self.console_log_level: str = "INFO"  # 默认console日志等级

    ########################################################
    #                  user interface                      #
    ########################################################

    def set_console_log_level(self, level: str):
        """
        设置控制台日志等级
        
        Args:
            level: 日志等级，可选值: "DEBUG", "INFO", "WARNING", "ERROR"
            
        Example:
            env.set_console_log_level("DEBUG")  # 显示所有日志
            env.set_console_log_level("WARNING")  # 只显示警告和错误
        """
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {level}. Must be one of {valid_levels}")
        
        self.console_log_level = level.upper()
        
        # 如果logger已经初始化，更新其配置
        if hasattr(self, '_logger') and self._logger is not None:
            self._logger.update_output_level("console", self.console_log_level)


    def register_service(self, service_name: str, service_class: Type, *args, **kwargs):
        """
        注册服务到环境中
        
        Args:
            service_name: 服务名称，用于标识服务
            service_class: 服务类，将在任务提交时实例化
            *args: 传递给服务构造函数的位置参数
            **kwargs: 传递给服务构造函数的关键字参数
            
        Example:
            # 注册一个自定义服务
            env.register_service("my_cache", MyCacheService, cache_size=1000)
            
            # 注册数据库连接服务
            env.register_service("db_conn", DatabaseConnection, 
                               host="localhost", port=5432, db="mydb")
        """
        # 创建服务工厂
        service_factory = ServiceFactory(
            service_name=service_name,
            service_class=service_class,
            service_args=args,
            service_kwargs=kwargs
        )
        
        self.service_factories[service_name] = service_factory
        
        platform_str = "remote" if self.platform == "remote" else "local"
        self.logger.info(f"Registered {platform_str} service: {service_name} ({service_class.__name__})")
        
        return service_factory

    def register_service_factory(self, service_name: str, service_factory: ServiceFactory):
        """
        注册服务工厂到环境中
        
        Args:
            service_name: 服务名称，用于标识服务
            service_factory: 服务工厂实例
            
        Example:
            # 注册预配置的服务工厂
            kv_factory = create_kv_service_factory("my_kv", backend_type="memory")
            env.register_service_factory("my_kv", kv_factory)
        """
        self.service_factories[service_name] = service_factory
        
        platform_str = "remote" if self.platform == "remote" else "local"
        self.logger.info(f"Registered {platform_str} service factory: {service_name}")
        
        return service_factory

    ########################################################
    #                jobmanager interface                  #
    ########################################################
    @abstractmethod
    def submit(self):
        pass


    ########################################################
    #                properties                            #
    ########################################################

    @property
    def logger(self):
        if not hasattr(self, "_logger"):
            self._logger = _CustomLogger()
        return self._logger

    @property
    def client(self) -> JobManagerClientType:
        if self._engine_client is None:
            # 从配置中获取 Engine 地址，或使用默认值
            daemon_host = self.config.get("engine_host", "127.0.0.1")
            daemon_port = self.config.get("engine_port", 19000)
            
            self._engine_client = _JobManagerClient(host=daemon_host, port=daemon_port)
            
        return self._engine_client

    ########################################################
    #                auxiliary methods                     #
    ########################################################

    def _append(self, transformation: 'BaseTransformation'):
        """将 BaseTransformation 添加到管道中（Compiler 会使用）。"""
        self.pipeline.append(transformation)
        return self._get_datastream_class()(self, transformation)
