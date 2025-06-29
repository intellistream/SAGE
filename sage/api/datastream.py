from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any

from sage.api.env import StreamingExecutionEnvironment
from sage.api.base_operator import BaseOperator
from sage.api.base_function import BaseFunction
from sage.api.transformation import TransformationType, BaseTransformation
from sage.api.env import StreamingExecutionEnvironment

    
class DataStream:

    def __init__(self,
        env:StreamingExecutionEnvironment, 
        transform: BaseTransformation
    ):
        self._environment = env
        self._transformation:BaseTransformation = transform

    # ---------------------------------------------------------------------
    # 内部帮助：把新 Transformation 接入管线
    # ---------------------------------------------------------------------
    def _apply(self, tr: BaseTransformation) -> "DataStream":
        tr.add_upstream(self._transformation)
        self._environment.pipeline.append(tr)          # 环境收集所有变换
        return DataStream(self._env, tr)

    def map(self, function: Union[BaseFunction, Type[BaseFunction] ], **kwargs) -> "DataStream":
        tr = BaseTransformation(TransformationType.MAP, function, **kwargs)
        return self._apply(tr)

    def sink(self, function: Union[BaseFunction, Type[BaseFunction] ], **kwargs) -> "DataStream":
        tr = BaseTransformation(TransformationType.SINK, function, **kwargs)
        return self._apply(tr)
