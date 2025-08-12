from typing import Any, TYPE_CHECKING, Union
from sage.kernel.runtime.task.ray_task import RayTask
from sage.kernel.runtime.task.local_task import LocalTask
from sage.kernel.runtime.task.base_task import BaseTask
from sage.kernel.utils.ray.actor import ActorWrapper
if TYPE_CHECKING:
    from sage.core.transformation.base_transformation import BaseTransformation
    from ray.actor import ActorHandle
    from sage.kernel.runtime.context.task_context import TaskContext
    
class TaskFactory:
    def __init__(
        self,
        transformation: 'BaseTransformation',
        # parallel_index: int, # 这个在create instance时传入
    ):
        self.basename = transformation.basename
        self.env_name = transformation.env_name
        self.operator_factory = transformation.operator_factory
        self.delay = transformation.delay
        self.remote:bool = transformation.remote
        self.is_spout = transformation.is_spout

        # 这些参数在创建节点时注入
        # self.parallel_index: int  # 来自图编译
        # self.parallelism: int     # 来自图编译
        # self.node_name: str       # 来自图编译

    def create_task(
        self,
        name: str,
        runtime_context: 'TaskContext' = None,
    ) -> 'BaseTask':
        if self.remote:
            node = RayTask.options(lifetime="detached").remote(runtime_context,  self.operator_factory)
            node = ActorWrapper(node)
        else:
            node = LocalTask(runtime_context, self.operator_factory)
        return node
    
    def __repr__(self) -> str:
        return f"<TaskFactory {self.basename}>"