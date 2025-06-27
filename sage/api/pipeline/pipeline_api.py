from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any, TYPE_CHECKING
import pip
from sage.api.pipeline.datastream_api import DataStream
from sage.api.operator import SourceFunction
from sage.api.operator.base_operator_api import BaseFunction
# from sage.core.graph.sage_graph import SageGraph

class Pipeline:
    name:str
    operators: list[Union[BaseFunction, Type[BaseFunction] ]]
    data_streams: list[DataStream]
    operator_config: dict
    operator_cls_mapping: dict
    # operator_factory: OperatorFactory
    # use_ray: bool
    # compiler: QueryCompiler
    def __init__(self, name: str):
        self.name = name
        self.operators = []
        self.data_streams = []
        self.operator_config = {}
        self.operator_cls_mapping = {}
        self.use_ray = False  # 是否使用 Ray 运行时，默认为 False
        # 创建全局算子工厂
        # self.operator_factory = OperatorFactory(self.use_ray)


    def _register_operator(self, operator):
        self.operators.append(operator)

    def add_source(self,source: Union[Type[SourceFunction], SourceFunction], config:dict = {}) -> DataStream:
        """
        添加数据源，自动根据运行时配置创建合适的实例
        
        Args:
            source_class: 算子类（如 FileSource）
            config: 算子配置
        
        Returns:
            DataStream: 数据流对象
        """
        if(isinstance(source, SourceFunction)):
            config.update(source.config)  # 如果是实例，继承其配置
        # 使用工厂创建算子实例
        # operator_wrapper = self.operator_factory.create(source_class, config)
        stream = DataStream(source, self, "source", config, "source")
        self.data_streams.append(stream)
        return stream

    def stop(self):
        from sage.core.engine import Engine
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
        # self.operator_factory = OperatorFactory(runtime_config)

    # def submit(self, config=None, generate_func=None):
    #     from sage.core.engine import Engine
    #     engine = Engine.get_instance(generate_func)
    #     print(f"[Pipeline] Pipeline '{self.name}'submitted to engine.")
    #     engine.submit_pipeline(self, config, generate_func)

    def submit(self, config=None):
        from sage.core.engine import Engine
        engine = Engine.get_instance()
        print(f"[Pipeline] Pipeline '{self.name}'submitted to engine.")
        engine.submit_mixed_pipeline(self, config)

    def get_graph_preview(self) -> dict:
        """
        获取 pipeline 转换为 graph 后的预览信息，不实际提交
        
        Returns:
            dict: 图的结构信息
        """
        try:
            graph = self.to_graph()
            return graph.get_graph_info()
        except Exception as e:
            return {"error": str(e)}