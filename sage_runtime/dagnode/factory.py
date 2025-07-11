from typing import Type, Any, Dict, TYPE_CHECKING, Union
from sage_runtime.function.factory import FunctionFactory
from sage_runtime.dagnode.ray_dag_node import RayDAGNode
from sage_runtime.dagnode.local_dag_node import LocalDAGNode

if TYPE_CHECKING:
    from sage_core.api.transformation import Transformation
    from sage_core.api.env import BaseEnvironment
    from sage_runtime.dagnode.base_dag_node import BaseDAGNode
    from ray.actor import ActorHandle
    from sage_core.core.compiler import GraphNode

    
class DAGNodeFactory:
    def __init__(
        self,
        transformation: 'Transformation',
        # parallel_index: int, # 这个在create instance时传入
    ):
        self.basename = transformation.basename
        self.env_name = transformation.env.name
        self.operator_factory = transformation.operator_factory
        self.delay = transformation.delay
        self.remote:bool = transformation.remote
        self.memory_collection:Union[Any, ActorHandle] = transformation.env.memory_collection
        self.is_spout = transformation.type.value == "source"

        # 这些参数在创建节点时注入
        # self.parallel_index: int  # 来自图编译
        # self.parallelism: int     # 来自图编译
        # self.node_name: str       # 来自图编译

    def create_node(
        self,
        name: str,
        memory_collection: Union[Any, 'ActorHandle'],
        parallel_index: int = 0,
        parallelism: int = 1,
    ) -> 'BaseDAGNode':
        """
        创建 DAG 节点实例
        
        Args:
            graph_node: 图节点，包含动态参数（名称、并行度、并行索引）
            memory_collection: 内存集合（来自环境）
            remote: 是否为远程节点（来自环境平台类型）
        
        Returns:
            创建的 DAG 节点实例
        """
        if self.remote:
            return RayDAGNode(
                name = name,
                operator_factory=self.operator_factory,
                memory_collection=memory_collection,
                delay=self.delay,
                env_name=self.env_name, 
                parallel_index=parallel_index,
                parallelism=parallelism,
                is_spout=self.is_spout
            )
        else:
            return LocalDAGNode(
                name = name,
                operator_factory=self.operator_factory,
                memory_collection=memory_collection,
                delay=self.delay,
                env_name=self.env_name, 
                parallel_index=parallel_index,
                parallelism=parallelism,
                is_spout=self.is_spout
            )
    
    def __repr__(self) -> str:
        return f"<DAGNodeFactory {self.basename}>"