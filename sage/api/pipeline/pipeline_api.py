from typing import Type
from sage.core.engine.runtime import Engine
from sage.api.pipeline.datastream_api import DataStream
from sage.runtime.operator_factory import OperatorFactory
from sage.api.operator import SourceFunction

class Pipeline:
    def __init__(self, name: str, use_ray: bool = True):
        self.name = name
        self.operators = []
        self.data_streams = []
        self.operator_config = {}
        self.operator_cls_mapping = {}
        
        # 创建全局算子工厂
        self.operator_factory = OperatorFactory(use_ray=use_ray)


    def _register_operator(self, operator):
        self.operators.append(operator)

    def add_source(self,source_class: Type[SourceFunction], config:dict) -> DataStream:
        """
        添加数据源，自动根据运行时配置创建合适的实例
        
        Args:
            source_class: 算子类（如 FileSource）
            config: 算子配置
        
        Returns:
            DataStream: 数据流对象
        """
        # 使用工厂创建算子实例
        source_instance = self.operator_factory.create(source_class, config)

        stream = DataStream(operator=source_instance, pipeline=self, name="source")
        self.data_streams.append(stream)
        return stream

    def submit(self, config=None,generate_func = None):
        """
        Submit the pipeline to the SAGE engine.
        The engine is responsible for compiling and executing the DAG.

        Args:
            config (dict, optional): Configuration options for runtime execution.
                Example:
                {
                    "is_long_running": True,
                    "duration": 1,
                    "frequency": 30
                }
                :param generate_func:
        """

        engine = Engine.get_instance(generate_func) # client side
        engine.submit_pipeline(self, config=config or {}) # compile dag -> register engine
        print(f"[Pipeline] Pipeline '{self.name}' submitted to engine with config: {config or {}}")

    def stop(self):
        engine= Engine.get_instance() # client side
        engine.stop_pipeline(self) # stop the pipeline
        print(f"[Pipeline] Pipeline '{self.name}' stopped.")

    def add_operator_config(self, config):
        self.operator_config.update(config)

    def add_operator_cls(self, operator_cls):
        self.operator_cls_mapping.update(operator_cls)

    def get_operator_cls(self):
        return self.operator_cls_mapping

    def get_operator_config(self):
        return self.operator_config

    def _merge_configs(self, operator_config):
        """合并全局配置和算子特定配置"""
        merged = {}
        merged.update(self.operator_config)  # 全局算子配置
        merged.update({"runtime": self.runtime_config})  # 运行时配置
        if operator_config:
            merged.update(operator_config)  # 算子特定配置
        return merged
    def set_runtime_config(self, runtime_config: dict):
        """动态设置运行时配置"""
        self.runtime_config = runtime_config
        self.operator_factory = OperatorFactory(runtime_config)