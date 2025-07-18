from typing import Type, Any, Dict, TYPE_CHECKING, Union
from sage_runtime.function.factory import FunctionFactory
from sage_runtime.dagnode.ray_dag_node import RayDAGNode
from sage_runtime.dagnode.local_dag_node import LocalDAGNode

if TYPE_CHECKING:
    from sage_core.transformation.base_transformation import BaseTransformation
    from sage_core.api.env import BaseEnvironment
    from sage_runtime.dagnode.base_dag_node import BaseDAGNode
    from ray.actor import ActorHandle
    from sage_runtime.compiler import GraphNode
    from sage_runtime.runtime_context import RuntimeContext
    
class DAGNodeFactory:
    def __init__(
        self,
        transformation: 'BaseTransformation',
        # parallel_index: int, # 这个在create instance时传入
    ):
        self.basename = transformation.basename
        self.env_name = transformation.env.name
        self.operator_factory = transformation.operator_factory
        self.delay = transformation.delay
        self.remote:bool = transformation.remote
        self.memory_collection:Union[Any, ActorHandle] = transformation.env.memory_collection
        self.is_spout = transformation.is_spout

        # 这些参数在创建节点时注入
        # self.parallel_index: int  # 来自图编译
        # self.parallelism: int     # 来自图编译
        # self.node_name: str       # 来自图编译

    def create_node(
        self,
        name: str,
        runtime_context: 'RuntimeContext' = None,
    ) -> 'BaseDAGNode':
        if self.remote:
            node = RayDAGNode(name, runtime_context,  self.operator_factory)
        else:
            node = LocalDAGNode(name, runtime_context, self.operator_factory)
        node.delay = self.delay
        node.is_spout = self.is_spout
        # print(f"{name} is spout: {node.is_spout}")
        return node
    
    def __repr__(self) -> str:
        return f"<DAGNodeFactory {self.basename}>"