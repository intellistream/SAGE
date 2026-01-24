import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sage.kernel.runtime.context.service_context import ServiceContext
    from sage.kernel.runtime.factory.service_factory import ServiceFactory

logger = logging.getLogger(__name__)


class ServiceTaskFactory:
    """服务任务工厂，负责创建服务任务（本地或Ray Actor），类似TaskFactory"""

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
            remote: 是否创建远程服务任务
            extra_python_paths: 额外的 Python 路径，用于 Ray runtime_env
        """
        self.service_factory = service_factory
        self.service_name = service_factory.service_name
        self.remote = remote

        # Extra Python paths for Ray runtime_env
        # Must be passed explicitly since env attribute is excluded during serialization
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
            服务任务实例（LocalServiceTask或ActorWrapper包装的RayServiceTask）
        """
        if self.remote:
            # 创建Ray服务任务
            from sage.kernel.runtime.service.ray_service_task import RayServiceTask
            from sage.kernel.utils.ray.actor import ActorWrapper

            ray_options = {"lifetime": "detached"}

            # Build runtime_env for Ray worker
            if self.extra_python_paths:
                # Use PYTHONPATH environment variable so Ray workers can find custom modules
                runtime_env = {"env_vars": {"PYTHONPATH": ":".join(self.extra_python_paths)}}
                ray_options["runtime_env"] = runtime_env
                logger.info(
                    f"[ServiceTaskFactory] Creating RayServiceTask with runtime_env: {runtime_env}"
                )

            # 直接创建Ray Actor，传入ServiceFactory和ctx
            ray_service_task = RayServiceTask.options(**ray_options).remote(  # type: ignore[attr-defined]
                self.service_factory, ctx
            )

            # 使用ActorWrapper包装
            service_task = ActorWrapper(ray_service_task)

        else:
            # 创建本地服务任务
            from sage.kernel.runtime.service.local_service_task import LocalServiceTask

            service_task = LocalServiceTask(self.service_factory, ctx)  # type: ignore

        return service_task

    def __repr__(self) -> str:
        remote_str = "Remote" if getattr(self, "remote", False) else "Local"
        service_name = getattr(self, "service_name", "Unknown")
        return f"<ServiceTaskFactory {service_name} ({remote_str})>"
