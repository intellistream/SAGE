from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any, List, Tuple, TypeVar, Generic, get_args, get_origin
from sage_core.transformation.base_transformation import BaseTransformation
from sage_core.function.base_function import BaseFunction
if TYPE_CHECKING:
    from .datastream import DataStream
    from .env import BaseEnvironment

# TODO: 重做
# Issue URL: https://github.com/intellistream/SAGE/issues/146
class ConnectedStreams:
    """表示多个transformation连接后的流结果"""
    def __init__(self, env:'BaseEnvironment', transformations: List[Tuple[BaseTransformation, str]]):
        self._environment = env
        self.transformations = transformations

    def _apply(self, tr: BaseTransformation) -> 'DataStream':
        """将新 BaseTransformation 接入管线"""
        declared_inputs = tr.function_class.declare_inputs()
        
        if len(self.transformations) > len(declared_inputs):
            raise ValueError(
                f"Too many upstream connections: "
                f"{len(self.transformations)} provided vs {len(declared_inputs)} expected in {tr.function_class.__name__}"
            )

        # 按顺序连接每个上游transformation到对应的输入
        for (upstream_trans, output_tag), (input_tag, input_type) in zip(self.transformations, declared_inputs):
            tr.add_upstream(input_tag=input_tag, upstream_trans=upstream_trans, upstream_tag=output_tag)

        return self._environment._append(tr)

    def map(self, function: Union[BaseFunction, Type[BaseFunction]], *args, **kwargs) -> 'DataStream':
        tr = BaseTransformation(self._environment,BaseTransformationType.MAP, function, *args, **kwargs)
        return self._apply(tr)

    def sink(self, function: Union[BaseFunction, Type[BaseFunction]], *args, **kwargs) -> 'DataStream':
        tr = BaseTransformation(self._environment, BaseTransformationType.SINK, function, *args, **kwargs)
        return self._apply(tr)

    def connect(self, other: Union['DataStream', 'ConnectedStreams']) -> 'ConnectedStreams':
        """连接更多数据流"""
        if isinstance(other, DataStream):
            new_transformations = self.transformations + [(other.transformation, other.output_tag)]
        else:  # ConnectedStreams
            new_transformations = self.transformations + other.transformations
        
        return ConnectedStreams(self._environment, new_transformations)