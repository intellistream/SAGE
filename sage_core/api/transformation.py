from __future__ import annotations
from typing import List, Type, Union, Tuple, Dict, Set, TYPE_CHECKING, Any, Optional
from enum import Enum
# from sage_core.api.env import BaseEnvironment
from sage_core.core.operator.map_operator import MapOperator
from sage_core.core.operator.flatmap_operator import FlatMapOperator
from sage_core.core.operator.filter_operator import FilterOperator
from sage_utils.custom_logger import CustomLogger
from sage_core.api.enum import PlatformType
from sage_utils.name_server import get_name
from sage_runtime.operator.factory import OperatorFactory
from sage_runtime.function.factory import FunctionFactory
from sage_runtime.dagnode.factory import DAGNodeFactory
from ray.actor import ActorHandle
if TYPE_CHECKING:
    from sage_core.core.operator.base_operator import BaseOperator
    from sage_core.api.base_function import BaseFunction
    from sage_core.api.env import BaseEnvironment


class TransformationType(Enum):
    MAP = "map"
    FILTER = "filter"
    FLATMAP = "flatmap"
    SINK = "sink"
    SOURCE = "source"

# TODO: 提供更多的transformation继承类，改善构造函数
# Issue URL: https://github.com/intellistream/SAGE/issues/147
class Transformation:
    TO_OPERATOR = {
        TransformationType.MAP: MapOperator,
        TransformationType.FILTER: FilterOperator,
        TransformationType.FLATMAP: FlatMapOperator,
        TransformationType.SINK: MapOperator,
        TransformationType.SOURCE: MapOperator,
    }
    def __init__(
        self,
        env:'BaseEnvironment',
        type: TransformationType,
        function: Type['BaseFunction'],
        *args,
        name:str = None,
        parallelism: int = 1,
        platform:PlatformType = PlatformType.LOCAL,
        delay: Optional[float] = 0.1,
        **kwargs
    ):
        self.remote = (platform == PlatformType.REMOTE) or False
        self.env = env
        self.type = type
        self.delay = delay
        self.function_class = function
        self.basename = get_name(name) if name else get_name(self.function_class.__name__)
            

        self.logger = CustomLogger(
            filename=f"Transformation_{self.basename}",
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
            function_kwargs=kwargs,
            memory_collection= self.env.memory_collection
        )

        self.logger.debug(f"Creating Transformation of type {type} with rag {self.function_class.__name__}")

        # 创建OperatorFactory来处理operator的创建
        self.operator_class = self.TO_OPERATOR.get(type, None)

        self.operator_factory = OperatorFactory(
            operator_class=self.operator_class,
            function_factory=self.function_factory,  # 传递函数工厂而不是具体参数
            is_spout = (self.type == TransformationType.SOURCE),
            basename=self.basename,
            env_name = env.name,
            remote = self.remote
        )
        # 创建 DAG 节点工厂（包含所有静态参数）
        self.dag_node_factory = DAGNodeFactory(self)



        self.upstream:Transformation = None
        self.downstreams:List[Tuple[Transformation, str]] = []
        


        self.parallelism = parallelism  
        # 生成的平行节点名字：f"{transformation.function_class.__name__}_{i}"
        self.function_args = args
        self.kwargs = kwargs


        
    # 双向连接
    def add_upstream(self,upstream_trans: 'Transformation') -> None:
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
        return f"<Transformation {cls_name} at {hex(id(self))}>"


