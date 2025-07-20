from typing import Type, Any, Dict, TYPE_CHECKING, Union
from sage_runtime.ray_task import RayTask
from sage_runtime.dagnode.local_dag_node import LocalDAGNode
import ray
from sage_runtime.actor_wrapper import ActorWrapper
if TYPE_CHECKING:
    from sage_core.transformation.base_transformation import BaseTransformation
    from sage_runtime.dagnode.base_dag_node import BaseDAGNode
    from ray.actor import ActorHandle
    from sage_runtime.runtime_context import RuntimeContext
    
class TaskFactory:
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
            node = RayTask.remote(name, runtime_context,  self.operator_factory)
            node = ActorWrapper(node, name, self.env_name)
        else:
            node = LocalDAGNode(name, runtime_context, self.operator_factory)
        return node
    
    def __repr__(self) -> str:
        return f"<TaskFactory {self.basename}>"