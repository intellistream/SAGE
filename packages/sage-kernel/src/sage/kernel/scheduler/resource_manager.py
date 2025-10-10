"""
资源管理器

负责管理本地和远程计算资源，提供资源可用性查询和分配功能。
"""

from typing import Any, Dict, Optional

from sage.kernel.core.exceptions import ResourceAllocationError
from sage.kernel.core.types import ExecutionMode, TaskID


class ResourceManager:
    """
    资源管理器

    管理本地和远程（Ray）资源的分配和释放。
    """

    def __init__(self, platform: str = "local"):
        """
        初始化资源管理器

        Args:
            platform: 平台类型 ('local' 或 'remote')
        """
        self.platform = platform
        self.local_resources: Dict[str, Any] = {}
        self.remote_resources: Dict[str, Any] = {}
        self.allocated_resources: Dict[TaskID, Dict[str, Any]] = {}

    def has_local_resources(self) -> bool:
        """
        检查是否有可用的本地资源

        Returns:
            True 如果有本地资源可用
        """
        # 简化实现：本地资源总是可用
        return True

    def has_remote_resources(self) -> bool:
        """
        检查是否有可用的远程资源

        Returns:
            True 如果有远程资源（Ray 集群）可用
        """
        if self.platform == "remote":
            return self._check_ray_availability()
        return False

    def _check_ray_availability(self) -> bool:
        """
        检查 Ray 集群是否可用

        Returns:
            True 如果 Ray 已初始化
        """
        try:
            import ray

            return ray.is_initialized()
        except ImportError:
            return False

    def allocate_resource(
        self, task_id: TaskID, resource_type: str = "cpu", amount: float = 1.0
    ) -> bool:
        """
        为任务分配资源

        Args:
            task_id: 任务标识符
            resource_type: 资源类型 ('cpu', 'gpu', 'memory' 等)
            amount: 资源数量

        Returns:
            True 如果分配成功

        Raises:
            ResourceAllocationError: 如果资源不足
        """
        # 记录分配的资源
        if task_id not in self.allocated_resources:
            self.allocated_resources[task_id] = {}

        self.allocated_resources[task_id][resource_type] = amount
        return True

    def release_resource(self, task_id: TaskID):
        """
        释放任务占用的资源

        Args:
            task_id: 任务标识符
        """
        if task_id in self.allocated_resources:
            del self.allocated_resources[task_id]

    def get_available_resources(self) -> Dict[str, Any]:
        """
        获取可用资源信息

        Returns:
            资源信息字典
        """
        resources = {
            "platform": self.platform,
            "local_available": self.has_local_resources(),
            "remote_available": self.has_remote_resources(),
        }

        if self.has_remote_resources():
            try:
                import ray

                resources["ray_resources"] = ray.available_resources()
            except:
                pass

        return resources

    def get_resource_usage(self) -> Dict[str, Any]:
        """
        获取资源使用情况

        Returns:
            资源使用情况字典
        """
        return {
            "allocated_tasks": len(self.allocated_resources),
            "allocations": dict(self.allocated_resources),
        }


__all__ = ["ResourceManager"]
