# -*- coding: utf-8 -*-
"""Transformation —— 声明即连接，性感即正义。"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, List, Type, Union, TYPE_CHECKING
from enum import Enum
from sage.api.base_function import BaseFunction
from sage.api.base_operator import BaseOperator


# if TYPE_CHECKING:
#     from sage.core.operator_factory.base_operator_factory import BaseOperatorFactory
#     from sage.core.operator import BaseOperator
#     from sage.core.function import BaseFunction

class TransformationType(Enum):
    MAP = "map"
    FILTER = "filter"
    FLATMAP = "flatmap"
    SINK = "sink"
    SOURCE = "source"



class BaseTransformation(ABC):

    def __init__(
        self,
        transformation_type: TransformationType,
        function: Union[BaseFunction, Type[BaseFunction] ],
        *args,
        parallelism: int = 1,
        platform:str = "local",
        **kwargs
    ):
        """
        Args:
            op_or_class: 可以是 function/operator 的实例，
                         或 function/operator 的类。
            **kwargs: 若op_or_class是类，则用于构造实例；
                      若是实例，则忽略。
        """
        self.transformation_type = transformation_type
        self.upstream: List["BaseTransformation"] = []
        self.downstream: List["BaseTransformation"] = []
        self.parallelism = parallelism
        self.platform = platform
        self.args = args
        self.kwargs = kwargs
        if isinstance(function, BaseFunction):
            self.is_instance = True
            self.function = function
            self.function_class = type(function)
        elif isinstance(function, type):
            self.is_instance = False
            self.op_instance = None
            self.op_class = function
        else:
            raise ValueError(
                f"Unsupported function type: {type(function)}"
            )
        
    # 双向连接
    def add_upstream(self, parent: "BaseTransformation") -> None:
        self.upstream.append(parent)
        parent.downstream.append(self)

    # 这个方法不要使用，避免重复连接
    # def add_downstream(self, child: "BaseTransformation") -> None:
    #     self.downstream.append(child)
    #     child.upstream.append(self)

    # ---------------- 编译器接口 ----------------
    # @abstractmethod
    # def get_operator_factory(self) -> "BaseOperatorFactory":
    #     """返回生成 Operator 的工厂。"""

    # ---------------- 工具函数 ----------------
    def build_instance(self) -> BaseOperator:
        """如果尚未实例化，则根据 op_class 和 kwargs 实例化。"""
        if self.is_instance:
            return self.op_instance
        return BaseOperator(self.op_class, *self.args, **self.kwargs)

    def __repr__(self) -> str:
        cls_name = self.op_class.__name__
        return f"<Transformation {cls_name} at {hex(id(self))}>"
