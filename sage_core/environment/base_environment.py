from __future__ import annotations

import time
from typing import Type, Union, Any, List, Optional
from enum import Enum
import sage_memory.api
from sage_core.function.base_function import BaseFunction
from sage_core.api.datastream import DataStream
from sage_core.transformation.base_transformation import BaseTransformation
from sage_core.transformation.source_transformation import SourceTransformation
from sage_core.transformation.future_transformation import FutureTransformation
from sage_utils.custom_logger import CustomLogger
from sage_utils.name_server import get_name
from sage_core.function.lambda_function import wrap_lambda
from sage_core.client import EngineClient


class BaseEnvironment:

    def __init__(self, name: str, config: dict | None, *, platform: str = "local"):

        self.__state_exclude__ = ["_engine_client", "client", "jobmanager"]

        self.name = get_name(name)
        

        self.config: dict = dict(config or {})
        self.platform:str = platform
        # 用于收集所有 BaseTransformation，供 ExecutionGraph 构建 DAG
        self._pipeline: List[BaseTransformation] = []
        self._filled_futures: dict = {}  # 记录已填充的future stream信息：name -> {future_transformation, actual_transformation, filled_at}
        self.runtime_context = dict  # 需要在compiler里面实例化。
        self.memory_collection = None  # 用于存储内存集合
        self.is_running = False

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
        
        self._pipeline.append(transformation)
        self.logger.info(f"Kafka source created for topic: {topic}, group: {group_id}")
        
        return DataStream(self, transformation)

    def from_source(self, function: Union[Type[BaseFunction], callable], *args, **kwargs) -> DataStream:
        if callable(function) and not isinstance(function, type):
            # 这是一个 lambda 函数或普通函数
            function = wrap_lambda(function, 'flatmap')
        transformation = SourceTransformation(self, function, *args,**kwargs)
        
        self._pipeline.append(transformation)
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
        self._pipeline.append(transformation)
        return DataStream(self, transformation)

    ########################################################
    #                engine interface                      #
    ########################################################

    def submit(self, name="example_pipeline"):
        """提交环境到 Engine"""
        
        # 序列化环境
        from sage_utils.dill_serializer import serialize_object
        serialized_env = serialize_object(self)
        
        # 发送提交请求
        response = self.client.send_message(
            message_type="env_submit",
            env_name=self.name,
            payload={"serialized_env": serialized_env}
        )
        
        if response["status"] == "success":
            self.env_uuid = response["env_uuid"]
            self.logger.info(f"Environment submitted with UUID: {self.env_uuid}")
        else:
            raise RuntimeError(f"Failed to submit environment: {response['message']}")

    # def run_once(self, node: str = None):
    #     """运行一次管道，适用于测试或调试"""
    #     if self.is_running:
    #         self.logger.warning("Pipeline is already running.")
    #         return
            
    #     if not self.env_uuid:
    #         raise RuntimeError("Environment not submitted yet. Call submit() first.")
        
    #     response = self.client.send_message(
    #         message_type="env_run_once",
    #         env_name=self.name,
    #         env_uuid=self.env_uuid,
    #         payload={"node": node}
    #     )
        
    #     if response["status"] != "success":
    #         raise RuntimeError(f"Failed to run once: {response['message']}")
        
    #     self.logger.info("Pipeline executed once successfully")

    # def run_streaming(self, node: str = None):
    #     """运行管道，适用于生产环境"""
    #     if not self.env_uuid:
    #         raise RuntimeError("Environment not submitted yet. Call submit() first.")
        
    #     response = self.client.send_message(
    #         message_type="env_run_streaming",
    #         env_name=self.name,
    #         env_uuid=self.env_uuid,
    #         payload={"node": node}
    #     )
        
    #     if response["status"] != "success":
    #         raise RuntimeError(f"Failed to run streaming: {response['message']}")
        
    #     self.is_running = True
    #     self.logger.info("Pipeline streaming started successfully")

    def stop(self):
        """停止管道运行"""
        if not self.env_uuid:
            self.logger.warning("Environment not submitted, nothing to stop")
            return
        
        self.logger.info("Stopping pipeline...")
        
        try:
            response = self.client.send_message(
                message_type="env_stop",
                env_name=self.name,
                env_uuid=self.env_uuid,
                payload={}
            )
            
            if response["status"] == "success":
                self.is_running = False
                self.logger.info("Pipeline stopped successfully")
            else:
                self.logger.warning(f"Failed to stop pipeline: {response['message']}")
        except Exception as e:
            self.logger.error(f"Error stopping pipeline: {e}")

    def close(self):
        """关闭管道运行"""
        if not self.env_uuid:
            self.logger.warning("Environment not submitted, nothing to close")
            return
        
        self.logger.info("Closing environment...")
        
        try:
            response = self.client.send_message(
                message_type="env_close",
                env_name=self.name,
                env_uuid=self.env_uuid,
                payload={}
            )
            
            if response["status"] == "success":
                self.logger.info("Environment closed successfully")
            else:
                self.logger.warning(f"Failed to close environment: {response['message']}")
                
        except Exception as e:
            self.logger.error(f"Error closing environment: {e}")
        finally:
            # 清理本地资源
            self.is_running = False
            self.env_uuid = None
            
            # 断开客户端连接
            self.client.disconnect()
            self._client = None
            
            # 清理管道
            self._pipeline.clear()

    ########################################################
    #                properties                            #
    ########################################################

    @property
    def logger(self):
        if not hasattr(self, "_logger"):
            self._logger = CustomLogger(
            filename=f"Environment_{self.name}",
            env_name = self.name,
            console_output="WARNING", 
            file_output=True,
            global_output = "DEBUG",
        )
        return self._logger

    @property
    def client(self)-> EngineClient:
        if self._engine_client is None:
            # 从配置中获取 Engine 地址，或使用默认值
            engine_host = self.config.get("engine_host", "127.0.0.1")
            engine_port = self.config.get("engine_port", 19000)
            
            self._engine_client = EngineClient(host=engine_host, port=engine_port)
            
        return self._engine_client


    ########################################################
    #                auxiliary methods                     #
    ########################################################

    def _append(self, transformation: BaseTransformation):
        """将 BaseTransformation 添加到管道中（Compiler 会使用）。"""
        self.pipeline.append(transformation)
        return DataStream(self, transformation)
    
    @property
    def pipeline(self) -> List[BaseTransformation]:  # noqa: D401
        """返回 BaseTransformation 列表（Compiler 会使用）。"""
        return self._pipeline





