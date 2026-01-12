from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sage.kernel.runtime.context.service_context import ServiceContext
    from sage.kernel.runtime.factory.service_factory import ServiceFactory


class ServiceTaskFactory:
    """服务任务工厂，负责创建服务任务（本地或Ray Actor），类似TaskFactory"""

    def __init__(self, service_factory: "ServiceFactory", remote: bool = False):
        """
        初始化服务任务工厂

        Args:
            service_factory: 服务工厂实例
            remote: 是否创建远程服务任务
        """
        self.service_factory = service_factory
        self.service_name = service_factory.service_name
        self.remote = remote

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

            # 构建 Ray Actor options
            actor_options = {"lifetime": "detached"}

            # 从 ServiceFactory 获取调度选项
            scheduling_opts = getattr(self.service_factory, "scheduling_options", {}) or {}

            # 节点调度选项
            if "node_id" in scheduling_opts:
                # 指定节点 ID（Ray 内部格式）
                actor_options["scheduling_strategy"] = (
                    f"node:{scheduling_opts['node_id']}"
                )
            elif "node_ip" in scheduling_opts:
                # 通过 IP 地址指定节点
                import ray
                from ray.util.scheduling_strategies import NodeAffinitySchedulingStrategy
                node_ip = scheduling_opts["node_ip"]
                # 查找对应节点 ID
                nodes = ray.nodes()
                target_node_id = None
                for node in nodes:
                    if node.get("NodeManagerAddress") == node_ip and node.get("Alive"):
                        target_node_id = node.get("NodeID")
                        break
                if target_node_id:
                    actor_options["scheduling_strategy"] = NodeAffinitySchedulingStrategy(
                        node_id=target_node_id, soft=False
                    )
                    print(f"[ServiceTaskFactory] Scheduling service '{self.service_name}' to node {node_ip}")

            # 资源需求选项
            if "num_cpus" in scheduling_opts:
                actor_options["num_cpus"] = scheduling_opts["num_cpus"]
            if "num_gpus" in scheduling_opts:
                actor_options["num_gpus"] = scheduling_opts["num_gpus"]
            if "resources" in scheduling_opts:
                actor_options["resources"] = scheduling_opts["resources"]

            # 创建 Ray Actor，传入 ServiceFactory 和 ctx
            ray_service_task = RayServiceTask.options(**actor_options).remote(  # type: ignore[attr-defined]
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
