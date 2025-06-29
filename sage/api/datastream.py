from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any

# from sage.api.env import StreamingExecutionEnvironment
from sage.api.base_operator import BaseOperator
from sage.api.base_function import BaseFunction
from sage.api.transformation import TransformationType, BaseTransformation
    
class DataStream:

    def __init__(self,
        env, 
        transform: BaseTransformation
    ):
        self._environment = env
        self._transformation:BaseTransformation = transform

    # ---------------------------------------------------------------------
    # 内部帮助：把新 Transformation 接入管线
    # ---------------------------------------------------------------------
    def _apply(self, tr: BaseTransformation) -> "DataStream":
        tr.add_upstream(self._transformation)
        self._environment._pipeline.append(tr)          # 环境收集所有变换
        return DataStream(self._environment, tr)

    def map(self, function: Union[BaseFunction, Type[BaseFunction] ],*args, **kwargs) -> "DataStream":
        tr = BaseTransformation(TransformationType.MAP, function,*args, **kwargs)
        return self._apply(tr)

    def sink(self, function: Union[BaseFunction, Type[BaseFunction] ],*args, **kwargs) -> "DataStream":
        tr = BaseTransformation(TransformationType.SINK, function,*args, **kwargs)
        return self._apply(tr)
