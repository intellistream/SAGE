from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterable, List, Optional, TYPE_CHECKING, Type, Union, Any
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.jobmanager.jobmanager_client import JobManagerClient
from sage.core.transformation.base_transformation import BaseTransformation
from sage.core.transformation.source_transformation import SourceTransformation
from sage.core.transformation.batch_transformation import BatchTransformation

if TYPE_CHECKING:
    from sage.core.api.function.base_function import BaseFunction
    from sage.core.api.datastream import DataStream


class BaseEnvironment(ABC):

    __state_exclude__ = ["_engine_client", "client", "jobmanager"]
    # 会被继承，但是不会被自动合并

    def __init__(self, name: str, config: dict | None, *, platform: str = "local"):

        self.name = name
        self.uuid: Optional[str]  # 由jobmanager生成

        self.config: dict = dict(config or {})
        self.platform: str = platform
        # 用于收集所有 BaseTransformation，供 ExecutionGraph 构建 DAG
        self.pipeline: List["BaseTransformation"] = []

        self.env_base_dir: Optional[str] = None  # 环境基础目录，用于存储日志和其他文件
        # JobManager 相关
        self._jobmanager: Optional[Any] = None

        # Engine 客户端相关
        self._engine_client: Optional["JobManagerClient"] = None
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
            raise ValueError(
                f"Invalid log level: {level}. Must be one of {valid_levels}"
            )

        self.console_log_level = level.upper()

        # 如果logger已经初始化，更新其配置
        if hasattr(self, "_logger") and self._logger is not None:
            self._logger.update_output_level("console", self.console_log_level)

    def from_source(self, function: callable) -> "DataStream":
        if not callable(function):
            raise ValueError("function must be callable")
        transformation = SourceTransformation(self, function)

        self.pipeline.append(transformation)
        return DataStream(self, transformation)

    def from_batch(self, data: Union[callable, Iterable]) -> "DataStream":
        if isinstance(data, Iterable):
            return self._from_batch_iterable(data)
        elif isinstance(data, callable):
            return self._from_batch_function_class(data)

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
            self._logger = CustomLogger()
        return self._logger

    @property
    def client(self) -> "JobManagerClient":
        if self._engine_client is None:
            # 从配置中获取 Engine 地址，或使用默认值
            daemon_host = self.config.get("engine_host", "127.0.0.1")
            daemon_port = self.config.get("engine_port", 19000)

            self._engine_client = JobManagerClient(host=daemon_host, port=daemon_port)

        return self._engine_client

    ########################################################
    #                auxiliary methods                     #
    ########################################################

    def _append(self, transformation: "BaseTransformation"):
        """将 BaseTransformation 添加到管道中（Compiler 会使用）。"""
        self.pipeline.append(transformation)
        return DataStream(self, transformation)

    def _from_batch_function_class(
        self, batch_function_class: Type["BaseFunction"]
    ) -> "DataStream":

        transformation = BatchTransformation(self, batch_function_class)

        self.pipeline.append(transformation)
        self.logger.info(
            f"Custom batch source created with {batch_function_class.__name__}"
        )

        return DataStream(self, transformation)

    def _from_batch_iterable(self, iterable: Any, **kwargs) -> "DataStream":
        """
        从任何可迭代对象创建批处理数据源
        """
        from sage.core.api.function.simple_batch_function import (
            IterableBatchIteratorFunction,
        )

        # 尝试获取总数量
        total_count = kwargs.pop("total_count", None)
        if total_count is None:
            try:
                total_count = len(iterable)
            except TypeError:
                # 如果对象没有 len() 方法，则保持 None
                total_count = None

        transformation = BatchTransformation(
            self,
            IterableBatchIteratorFunction,
            iterable=iterable,
            total_count=total_count,
            **kwargs,
        )

        self.pipeline.append(transformation)

        # 构建日志信息
        type_name = type(iterable).__name__
        count_info = f" with {total_count} items" if total_count is not None else ""
        self.logger.info(f"Batch iterable source created from {type_name}{count_info}")

        return DataStream(self, transformation)
