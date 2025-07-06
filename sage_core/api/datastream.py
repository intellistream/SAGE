from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any, List, Tuple

# from sage.api.env import Environment
from sage_core.core.operator.base_operator import BaseOperator
from sage_core.core.operator.transformation import TransformationType, Transformation
from sage_core.api.base_function import BaseFunction

# datastream应该描述多个算子的流结果
# 核心数据结构为：[(transformation1, o3), (transformation2, o2), ...]
# 然后在创建下游运算new_transformation时，会把(t1,o3)接入到(new_t,i1), (t2,o2)接入到(new_t, i2)中。
# 所以说我们在transformation中，需要维护它的每一个输出channel会供给的多个下游


class DataStream:
    # 表示多个transformation生成的流结果
    def __init__(self, env, transformations: Union[
        Transformation, 
        Tuple[Transformation, str], 
        List[Union[Transformation, Tuple[Transformation, str]]]
    ]):
        self._environment = env
        # self.transformations: List[Tuple[Transformation, str]] = []
        if isinstance(transformations, list):
            # Handle list of transformations or tuples
            self.transformations: List[Tuple[Transformation, str]] = []
            for item in transformations:
                if isinstance(item, tuple):
                    # Item is (transformation, output_tag)
                    self.transformations.append(item)
                else:
                    # Item is just transformation, use default channel 0
                    self.transformations.append((item, item.function_class.declare_outputs()[0][0]))
        elif isinstance(transformations, tuple):
            # Single tuple (transformation, channel)
            self.transformations: List[Tuple[Transformation, str]] = [transformations]
        else:
            # Single transformation, use default channel 0
            self.transformations: List[Tuple[Transformation, str]] = [(transformations, transformations.function_class.declare_outputs()[0][0])]


    # ---------------------------------------------------------------------
    # 内部帮助：把新 Transformation 接入管线
    # ---------------------------------------------------------------------
    def _apply(self, tr: Transformation) -> "DataStream":
        # 从tr.function_class.declare_inputs中获取输出标签列表
        # 然后和self.transformations中的每一个transformation输出标签进行匹配
        # 输入可以少于function desired inputs数量，但是不能多
        declared_inputs = tr.function_class.declare_inputs()  # ["in1", "in2", ...]
        if len(self.transformations) > len(declared_inputs):
            raise ValueError(
                f"Too many upstream connections: "
                f"{len(self.transformations)} provided vs {len(declared_inputs)} expected in {tr.function_class.__name__}"
            )

        for (upstream, output_tag), (input_tag, input_type) in zip(self.transformations, declared_inputs):
            tr.add_upstream(input_tag=input_tag, upstream_trans=upstream, upstream_tag=output_tag)

        self._environment._pipeline.append(tr)
        return DataStream(self._environment, tr)

    def map(self, function: Union[BaseFunction, Type[BaseFunction] ],*args, **kwargs) -> "DataStream":
        tr = Transformation(TransformationType.MAP, function,*args, **kwargs)
        return self._apply(tr)

    def sink(self, function: Union[BaseFunction, Type[BaseFunction] ],*args, **kwargs) -> "DataStream":
        tr = Transformation(TransformationType.SINK, function,*args, **kwargs)
        return self._apply(tr)

    def side_output(self, output_tag:str):
        if(len(self.transformations) > 1):
            raise ValueError("side_output can only be used on a single transformation DataStream.")
        declared_tags = [tag for tag, _ in self.transformations[0][0].function_class.declare_outputs()]
        if(output_tag not in declared_tags):
            raise ValueError(f"Output tag '{output_tag}' is not declared in the function {self.transformations[0][0].function_class.__name__}.")
        return DataStream(self._environment, (self.transformations[0][0], output_tag))

    def connect(self, other: "DataStream") -> "DataStream":
        # Create new DataStream with combined transformations instead of modifying self
        combined_transformations = self.transformations + other.transformations
        new_datastream = DataStream.__new__(DataStream)
        new_datastream._environment = self._environment
        new_datastream.transformations = combined_transformations
        return new_datastream
    
    def _append(self, upstream_trans:Transformation, upstream_channel:int = 0)->DataStream:
        self.transformations.append((upstream_trans, upstream_channel))
        return self