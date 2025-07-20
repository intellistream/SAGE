from __future__ import annotations
from typing import Type, Union
from sage_core.function.base_function import BaseFunction
from sage_core.api.datastream import DataStream
from sage_core.transformation.source_transformation import SourceTransformation
from sage_core.function.lambda_function import wrap_lambda

from sage_core.environment.base_environment import BaseEnvironment


class BatchEnvironment(BaseEnvironment):
    def from_collection(self, function: Union[Type[BaseFunction], callable], *args, **kwargs) -> DataStream:
        if callable(function) and not isinstance(function, type):
            # 这是一个 lambda 函数或普通函数
            function = wrap_lambda(function, 'flatmap')
        transformation = SourceTransformation(self, function, *args,
                                              **kwargs)  # TODO: add a new transformation 去告诉engine这个input source是有界的，当执行完毕之后，会发送一个endofinput信号来停止所有进程。

        self._pipeline.append(transformation)
        return DataStream(self, transformation)
