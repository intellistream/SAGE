import logging
from typing import TYPE_CHECKING

from sage.kernel.runtime.task.local_task import LocalTask

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

        # Extra Python paths reserved for distributed runtime bootstrapping.
        # Ray has been removed from kernel runtime; paths are kept for future transport bootstrap.
        self.extra_python_paths: list[str] = (
            extra_python_paths
            if isinstance(extra_python_paths, list)
            else ([extra_python_paths] if extra_python_paths else [])
        )

    def create_task(
        self,
        name: str,
        runtime_context: "TaskContext | None" = None,
    ):
        if self.remote:
            logger.info(
                "[TaskFactory] remote=True requested; using kernel-native task runtime (Ray removed)."
            )
        node = LocalTask(ctx=runtime_context, operator_factory=self.operator_factory)  # type: ignore
        return node

    def __repr__(self) -> str:
        return f"<TaskFactory {self.basename}>"
