from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any, List

# from sage.api.env import Environment
from sage_core.core.operator.base_operator import BaseOperator
from sage_core.core.operator.transformation import TransformationType, Transformation
from sage_core.api.base_function import BaseFunction
    
class DataStream:
    # 表示多个transformation生成的流结果
    def __init__(self, 
                 env, 
                 transformations: Union["Transformation", List["Transformation"]]):
        self._environment = env

        if isinstance(transformations, list):
            self.transformations: List[Transformation] = transformations
        else:
            self.transformations: List[Transformation] = [transformations]

    # ---------------------------------------------------------------------
    # 内部帮助：把新 Transformation 接入管线
    # ---------------------------------------------------------------------
    def _apply(self, tr: Transformation) -> "DataStream":
        for transformation in self.transformations:
            tr.add_upstream(transformation)
        
        self._environment._pipeline.append(tr)          # 环境收集所有变换
        return DataStream(self._environment, tr)

    def map(self, function: Union[BaseFunction, Type[BaseFunction] ],*args, **kwargs) -> "DataStream":
        tr = Transformation(TransformationType.MAP, function,*args, **kwargs)
        return self._apply(tr)

    def sink(self, function: Union[BaseFunction, Type[BaseFunction] ],*args, **kwargs) -> "DataStream":
        tr = Transformation(TransformationType.SINK, function,*args, **kwargs)
        return self._apply(tr)

    def side_output(self, output_index:int):
        if(self.transformations.__len__ > 1):
            raise ValueError("side_output can only be used on a single transformation DataStream.")


    def connect(self, *others: Union["DataStream", List["DataStream"]]) -> "DataStream":
        """
        Connect this DataStream to one or more other DataStreams.
        Supports:
        - s1.connect(s2)
        - s1.connect(s2, s3)
        - s1.connect([s2, s3])
        """
        flattened = []

        for item in others:
            if isinstance(item, list):
                flattened.extend(item)
            else:
                flattened.append(item)

        all_trans = self.transformations[:]
        for stream in flattened:
            all_trans.extend(stream.transformations)

        return DataStream(self._environment, all_trans)