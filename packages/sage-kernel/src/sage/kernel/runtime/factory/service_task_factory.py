import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sage.kernel.runtime.context.service_context import ServiceContext
    from sage.kernel.runtime.factory.service_factory import ServiceFactory

logger = logging.getLogger(__name__)


class ServiceTaskFactory:
    """服务任务工厂，负责创建服务任务。"""

    def __init__(
        self,
        service_factory: "ServiceFactory",
        remote: bool = False,
        extra_python_paths: list[str] | None = None,
    ):
        """
        初始化服务任务工厂

        Args:
            service_factory: 服务工厂实例
            remote: 是否请求远程服务任务（当前仅作为提示，Ray 已移除）
            extra_python_paths: 额外 Python 路径（预留给后续分布式运行时）
        """
        self.service_factory = service_factory
        self.service_name = service_factory.service_name
        self.remote = remote

        # Extra Python paths reserved for future distributed runtime bootstrap.
        self.extra_python_paths: list[str] = (
            extra_python_paths
            if isinstance(extra_python_paths, list)
            else ([extra_python_paths] if extra_python_paths else [])
        )

    def create_service_task(self, ctx: "ServiceContext | None" = None):
        """
        参考task_factory.create_task的逻辑，创建服务任务实例

        Args:
            ctx: 服务运行时上下文

        Returns:
            服务任务实例
        """
        if self.remote:
            logger.info(
                "[ServiceTaskFactory] remote=True requested; using kernel-native service runtime (Ray removed)."
            )

        from sage.kernel.runtime.service.local_service_task import LocalServiceTask

        service_task = LocalServiceTask(self.service_factory, ctx)  # type: ignore

        return service_task

    def __repr__(self) -> str:
        remote_str = "Remote" if getattr(self, "remote", False) else "Local"
        service_name = getattr(self, "service_name", "Unknown")
        return f"<ServiceTaskFactory {service_name} ({remote_str})>"
