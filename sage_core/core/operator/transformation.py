# -*- coding: utf-8 -*-
"""Transformation —— 声明即连接，性感即正义。"""

from __future__ import annotations
from typing import List, Type, Union, Tuple
from enum import Enum
from sage_core.api.base_function import BaseFunction
from sage_core.api.environment import BaseEnvironment
from sage_core.core.operator.base_operator import BaseOperator
from sage_core.core.operator.map_operator import MapOperator
from sage_utils.custom_logger import CustomLogger
from sage_core.api.enum import PlatformType
from sage_utils.name_server import get_name
class TransformationType(Enum):
    MAP = "map"
    FILTER = "filter"
    FLATMAP = "flatmap"
    SINK = "sink"
    SOURCE = "source"

class Transformation:
    TO_OPERATOR = {
        TransformationType.MAP: MapOperator,
        # TODO: 添加其他transformation类型的映射
        # TransformationType.FILTER: FilterOperator,
        # TransformationType.FLATMAP: FlatMapOperator,
        TransformationType.SINK: MapOperator,
        TransformationType.SOURCE: MapOperator,
    }
    def __init__(
        self,
        env:BaseEnvironment,
        type: TransformationType,
        function: Union[BaseFunction, Type[BaseFunction] ],
        *args,
        name:str = None,
        parallelism: int = 1,
        platform:PlatformType = PlatformType.LOCAL,
        **kwargs
    ):
        self.env = env
        self.type = type

        if(env.platform is PlatformType.HYBRID):
            self.platform = platform
        else:
            self.platform = env.platform
        
        if isinstance(function, BaseFunction):
            self.is_instance = True
            self.function = function
            self.function_class = type(function)
        elif isinstance(function, Type):
            self.is_instance = False
            self.function = None
            self.function_class = function
        else:
            raise ValueError(
                f"Unsupported rag type: {type(function)}"
            )


            
        self.basename = get_name(name) or get_name(self.function_class.__name__)
        # 这个basename会沿用到生成的dagnode， operator和functions上

        self.logger = CustomLogger(
            object_name=get_name(f"Transformation_{self.basename}"),
            console_output=False,
            file_output=True
        )
        self.logger.debug(f"Creating Transformation of type {type} with rag {self.function_class.__name__}")


        self.operator_class = self.TO_OPERATOR.get(type, None)
        self.upstreams:List[Tuple[Transformation, int]] = []
        # (upstream_transformation, upstream_output_channel)

        self.downstreams:List[List[Tuple[Transformation, int]]] = []
        # {(downstream_transformation, downstream_input_channel)}
        # 维护自己每一个输出channel会供给的多个下游并行算子组（组与组广播，组内发一个）

        self.parallelism = parallelism  
        # 生成的平行节点名字：f"{transformation.function_class.__name__}_{i}"
        self.function_args = args
        self.kwargs = kwargs


        
    # 双向连接
    def add_upstream(self, upstream_trans: "Transformation", upstream_channel:int = 0) -> None:
        self.upstreams.append((upstream_trans, upstream_channel))
        while(len(upstream_trans.downstreams) <= upstream_channel):
            # 确保上游的downstreams列表有足够的长度
            upstream_trans.downstreams.append([])
        upstream_trans.downstreams[upstream_channel].append((self, len(self.upstreams) - 1))

    # 这个方法不要使用，避免重复连接
    # def add_downstream(self, child: "Transformation") -> None:
    #     self.downstream.append(child)
    #     child.upstream.append(self)

    # ---------------- 编译器接口 ----------------
    # @abstractmethod
    # def get_operator_factory(self) -> "BaseOperatorFactory":
    #     """返回生成 Operator 的工厂。"""

    # ---------------- 工具函数 ----------------
    def build_instance(self, **kwargs) -> BaseOperator:
        """如果尚未实例化，则根据 op_class 和 kwargs 实例化。"""
        if self.is_instance is False:
            # *self.args是用户传递的Function构造函数参数
            # **kwargs是engine传递的构造函数参数
            self.function = self.function_class(*self.function_args, **kwargs)
            self.logger.debug(f"Created function instance: {self.function_class.__name__} with args {self.function_args} and kwargs {kwargs}")
        return self.operator_class(self.function, **kwargs)

    def __repr__(self) -> str:
        cls_name = self.function_class.__name__
        return f"<Transformation {cls_name} at {hex(id(self))}>"
