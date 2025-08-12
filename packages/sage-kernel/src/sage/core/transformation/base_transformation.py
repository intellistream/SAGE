from __future__ import annotations
from typing import List, Type, Union, TYPE_CHECKING, Any
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.factory.operator_factory import OperatorFactory
from sage.core.factory.function_factory import FunctionFactory
from ray.actor import ActorHandle
if TYPE_CHECKING:
    from sage.core.operator.base_operator import BaseOperator
    from sage.core.api.function.base_function import BaseFunction
    from sage.core.api.base_environment import BaseEnvironment


class BaseTransformation:
    def __init__(
        self,
        env:'BaseEnvironment',
        function: Type['BaseFunction'],
        *args,
        name:str = None,
        parallelism: int = 1,
        **kwargs
    ):
        self.operator_class:Type[BaseOperator]  # 由子类设置

        self.remote = (env.platform == "remote")
        self.env_name = env.name
        self.env = env
        self.function_class = function
        self.function_args = args
        self.function_kwargs = kwargs

        self.basename =  name or self.function_class.__name__
            

        self.logger = CustomLogger()

        self.logger.debug(f"Creating BaseTransformation of type {type} with rag {self.function_class.__name__}")

        self.upstreams: List[BaseTransformation] = []
        self.downstreams: dict[str, int] = {} 
        self.parallelism = parallelism  

        
        # 懒加载工厂
        self._operator_factory: OperatorFactory = None
        self._function_factory: FunctionFactory = None
        # 生成的平行节点名字：f"{transformation.function_class.__name__}_{i}"

    # 增强的连接方法
    def add_upstream(self, upstream_trans: 'BaseTransformation', input_index: int = 0) -> None:
        """
        添加上游连接
        
        Args:
            upstream_trans: 上游transformation
            input_index: 当前transformation的输入索引
            output_index: 上游transformation的输出索引
        """
        # 添加到当前transformation的upstreams
        self.upstreams.append(upstream_trans)
        # 添加到上游transformation的downstreams
        upstream_trans.downstreams[self.basename] =  input_index
        
        self.logger.debug(f"Connected {upstream_trans.basename} -> {self.basename}[in:{input_index}]")


    ########################################################
    #                     properties                       #
    ########################################################

    @property
    def function_factory(self) -> FunctionFactory:
        """懒加载创建函数工厂"""
        if self._function_factory is None:
            self._function_factory = FunctionFactory(
                function_class=self.function_class,
                function_args=self.function_args,
                function_kwargs=self.function_kwargs
            )
        return self._function_factory

    @property
    def operator_factory(self) -> OperatorFactory:
        """懒加载创建操作符工厂"""
        if self._operator_factory is None:
            self._operator_factory = OperatorFactory(
                operator_class=self.operator_class,
                function_factory=self.function_factory,
                basename=self.basename,
                env_name=self.env_name,
                remote=self.remote
            )   
        return self._operator_factory

    @property
    def delay(self) -> float:
        return 0.1  # 固定的内部事件监听循环延迟
    
    @property
    def is_spout(self) -> bool:
        return False

    @property
    def is_sink(self) -> bool:
        return False

    @property
    def is_merge_operation(self) -> bool:
        """
        判断是否为合并操作
        对于大多数transformation，多个上游输入会被合并到input_index=0
        只有特殊的comap等操作会分别处理多个输入到不同的input_index
        """
        return not hasattr(self.function_class, 'is_comap') or not self.function_class.is_comap


    # ---------------- 工具函数 ----------------


    def __repr__(self) -> str:
        cls_name = self.function_class.__name__
        return f"<{self.__class__.__name__} {cls_name} at {hex(id(self))}>"


