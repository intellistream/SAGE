from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any, TYPE_CHECKING, List
import pip
from sage.api.datastream import DataStream
from sage.api.base_function import BaseFunction
from sage.core.operator.base_operator import BaseOperator
from sage.core.operator.transformation import TransformationType, Transformation

# from sage.core.graph.sage_graph import SageGraph

class StreamingExecutionEnvironment:
    def __init__(self,name:str = "default_environment", config: dict = {}):
        self.name = name
        self.config = config
        self._pipeline: List[Transformation] = []   # Transformation DAG

    def from_source(self, function: Union[BaseFunction, Type[BaseFunction]],*args,  **kwargs: Any) -> DataStream:
        """用户 API：声明一个数据源并返回 DataStream 起点。"""
        transformation = Transformation(TransformationType.SOURCE, function,*args,  **kwargs)
        self._pipeline.append(transformation)
        return DataStream(self, transformation)

    def execute(self):
        from sage.core.engine import Engine
        engine = Engine.get_instance()
        engine.submit_env(self)

    @property
    def pipeline(self) -> List[Transformation]:  # noqa: D401
        """返回 Transformation 列表（Compiler 会使用）。"""
        return self._pipeline