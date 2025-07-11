from __future__ import annotations
from typing import List, Type, Union, Tuple, Dict, Set, TYPE_CHECKING, Any, Optional
from enum import Enum
from abc import ABC, abstractmethod
from sage_utils.custom_logger import CustomLogger
from sage_utils.name_server import get_name
from sage_runtime.operator.factory import OperatorFactory
from sage_runtime.function.factory import FunctionFactory
from sage_runtime.dagnode.factory import DAGNodeFactory
from ray.actor import ActorHandle
if TYPE_CHECKING:
    from sage_core.operator.base_operator import BaseOperator
    from sage_core.function.base_function import BaseFunction
    from sage_core.api.env import BaseEnvironment


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
        self.env = env
        self.function_class = function
        self.basename = get_name(name) if name else get_name(self.function_class.__name__)
            

        self.logger = CustomLogger(
            filename=f"BaseTransformation_{self.basename}",
            env_name = env.name,
            console_output=False,
            file_output=True
        )
        if self.remote and not isinstance(env.memory_collection, ActorHandle):
            raise Exception("Memory collection must be a Ray Actor handle for remote transformation")
        # 创建可序列化的函数工厂
        self.function_factory = FunctionFactory(
            function_class=self.function_class,
            function_args=args,
            function_kwargs=kwargs
        )

        self.logger.debug(f"Creating BaseTransformation of type {type} with rag {self.function_class.__name__}")

        self.operator_factory = OperatorFactory(
            operator_class=self.operator_class,
            function_factory=self.function_factory,  # 传递函数工厂而不是具体参数
            basename=self.basename,
            env_name = env.name,
            remote = self.remote
        )
        # 创建 DAG 节点工厂（包含所有静态参数）
        self.dag_node_factory = DAGNodeFactory(self)



        self.upstream:BaseTransformation = None
        self.downstreams:List[Tuple[BaseTransformation, str]] = []
        


        self.parallelism = parallelism  
        # 生成的平行节点名字：f"{transformation.function_class.__name__}_{i}"
        self.function_args = args
        self.kwargs = kwargs
    
    @property
    def delay(self) -> float:
        return 0.1  # 固定的内部事件监听循环延迟
    
    @property
    def is_spout(self) -> bool:
        return False

    # 双向连接
    def add_upstream(self,upstream_trans: 'BaseTransformation') -> None:
        self.upstream = upstream_trans
        upstream_trans.downstreams.append(self)

    # ---------------- 工具函数 ----------------
    def create_operator(self, **kwargs) -> 'BaseOperator':
        """如果尚未实例化，则根据 op_class 和 kwargs 实例化。"""
        function = self.function_class(*self.function_args, **kwargs)
        self.logger.debug(f"Created function instance: {self.function_class.__name__} with args {self.function_args} and kwargs {kwargs}")
        return self.operator_class(function, **kwargs)


    def __repr__(self) -> str:
        cls_name = self.function_class.__name__
        return f"<{self.__class__.__name__} {cls_name} at {hex(id(self))}>"


