from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any

# from sage.api.env import StreamingExecutionEnvironment
from sage.core.operator.base_operator import BaseOperator
from sage.core.operator.transformation import TransformationType, Transformation
from sage.api.base_function import BaseFunction
    
class DataStream:

    def __init__(self,
        env, 
        transform: Transformation
    ):
        self._environment = env
        self._transformation:Transformation = transform

    # ---------------------------------------------------------------------
    # 内部帮助：把新 Transformation 接入管线
    # ---------------------------------------------------------------------
    def _apply(self, tr: Transformation) -> "DataStream":
        tr.add_upstream(self._transformation)
        self._environment._pipeline.append(tr)          # 环境收集所有变换
        return DataStream(self._environment, tr)

    def map(self, function: Union[BaseFunction, Type[BaseFunction] ],*args, **kwargs) -> "DataStream":
        tr = Transformation(TransformationType.MAP, function,*args, **kwargs)
        return self._apply(tr)

    def sink(self, function: Union[BaseFunction, Type[BaseFunction] ],*args, **kwargs) -> "DataStream":
        tr = Transformation(TransformationType.SINK, function,*args, **kwargs)
        return self._apply(tr)
