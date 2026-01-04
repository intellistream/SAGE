"""
TaskNode - 图节点类

每个TaskNode代表一个transformation的单个并行实例，包含：
- 单一输入队列描述符（被所有上游复用）
- 服务响应队列描述符
- 输入通道和输出通道的连接信息
- 运行时上下文
- TaskFactory用于创建任务实例
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sage.kernel.utils.ray.ray_utils import normalize_extra_python_paths

if TYPE_CHECKING:
    from sage.kernel.api.base_environment import BaseEnvironment
    from sage.kernel.api.transformation.base_transformation import BaseTransformation
    from sage.kernel.runtime.context.task_context import TaskContext
    from sage.kernel.runtime.factory.task_factory import TaskFactory
    from sage.kernel.runtime.graph.graph_edge import GraphEdge
    from sage.platform.queue.base_queue_descriptor import BaseQueueDescriptor


def _create_queue_descriptor(env: BaseEnvironment, name: str, maxsize: int) -> BaseQueueDescriptor:
    """
    根据环境平台类型创建相应的队列描述符

    Args:
        env: 环境对象
        name: 队列名称
        maxsize: 队列最大大小

    Returns:
        对应平台的队列描述符
    """
    if env.platform == "remote":
        from sage.platform.queue.ray_queue_descriptor import RayQueueDescriptor

        return RayQueueDescriptor(maxsize=maxsize, queue_id=name)
    else:  # local 或其他情况使用 python 队列
        from sage.platform.queue.python_queue_descriptor import PythonQueueDescriptor

        return PythonQueueDescriptor(maxsize=maxsize, queue_id=name)


class TaskNode:
    """
    图节点类

    每个TaskNode只有一个输入队列描述符 - 不是每个输入通道一个
    这个输入队列被所有上游节点复用 - 所有上游都写入同一个队列
    输入通道只是逻辑概念 - 用于区分不同的输入数据流，但物理上共享同一个队列
    """

    def __init__(
        self,
        name: str,
        transformation: BaseTransformation,
        parallel_index: int,
        env: BaseEnvironment,
    ):
        self.name: str = name
        self.transformation: BaseTransformation = transformation
        self.parallel_index: int = parallel_index  # 在该transformation中的并行索引
        self.parallelism: int = transformation.parallelism
        self.is_spout: bool = transformation.is_spout
        self.is_sink: bool = transformation.is_sink
        self.input_channels: dict[int, list[GraphEdge]] = {}
        self.output_channels: list[list[GraphEdge]] = []

        # 在构造时创建队列描述符
        self._create_queue_descriptors(env)

        # 在ExecutionGraph中创建TaskFactory，而不是在BaseTransformation中
        # 保存 extra_python_paths 用于传递给 TaskFactory
        self._extra_python_paths = normalize_extra_python_paths(
            getattr(env, "extra_python_paths", None)
        )

        # 在ExecutionGraph中创建TaskFactory，而不是在BaseTransformation中
        self.task_factory: TaskFactory = self._create_task_factory()

        self.stop_signal_num: int = 0  # 预期的源节点数量
        self.ctx: TaskContext | None = None

    def _create_queue_descriptors(self, env: BaseEnvironment):
        """在节点构造时创建队列描述符"""
        # 使用 env.name 作为队列前缀，确保不同 job 的队列隔离
        # env.name 在 Environment 创建时就已确定，且对于同一 pipeline 唯一
        env_prefix = env.name

        # 为每个节点创建单一的输入队列描述符（被所有上游复用）
        if not self.is_spout:  # 源节点不需要输入队列
            self.input_qd = _create_queue_descriptor(
                env=env, name=f"{env_prefix}__input_{self.name}", maxsize=10000
            )
        else:
            self.input_qd = None

        # 为每个graph node创建service response queue descriptor
        self.service_response_qd = _create_queue_descriptor(
            env=env, name=f"{env_prefix}__service_response_{self.name}", maxsize=10000
        )

    def _create_task_factory(self) -> TaskFactory:
        """在TaskNode中创建TaskFactory，避免BaseTransformation依赖runtime层"""
        from sage.kernel.runtime.factory.task_factory import TaskFactory

        return TaskFactory(self.transformation, extra_python_paths=self._extra_python_paths)

    def __repr__(self) -> str:
        return f"TaskNode(name={self.name}, parallel_index={self.parallel_index}, is_spout={self.is_spout}, is_sink={self.is_sink})"
