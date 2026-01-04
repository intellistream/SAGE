import logging
from typing import TYPE_CHECKING

from sage.kernel.runtime.task.local_task import LocalTask
from sage.kernel.runtime.task.ray_task import RayTask
from sage.kernel.utils.ray.actor import ActorWrapper
from sage.kernel.utils.ray.ray_utils import normalize_extra_python_paths

if TYPE_CHECKING:
    from sage.kernel.api.transformation.base_transformation import BaseTransformation
    from sage.kernel.runtime.context.task_context import TaskContext

logger = logging.getLogger(__name__)


class TaskFactory:
    def __init__(
        self,
        transformation: "BaseTransformation",
        extra_python_paths: list[str] | None = None,
    ):
        self.basename = transformation.basename
        self.env_name = transformation.env_name
        self.operator_factory = transformation.operator_factory
        self.delay = transformation.delay
        self.remote: bool = transformation.remote
        self.is_spout = transformation.is_spout

        # Extra Python paths for Ray runtime_env
        # Must be passed explicitly since env attribute is excluded during serialization
        self.extra_python_paths: list[str] = normalize_extra_python_paths(extra_python_paths)

    def create_task(
        self,
        name: str,
        runtime_context: "TaskContext | None" = None,
    ):
        if self.remote:
            # Build runtime_env for Ray worker
            runtime_env = {}
            if self.extra_python_paths:
                # Use PYTHONPATH environment variable so Ray workers can find custom modules
                runtime_env["env_vars"] = {"PYTHONPATH": ":".join(self.extra_python_paths)}
                logger.info(f"[TaskFactory] Creating RayTask with runtime_env: {runtime_env}")

            # Pass runtime_env when creating Ray Actor
            if runtime_env:
                node = RayTask.options(
                    lifetime="detached",
                    runtime_env=runtime_env,
                ).remote(runtime_context, self.operator_factory)
            else:
                node = RayTask.options(lifetime="detached").remote(
                    runtime_context, self.operator_factory
                )
            node = ActorWrapper(node)
        else:
            node = LocalTask(ctx=runtime_context, operator_factory=self.operator_factory)  # type: ignore
        return node

    def __repr__(self) -> str:
        return f"<TaskFactory {self.basename}>"
