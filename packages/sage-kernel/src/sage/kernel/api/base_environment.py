from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from sage.common.core import wrap_lambda
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.runtime.factory.service_factory import ServiceFactory
from sage.kernel.runtime.jobmanager_client import JobManagerClient

if TYPE_CHECKING:
    from sage.common.core.functions import BaseFunction
    from sage.kernel.api.datastream import DataStream
    from sage.kernel.api.transformation.base_transformation import BaseTransformation


class BaseEnvironment(ABC):
    __state_exclude__ = ["_engine_client", "client", "jobmanager"]
    # 会被继承，但是不会被自动合并

    def _get_datastream_class(self):
        """Deferred import of DataStream to avoid circular imports"""
        if not hasattr(self, "_datastream_class"):
            from sage.kernel.api.datastream import DataStream

            self._datastream_class = DataStream
        return self._datastream_class

    def _get_transformation_classes(self):
        """动态导入transformation类以避免循环导入"""
        if not hasattr(self, "_transformation_classes"):
            from sage.kernel.api.transformation.base_transformation import (
                BaseTransformation,
            )
            from sage.kernel.api.transformation.batch_transformation import (
                BatchTransformation,
            )
            from sage.kernel.api.transformation.future_transformation import (
                FutureTransformation,
            )
            from sage.kernel.api.transformation.source_transformation import (
                SourceTransformation,
            )

            self._transformation_classes = {
                "BaseTransformation": BaseTransformation,
                "SourceTransformation": SourceTransformation,
                "BatchTransformation": BatchTransformation,
                "FutureTransformation": FutureTransformation,
            }
        return self._transformation_classes

    def __init__(
        self,
        name: str,
        config: dict | None,
        *,
        platform: str = "local",
        scheduler=None,
        enable_monitoring: bool = False,
    ):
        self.name = name
        self.uuid: str | None = None  # 由jobmanager生成

        self.config: dict = dict(config or {})
        self.platform: str = platform

        # JobManager 注入的属性
        self.jobmanager_host: str | None = None
        self.jobmanager_port: int | None = None
        self.session_id: str | None = None
        self.session_timestamp: Any | None = None  # datetime object
        # 用于收集所有 BaseTransformation，供 ExecutionGraph 构建 DAG
        self.pipeline: list[BaseTransformation] = []
        self._filled_futures: dict = {}
        # 用于收集所有服务工厂，供ExecutionGraph构建服务节点时使用
        self.service_factories: dict = {}  # service_name -> ServiceFactory

        # 性能监控配置
        self.enable_monitoring: bool = enable_monitoring

        # 调度器配置（用户可选）
        self._scheduler = None
        self._init_scheduler(scheduler)

        self.env_base_dir: str | None = None  # 环境基础目录，用于存储日志和其他文件
        # JobManager 相关
        self._jobmanager: Any | None = None

        # Engine 客户端相关
        self._engine_client: JobManagerClient | None = None
        self.env_uuid: str | None = None

        # 日志配置
        self.console_log_level: str = "INFO"  # 默认console日志等级

    def _init_scheduler(self, scheduler):
        """
        初始化调度器

        Args:
            scheduler: 可以是以下类型之一:
                - None: 使用默认的 FIFO 调度器
                - str: 调度器名称 ("fifo", "load_aware")
                - BaseScheduler 实例: 自定义调度器实例
        """
        from sage.kernel.scheduler.api import BaseScheduler
        from sage.kernel.scheduler.impl import FIFOScheduler, LoadAwareScheduler

        if scheduler is None:
            # 默认使用 FIFO 调度器
            self._scheduler = FIFOScheduler(platform=self.platform)
        elif isinstance(scheduler, str):
            # 字符串指定调度器类型
            scheduler_lower = scheduler.lower()
            if scheduler_lower == "fifo":
                self._scheduler = FIFOScheduler(platform=self.platform)
            elif scheduler_lower in ["load_aware", "loadaware"]:
                self._scheduler = LoadAwareScheduler(platform=self.platform)
            else:
                raise ValueError(
                    f"Unknown scheduler type: {scheduler}. Available options: 'fifo', 'load_aware'"
                )
        elif isinstance(scheduler, BaseScheduler):
            # 直接使用提供的调度器实例
            self._scheduler = scheduler
        else:
            raise TypeError(
                f"scheduler must be None, str, or BaseScheduler instance, got {type(scheduler)}"
            )

    @property
    def scheduler(self):
        """获取当前调度器实例"""
        return self._scheduler

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
        if hasattr(self, "_logger") and self._logger is not None:
            self._logger.update_output_level("console", self.console_log_level)

    def register_service(self, service_name: str, service_class: type, *args, **kwargs):
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
            service_kwargs=kwargs,
        )

        self.service_factories[service_name] = service_factory

        platform_str = "remote" if self.platform == "remote" else "local"
        self.logger.info(
            f"Registered {platform_str} service: {service_name} ({service_class.__name__})"
        )

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

    def from_kafka_source(
        self,
        source_class: type,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        auto_offset_reset: str = "latest",
        value_deserializer: str = "json",
        buffer_size: int = 10000,
        max_poll_records: int = 500,
        **kafka_config,
    ) -> DataStream:
        """
        创建Kafka数据源，采用Flink兼容的架构设计

        Args:
            source_class: Kafka Source 类（需要从 sage.libs.io.source 导入 KafkaSource）
            bootstrap_servers: Kafka集群地址 (例: "localhost:9092")
            topic: Kafka主题名称
            group_id: 消费者组ID，用于offset管理
            auto_offset_reset: offset重置策略 ('latest'/'earliest'/'none')
            value_deserializer: 反序列化方式 ('json'/'string'/'bytes'或自定义函数)
            buffer_size: 本地缓冲区大小，防止数据丢失
            max_poll_records: 每次poll的最大记录数，控制批处理大小
            **kafka_config: 其他Kafka Consumer配置参数

        Returns:
            DataStream: 可用于构建处理pipeline的数据流

        Example:
            # 导入 KafkaSource
            from sage.libs.foundation.io.source import KafkaSource

            # 基本使用
            kafka_stream = env.from_kafka_source(
                KafkaSource,
                bootstrap_servers="localhost:9092",
                topic="user_events",
                group_id="sage_consumer"
            )

            # 高级配置
            kafka_stream = env.from_kafka_source(
                KafkaSource,
                bootstrap_servers="kafka1:9092,kafka2:9092",
                topic="events",
                group_id="sage_app",
                auto_offset_reset="earliest",
                buffer_size=20000,
                max_poll_records=1000,
                session_timeout_ms=30000,
                security_protocol="SSL"
            )

            # 构建处理pipeline
            result = (kafka_stream
                     .map(ProcessEventFunction)
                     .filter(FilterFunction)
                     .sink(OutputSinkFunction))
        """
        # 获取SourceTransformation类
        SourceTransformation = self._get_transformation_classes()["SourceTransformation"]

        # 创建Kafka Source Function
        transformation = SourceTransformation(
            self,
            source_class,
            bootstrap_servers=bootstrap_servers,
            topic=topic,
            group_id=group_id,
            auto_offset_reset=auto_offset_reset,
            value_deserializer=value_deserializer,
            buffer_size=buffer_size,
            max_poll_records=max_poll_records,
            **kafka_config,
        )

        self.pipeline.append(transformation)
        self.logger.info(f"Kafka source created for topic: {topic}, group: {group_id}")

        return self._get_datastream_class()(self, transformation)

    def from_source(self, function: type[BaseFunction] | Callable, *args, **kwargs) -> DataStream:
        if callable(function) and not isinstance(function, type):
            # 这是一个 lambda 函数或普通函数
            function = wrap_lambda(function, "flatmap")

        # 获取SourceTransformation类
        SourceTransformation = self._get_transformation_classes()["SourceTransformation"]
        transformation = SourceTransformation(self, function, *args, **kwargs)

        self.pipeline.append(transformation)
        return self._get_datastream_class()(self, transformation)

    def from_collection(
        self, function: type[BaseFunction] | Callable, *args, **kwargs
    ) -> DataStream:
        if callable(function) and not isinstance(function, type):
            # 这是一个 lambda 函数或普通函数
            function = wrap_lambda(function, "flatmap")

        # 获取BatchTransformation类
        BatchTransformation = self._get_transformation_classes()["BatchTransformation"]
        transformation = BatchTransformation(
            self, function, *args, **kwargs
        )  # TODO: add a new transformation 去告诉engine这个input source是有界的，当执行完毕之后，会发送一个endofinput信号来停止所有进程。
        # Issue URL: https://github.com/intellistream/SAGE/issues/387

        self.pipeline.append(transformation)
        return self._get_datastream_class()(self, transformation)

    def from_batch(self, source: type[BaseFunction] | Any, *args, **kwargs) -> DataStream:
        """
        统一的批处理数据源创建方法，支持多种输入类型

        Args:
            source: 可以是以下类型之一：
                   - BaseFunction 子类：自定义批处理函数类
                   - list/tuple：数据列表或元组
                   - 任何可迭代对象：实现了 __iter__ 的对象
            *args: 传递给批处理函数的位置参数（仅当 source 为函数类时有效）
            **kwargs: 传递给批处理函数的关键字参数，以及 transformation 的配置参数

        Returns:
            DataStream: 包含 BatchTransformation 的数据流

        Example:
            # 1. 使用自定义批处理函数类
            class MyBatchFunction(BaseFunction):
                def get_data_iterator(self):
                    return iter(range(50))

                def get_total_count(self):
                    return 50

            batch_stream = env.from_batch(MyBatchFunction, custom_param="value")

            # 2. 使用数据列表
            data = ["item1", "item2", "item3", "item4", "item5"]
            batch_stream = env.from_batch(data)

            # 3. 使用任何可迭代对象
            batch_stream = env.from_batch({1, 2, 3, 4, 5})
            batch_stream = env.from_batch("hello")  # 逐字符迭代
            batch_stream = env.from_batch(range(100))

            # 4. 配置额外参数
            batch_stream = env.from_batch(data, progress_log_interval=10)
        """

        # 检查 source 的类型并相应处理
        if isinstance(source, type) and hasattr(source, "__bases__"):
            # source 是一个类，检查是否是 BaseFunction 的子类
            from sage.common.core import BaseFunction

            if issubclass(source, BaseFunction):
                # 使用自定义批处理函数类
                return self._from_batch_function_class(source, *args, **kwargs)

        # source 是数据对象，需要检查其类型
        if isinstance(source, (list, tuple)):
            # 处理列表或元组
            return self._from_batch_collection(source, **kwargs)
        elif hasattr(source, "__iter__") and not isinstance(source, (str, bytes)):
            # 处理其他可迭代对象（排除字符串和字节）
            return self._from_batch_iterable(source, **kwargs)
        elif isinstance(source, (str, bytes)):
            # 特殊处理字符串和字节，按字符/字节迭代
            return self._from_batch_iterable(source, **kwargs)
        else:
            # 尝试将其作为可迭代对象处理
            try:
                iter(source)  # type: ignore[arg-type]
                return self._from_batch_iterable(source, **kwargs)
            except TypeError:
                raise TypeError(
                    f"Unsupported source type: {type(source)}. "
                    f"Expected BaseFunction subclass, list, tuple, or any iterable object."
                )

    def from_future(self, name: str) -> DataStream:
        """
        创建一个future stream占位符，用于建立反馈边。

        Args:
            name: future stream的名称，用于标识和调试

        Returns:
            DataStream: 包含FutureTransformation的数据流

        Example:
            future_stream = env.from_future("feedback_loop")
            # 使用future_stream参与pipeline构建
            result = source.connect(future_stream).comap(CombineFunction)
            # 最后填充future
            result.fill_future(future_stream)
        """
        # 获取FutureTransformation类
        FutureTransformation = self._get_transformation_classes()["FutureTransformation"]
        transformation = FutureTransformation(self, name)
        self.pipeline.append(transformation)
        return self._get_datastream_class()(self, transformation)

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
    def client(self) -> JobManagerClient:
        if self._engine_client is None:
            # 从配置中获取 Engine 地址，或使用默认值
            daemon_host = self.config.get("engine_host", "127.0.0.1")
            daemon_port = self.config.get("engine_port", 19000)

            self._engine_client = JobManagerClient(host=daemon_host, port=daemon_port)

        return self._engine_client

    ########################################################
    #                auxiliary methods                     #
    ########################################################

    def _append(self, transformation: BaseTransformation):
        """将 BaseTransformation 添加到管道中（Compiler 会使用）。"""
        self.pipeline.append(transformation)
        return self._get_datastream_class()(self, transformation)

    def _from_batch_function_class(
        self, batch_function_class: type[BaseFunction], *args, **kwargs
    ) -> DataStream:
        """
        从自定义批处理函数类创建批处理数据源
        """
        # 分离transformation配置和function参数
        transform_kwargs = {}
        function_kwargs = {}

        # transformation相关的参数
        transform_config_keys = {"delay", "progress_log_interval"}

        for key, value in kwargs.items():
            if key in transform_config_keys:
                transform_kwargs[key] = value
            else:
                function_kwargs[key] = value

        # 获取BatchTransformation类
        BatchTransformation = self._get_transformation_classes()["BatchTransformation"]
        transformation = BatchTransformation(
            self, batch_function_class, *args, **function_kwargs, **transform_kwargs
        )

        self.pipeline.append(transformation)
        self.logger.info(f"Custom batch source created with {batch_function_class.__name__}")

        return self._get_datastream_class()(self, transformation)

    def _from_batch_collection(self, data: list | tuple, **kwargs) -> DataStream:
        """
        从数据集合创建批处理数据源
        """
        from sage.kernel.api.function.simple_batch_function import (
            SimpleBatchIteratorFunction,
        )

        # 获取BatchTransformation类
        BatchTransformation = self._get_transformation_classes()["BatchTransformation"]
        transformation = BatchTransformation(self, SimpleBatchIteratorFunction, data=data, **kwargs)

        self.pipeline.append(transformation)
        self.logger.info(f"Batch collection source created with {len(data)} items")

        return self._get_datastream_class()(self, transformation)

    def _from_batch_iterable(self, iterable: Any, **kwargs) -> DataStream:
        """
        从任何可迭代对象创建批处理数据源
        """
        from sage.kernel.api.function.simple_batch_function import (
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

        # 获取BatchTransformation类
        BatchTransformation = self._get_transformation_classes()["BatchTransformation"]
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

        return self._get_datastream_class()(self, transformation)
