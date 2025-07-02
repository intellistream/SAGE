# -*- coding: utf-8 -*-
"""Transformation —— 声明即连接，性感即正义。"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, List, Type, Union, TYPE_CHECKING
from enum import Enum
from sage.api.base_function import BaseFunction
from sage.core.operator.base_operator import BaseOperator
from sage.core.operator.map_operator import MapOperator
from sage.utils.custom_logger import CustomLogger

# if TYPE_CHECKING:
#     from sage.core.operator_factory.operator.base_operator_factory import BaseOperatorFactory
#     from sage.core.operator import BaseOperator
#     from sage.core.rag import BaseFunction

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
        transformation_type: TransformationType,
        function: Union[BaseFunction, Type[BaseFunction] ],
        *args,
        parallelism: int = 1,
        platform:str = "local",
        **kwargs
    ):
        self.transformation_type = transformation_type
        """
        Args:
            op_or_class: 可以是 rag/operator 的实例，
                         或 rag/operator 的类。
            **kwargs: 若op_or_class是类，则用于构造实例；
                      若是实例，则忽略。
        """
        if isinstance(function, BaseFunction):
            self.is_instance = True
            self.function = function
            self.function_class = type(function)
        elif isinstance(function, type):
            self.is_instance = False
            self.function = None
            self.function_class = function
        else:
            raise ValueError(
                f"Unsupported rag type: {type(function)}"
            )
        
        self.logger = CustomLogger(
            object_name=f"Transformation_{self.function_class.__name__}",
            log_level="DEBUG",
            console_output=False,
            file_output=True
        )
        self.logger.debug(f"Creating Transformation of type {transformation_type} with rag {self.function_class.__name__}")


        self.operator_class = self.TO_OPERATOR.get(transformation_type, None)
        self.upstream: List["Transformation"] = []
        self.downstream: List["Transformation"] = []
        self.parallelism = parallelism
        self.platform = platform
        self.args = args
        self.kwargs = kwargs


        
    # 双向连接
    def add_upstream(self, parent: "Transformation") -> None:
        self.upstream.append(parent)
        parent.downstream.append(self)

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
            self.function = self.function_class(*self.args, **kwargs)
        return self.operator_class(self.function, **kwargs)

    def __repr__(self) -> str:
        cls_name = self.function_class.__name__
        return f"<Transformation {cls_name} at {hex(id(self))}>"
