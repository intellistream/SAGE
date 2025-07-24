from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
import os
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING, Type, Union, Any
from sage_core.function.base_function import BaseFunction
from sage_core.function.lambda_function import wrap_lambda
import sage_memory.api
from sage_core.api.datastream import DataStream
from sage_core.transformation.base_transformation import BaseTransformation
from sage_core.transformation.source_transformation import SourceTransformation
from sage_core.transformation.batch_transformation import BatchTransformation
from sage_core.transformation.future_transformation import FutureTransformation
from sage_utils.custom_logger import CustomLogger
from sage_jobmanager.utils.name_server import get_name
from sage_core.jobmanager_client import JobManagerClient
from sage_utils.actor_wrapper import ActorWrapper
if TYPE_CHECKING:
    from sage_jobmanager.job_manager import JobManager

class BaseEnvironment(ABC):

    __state_exclude__ = ["_engine_client", "client", "jobmanager"]
    # 会被继承，但是不会被自动合并

    def __init__(self, name: str, config: dict | None, *, platform: str = "local"):

        self.name = get_name(name)
        self.uuid: Optional[str] # 由jobmanager生成

        self.config: dict = dict(config or {})
        self.platform:str = platform
        # 用于收集所有 BaseTransformation，供 ExecutionGraph 构建 DAG
        self.pipeline: List[BaseTransformation] = []
        self._filled_futures: dict = {}  # 记录已填充的future stream信息：name -> {future_transformation, actual_transformation, filled_at}
        self.ctx = dict  # 需要在compiler里面实例化。
        self.memory_collection = None  # 用于存储内存集合
        self.is_running = False
        self.env_base_dir: Optional[str] = None  # 环境基础目录，用于存储日志和其他文件
        # JobManager 相关
        self._jobmanager: Optional[ActorWrapper] = None
        
        # Engine 客户端相关
        self._engine_client: Optional[JobManagerClient] = None
        self.env_uuid: Optional[str] = None

    ########################################################
    #                  user interface                      #
    ########################################################

    def set_memory(self, config = None):
        self.memory_collection = sage_memory.api.get_memory(config=config, remote=(self.platform != "local"), env_name=self.name)



    def from_kafka_source(self, 
                         bootstrap_servers: str,
                         topic: str,
                         group_id: str,
                         auto_offset_reset: str = 'latest',
                         value_deserializer: str = 'json',
                         buffer_size: int = 10000,
                         max_poll_records: int = 500,
                         **kafka_config) -> DataStream:
        """
        创建Kafka数据源，采用Flink兼容的架构设计
        
        Args:
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
            # 基本使用
            kafka_stream = env.from_kafka_source(
                bootstrap_servers="localhost:9092",
                topic="user_events", 
                group_id="sage_consumer"
            )
            
            # 高级配置
            kafka_stream = env.from_kafka_source(
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
        from sage_core.function.kafka_source import KafkaSourceFunction
        
        # 创建Kafka Source Function
        transformation = SourceTransformation(
            self,
            KafkaSourceFunction,
            bootstrap_servers=bootstrap_servers,
            topic=topic,
            group_id=group_id,
            auto_offset_reset=auto_offset_reset,
            value_deserializer=value_deserializer,
            buffer_size=buffer_size,
            max_poll_records=max_poll_records,
            **kafka_config
        )
        
        self.pipeline.append(transformation)
        self.logger.info(f"Kafka source created for topic: {topic}, group: {group_id}")
        
        return DataStream(self, transformation)

    def from_source(self, function: Union[Type[BaseFunction], callable], *args, **kwargs) -> DataStream:
        if callable(function) and not isinstance(function, type):
            # 这是一个 lambda 函数或普通函数
            function = wrap_lambda(function, 'flatmap')
        transformation = SourceTransformation(self, function, *args, **kwargs)

        self.pipeline.append(transformation)
        return DataStream(self, transformation)



    def from_collection(self, function: Union[Type[BaseFunction], callable], *args, **kwargs) -> DataStream:
        if callable(function) and not isinstance(function, type):
            # 这是一个 lambda 函数或普通函数
            function = wrap_lambda(function, 'flatmap')
        transformation = SourceTransformation(self, function, *args,
                                              **kwargs)  # TODO: add a new transformation 去告诉engine这个input source是有界的，当执行完毕之后，会发送一个endofinput信号来停止所有进程。

        self.pipeline.append(transformation)
        return DataStream(self, transformation)

    def from_batch_collection(self, data: list, **kwargs) -> DataStream:
        """
        从数据集合创建批处理数据源，引擎会自动判断批次大小
        
        Args:
            data: 要处理的数据列表
            **kwargs: 其他配置参数，如progress_log_interval等
            
        Returns:
            DataStream: 包含BatchTransformation的数据流
            
        Example:
            # 处理简单数据列表
            data = ["item1", "item2", "item3", "item4", "item5"]
            batch_stream = env.from_batch_collection(data)
            
            # 配置进度日志间隔
            batch_stream = env.from_batch_collection(
                data, 
                progress_log_interval=10
            )
        """
        from sage_core.function.simple_batch_function import SimpleBatchIteratorFunction
        
        transformation = BatchTransformation(
            self,
            SimpleBatchIteratorFunction,
            data=data,
            **kwargs
        )
        
        self.pipeline.append(transformation)
        self.logger.info(f"Batch collection source created with {len(data)} items")
        
        return DataStream(self, transformation)

    def from_batch_file(self, file_path: str, encoding: str = 'utf-8', **kwargs) -> DataStream:
        """
        从文件创建批处理数据源，引擎会自动统计行数并判断批次大小
        
        Args:
            file_path: 文件路径
            encoding: 文件编码，默认为utf-8
            **kwargs: 其他配置参数，如progress_log_interval等
            
        Returns:
            DataStream: 包含BatchTransformation的数据流
            
        Example:
            # 处理文本文件
            batch_stream = env.from_batch_file("/path/to/data.txt")
            
            # 指定编码和进度间隔
            batch_stream = env.from_batch_file(
                "/path/to/data.txt",
                encoding="gb2312",
                progress_log_interval=1000
            )
        """
        from sage_core.function.simple_batch_function import FileBatchIteratorFunction
        
        transformation = BatchTransformation(
            self,
            FileBatchIteratorFunction,
            file_path=file_path,
            encoding=encoding,
            **kwargs
        )
        
        self.pipeline.append(transformation)
        self.logger.info(f"Batch file source created for: {file_path}")
        
        return DataStream(self, transformation)

    def from_batch_range(self, start: int, end: int, step: int = 1, **kwargs) -> DataStream:
        """
        从数字范围创建批处理数据源，引擎会自动计算范围大小
        
        Args:
            start: 起始数字
            end: 结束数字(不包含)
            step: 步长，默认为1
            **kwargs: 其他配置参数，如progress_log_interval等
            
        Returns:
            DataStream: 包含BatchTransformation的数据流
            
        Example:
            # 生成1到1000的数字
            batch_stream = env.from_batch_range(1, 1001)
            
            # 生成偶数序列
            batch_stream = env.from_batch_range(0, 100, step=2)
        """
        from sage_core.function.simple_batch_function import RangeBatchIteratorFunction
        
        transformation = BatchTransformation(
            self,
            RangeBatchIteratorFunction,
            start=start,
            end=end,
            step=step,
            **kwargs
        )
        
        total_count = max(0, (end - start + step - 1) // step)
        self.pipeline.append(transformation)
        self.logger.info(f"Batch range source created: {start}-{end} (step={step}, total={total_count})")
        
        return DataStream(self, transformation)

    def from_batch_generator(self, generator_func: callable, total_count: int = None, **kwargs) -> DataStream:
        """
        从生成器函数创建批处理数据源
        
        Args:
            generator_func: 数据生成器函数，应该返回Iterator[Any]
            total_count: 预期生成的总数量（可选）
            **kwargs: 其他配置参数，如progress_log_interval等
            
        Returns:
            DataStream: 包含BatchTransformation的数据流
            
        Example:
            # 斐波那契数列生成器
            def fibonacci_generator():
                a, b = 0, 1
                for _ in range(100):
                    yield a
                    a, b = b, a + b
            
            batch_stream = env.from_batch_generator(fibonacci_generator, 100)
        """
        from sage_core.function.simple_batch_function import GeneratorBatchIteratorFunction
        
        transformation = BatchTransformation(
            self,
            GeneratorBatchIteratorFunction,
            generator_func=generator_func,
            total_count=total_count,
            **kwargs
        )
        
        self.pipeline.append(transformation)
        total_info = f" with {total_count} expected items" if total_count else ""
        self.logger.info(f"Batch generator source created{total_info}")
        
        return DataStream(self, transformation)

    def from_batch_iterable(self, iterable: Any, total_count: int = None, **kwargs) -> DataStream:
        """
        从任何可迭代对象创建批处理数据源
        
        Args:
            iterable: 任何实现了__iter__的对象
            total_count: 总数量（可选，如果不提供会尝试自动获取）
            **kwargs: 其他配置参数，如progress_log_interval等
            
        Returns:
            DataStream: 包含BatchTransformation的数据流
            
        Example:
            # 从集合创建
            batch_stream = env.from_batch_iterable({1, 2, 3, 4, 5})
            
            # 从字符串创建（逐字符）
            batch_stream = env.from_batch_iterable("hello")
            
            # 从任何可迭代对象创建
            batch_stream = env.from_batch_iterable(my_custom_iterable)
        """
        from sage_core.function.simple_batch_function import IterableBatchIteratorFunction
        
        transformation = BatchTransformation(
            self,
            IterableBatchIteratorFunction,
            iterable=iterable,
            total_count=total_count,
            **kwargs
        )
        
        self.pipeline.append(transformation)
        self.logger.info(f"Batch iterable source created from {type(iterable).__name__}")
        
        return DataStream(self, transformation)

    def from_batch_custom(self, batch_function_class: Type['BaseFunction'], *args, **kwargs) -> DataStream:
        """
        从自定义批处理函数创建批处理数据源
        
        Args:
            batch_function_class: 自定义函数类，需要实现get_data_iterator方法
            *args: 传递给批处理函数的位置参数
            **kwargs: 传递给批处理函数的关键字参数，以及transformation的配置参数
            
        Returns:
            DataStream: 包含BatchTransformation的数据流
            
        Example:
            class MyBatchFunction(BaseFunction):
                def get_data_iterator(self):
                    return iter(range(50))
                
                def get_total_count(self):  # 可选
                    return 50
            
            batch_stream = env.from_batch_custom(MyBatchFunction)
        """
        # 分离transformation配置和function参数
        transform_kwargs = {}
        function_kwargs = {}
        
        # transformation相关的参数
        transform_config_keys = {'delay', 'progress_log_interval'}
        
        for key, value in kwargs.items():
            if key in transform_config_keys:
                transform_kwargs[key] = value
            else:
                function_kwargs[key] = value
        
        transformation = BatchTransformation(
            self,
            batch_function_class,
            *args,
            **function_kwargs,
            **transform_kwargs
        )
        
        self.pipeline.append(transformation)
        self.logger.info(f"Custom batch source created with {batch_function_class.__name__}")
        
        return DataStream(self, transformation)


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
        transformation = FutureTransformation(self, name)
        self.pipeline.append(transformation)
        return DataStream(self, transformation)

    ########################################################
    #                jobmanager interface                  #
    ########################################################
    @abstractmethod
    def submit(self):
        pass

    def stop(self):
        """停止管道运行"""
        if not self.env_uuid:
            self.logger.warning("Environment not submitted, nothing to stop")
            return
        
        self.logger.info("Stopping pipeline...")
        
        try:
            response = self.jobmanager.pause_job(self.env_uuid)
            
            if response.get("status") == "success":
                self.is_running = False
                self.logger.info("Pipeline stopped successfully")
            else:
                self.logger.warning(f"Failed to stop pipeline: {response.get('message')}")
        except Exception as e:
            self.logger.error(f"Error stopping pipeline: {e}")

    def close(self):
        """关闭管道运行"""
        if not self.env_uuid:
            self.logger.warning("Environment not submitted, nothing to close")
            return
        
        self.logger.info("Closing environment...")
        
        try:
            response = self.jobmanager.pause_job(self.env_uuid)
            
            if response.get("status") == "success":
                self.logger.info("Environment closed successfully")
            else:
                self.logger.warning(f"Failed to close environment: {response.get('message')}")
                
        except Exception as e:
            self.logger.error(f"Error closing environment: {e}")
        finally:
            # 清理本地资源
            self.is_running = False
            self.env_uuid = None
            
            # 清理管道
            self.pipeline.clear()

    ########################################################
    #                properties                            #
    ########################################################

    @property
    def logger(self):
        if not hasattr(self, "_logger"):
            self._logger = CustomLogger()
        return self._logger

    @property
    def client(self)-> JobManagerClient:
        if self._engine_client is None:
            # 从配置中获取 Engine 地址，或使用默认值
            daemon_host = self.config.get("engine_host", "127.0.0.1")
            daemon_port = self.config.get("engine_port", 19000)
            
            self._engine_client = JobManagerClient(host=daemon_host, port=daemon_port)
            
        return self._engine_client


    @property
    @abstractmethod
    def jobmanager(self) -> 'JobManager':
        return
        # """获取JobManager句柄，通过ActorWrapper封装以提供透明调用"""
        # if self._jobmanager is None:
        #     self._jobmanager = self.client.get_actor_handle()
        # return self._jobmanager



    ########################################################
    #                auxiliary methods                     #
    ########################################################

    def _append(self, transformation: BaseTransformation):
        """将 BaseTransformation 添加到管道中（Compiler 会使用）。"""
        self.pipeline.append(transformation)
        return DataStream(self, transformation)

    def setup_logging_system(self, log_base_dir: str): 
        # this method is called by jobmanager when receiving the job, not the user
        self.session_timestamp = datetime.now()
        self.session_id = self.session_timestamp.strftime("%Y%m%d_%H%M%S")
        # self.log_base_dir = log_base_dir
        self.env_base_dir = os.path.join(log_base_dir, f"env_{self.name}_{self.session_id}")
        Path(self.env_base_dir).mkdir(parents=True, exist_ok=True)

        self._logger = CustomLogger([
                ("console", "INFO"),  # 控制台显示重要信息
                (os.path.join(self.env_base_dir, "Environment.log"), "DEBUG"),  # 详细日志
                (os.path.join(self.env_base_dir, "Error.log"), "ERROR")  # 错误日志
            ],
            name = f"Environment_{self.name}",
        )