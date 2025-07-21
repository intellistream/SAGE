from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
import os
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING
import sage_memory.api
from sage_core.api.datastream import DataStream
from sage_core.transformation.base_transformation import BaseTransformation
from sage_core.transformation.source_transformation import SourceTransformation
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
        self.runtime_context = dict  # 需要在compiler里面实例化。
        self.memory_collection = None  # 用于存储内存集合
        self.is_running = False

        # JobManager 相关
        self._jobmanager: Optional[ActorWrapper] = None
        
        # Engine 客户端相关
        self._engine_client: EngineClient = None
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
        # 序列化环境
        from sage_utils.serialization.dill_serializer import serialize_object
        serialized_env = serialize_object(self)
        
        # 通过jobmanager属性提交job
        env_uuid = self.jobmanager.submit_job(serialized_env)
        
        if env_uuid:
            self.env_uuid = env_uuid
            self.logger.info(f"Environment submitted with UUID: {self.env_uuid}")
        else:
            raise RuntimeError("Failed to submit environment: no UUID returned")

    def stop(self):
        """停止管道运行"""
        if not self.env_uuid:
            self.logger.warning("Environment not submitted, nothing to stop")
            return
        
        self.logger.info("Stopping pipeline...")
        
        try:
            response = self.jobmanager.stop_job(self.env_uuid)
            
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
            response = self.jobmanager.stop_job(self.env_uuid)
            
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

    @abstractmethod
    @property
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