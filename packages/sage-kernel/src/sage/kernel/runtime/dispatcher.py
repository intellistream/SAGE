import os
import time
from typing import TYPE_CHECKING, Any, Dict, List, Tuple, Union

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.runtime.service.base_service_task import BaseServiceTask
from sage.kernel.runtime.task.base_task import BaseTask
from sage.kernel.utils.ray.actor import ActorWrapper
from sage.kernel.utils.ray.ray_utils import ensure_ray_initialized
from sage.kernel.scheduler.api import BaseScheduler
from sage.kernel.fault_tolerance.lifecycle import ActorLifecycleManager

if TYPE_CHECKING:
    from sage.kernel.api.base_environment import BaseEnvironment
    from sage.kernel.runtime.graph.execution_graph import ExecutionGraph
    from sage.kernel.runtime.context.service_context import ServiceContext


# 这个dispatcher可以直接打包传给ray sage daemon service
class Dispatcher:
    def __init__(self, graph: "ExecutionGraph", env: "BaseEnvironment"):
        self.total_stop_signals = graph.total_stop_signals
        self.received_stop_signals = 0
        self.graph = graph
        self.env = env
        self.name: str = env.name
        self.remote = env.platform == "remote"
        # self.nodes: Dict[str, Union[ActorHandle, LocalDAGNode]] = {}
        self.tasks: Dict[str, Union[BaseTask, ActorWrapper]] = {}
        self.services: Dict[str, BaseServiceTask] = {}  # 存储服务实例
        self.is_running: bool = False
        
        # 使用调度器和容错管理器
        # 调度器由 Environment 传入，如果没有则使用默认的 FIFO 调度器
        self.scheduler: BaseScheduler = env.scheduler if hasattr(env, 'scheduler') else None
        if self.scheduler is None:
            from sage.kernel.scheduler.impl import FIFOScheduler
            self.scheduler = FIFOScheduler(platform=env.platform)
        self.lifecycle_manager = ActorLifecycleManager()
        
        self.setup_logging_system()
        
        # 注入 logger 到 lifecycle_manager
        self.lifecycle_manager.logger = self.logger
        
        self.logger.info(f"Dispatcher '{self.name}' construction complete")
        if env.platform == "remote":
            self.logger.info(f"Dispatcher '{self.name}' is running in remote mode")
            ensure_ray_initialized()

    def receive_stop_signal(self):
        """
        接收停止信号并处理
        """
        self.logger.info("Dispatcher received stop signal.")
        self.received_stop_signals += 1
        if self.received_stop_signals >= self.total_stop_signals:
            self.logger.info(
                f"Received all {self.total_stop_signals} stop signals, stopping dispatcher for batch job."
            )
            self.cleanup()
            return True
        else:
            return False

    def receive_node_stop_signal(self, node_name: str) -> bool:
        """
        接收单个节点的停止信号

        Args:
            node_name: 停止的节点名称

        Returns:
            bool: 如果所有节点都已停止返回True，否则返回False
        """
        self.logger.info(f"Dispatcher received node stop signal from: {node_name}")

        # 检查节点是否存在
        if node_name not in self.tasks:
            self.logger.warning(f"Node {node_name} not found in tasks")
            return False

        # 如果这是一个源节点，直接通知所有相关的 JoinOperator
        self._notify_join_operators_on_source_stop(node_name)

        # 停止并清理指定节点
        try:
            task = self.tasks[node_name]
            task.stop()
            task.cleanup()

            # 从任务列表中移除
            del self.tasks[node_name]

            self.logger.info(f"Node {node_name} stopped and cleaned up")

        except Exception as e:
            self.logger.error(f"Error stopping node {node_name}: {e}", exc_info=True)
            return False

        # 检查是否所有节点都已停止
        if len(self.tasks) == 0:
            self.logger.info(
                "All computation nodes stopped, batch processing completed"
            )
            self.is_running = False

            # 当所有计算节点停止后，也应该清理服务
            if len(self.services) > 0:
                self.logger.info(
                    f"Cleaning up {len(self.services)} services after batch completion"
                )
                self._cleanup_services_after_batch_completion()

            return True
        else:
            self.logger.info(
                f"Remaining nodes: {len(self.tasks)}, services: {len(self.services)}"
            )
            return False

    def _notify_join_operators_on_source_stop(self, source_node_name: str):
        """当源节点停止时，直接通知相关的 JoinOperator"""
        # 检查是否是源节点（以 "Source" 开头）
        if not source_node_name.startswith("Source"):
            return

        # 查找所有的 JoinOperator
        for task_name, task in self.tasks.items():
            if (
                hasattr(task, "operator")
                and hasattr(task.operator, "handle_stop_signal")
                and hasattr(task.operator, "__class__")
                and "JoinOperator" in task.operator.__class__.__name__
            ):
                # 这是一个 JoinOperator，创建一个停止信号并直接发送
                from sage.kernel.runtime.communication.router.packet import StopSignal

                stop_signal = StopSignal(source_node_name)

                try:
                    # 直接调用 JoinOperator 的 handle_stop_signal 方法
                    task.operator.handle_stop_signal(stop_signal)
                    self.logger.info(
                        f"Notified JoinOperator {task_name} about source {source_node_name} stopping"
                    )
                except Exception as e:
                    self.logger.error(f"Failed to notify JoinOperator {task_name}: {e}")

    def _cleanup_services_after_batch_completion(self):
        """在批处理完成后清理所有服务"""
        self.logger.info("Cleaning up services after batch completion")

        if self.remote:
            # 清理 Ray 服务
            self._cleanup_ray_services()
        else:
            # 清理本地服务
            for service_name, service_task in list(self.services.items()):
                try:
                    # 先停止服务（如果还在运行）
                    if hasattr(service_task, "is_running") and service_task.is_running:
                        self.logger.debug(f"Stopping service task: {service_name}")
                        if hasattr(service_task, "stop"):
                            service_task.stop()

                    # 清理服务（无论是否在运行）
                    if hasattr(service_task, "cleanup"):
                        self.logger.debug(f"Cleaning up service task: {service_name}")
                        service_task.cleanup()

                    self.logger.info(
                        f"Service task '{service_name}' cleaned up successfully"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Error cleaning up service task {service_name}: {e}"
                    )

        # 清空服务字典
        self.services.clear()
        self.logger.info("All services cleaned up")

    def setup_logging_system(self):
        self.logger = CustomLogger(
            [
                ("console", "INFO"),  # 控制台显示重要信息
                (
                    os.path.join(self.env.env_base_dir, "Dispatcher.log"),
                    "DEBUG",
                ),  # 详细日志
                (os.path.join(self.env.env_base_dir, "Error.log"), "ERROR"),  # 错误日志
            ],
            name=f"Dispatcher_{self.name}",
        )

    def start(self):
        # 第三步：启动所有服务任务
        for service_name, service_task in self.services.items():
            try:
                if hasattr(service_task, "start_running"):
                    service_task.start_running()
                elif hasattr(service_task, "_actor") and hasattr(
                    service_task, "start_running"
                ):
                    # ActorWrapper包装的服务
                    import ray

                    ray.get(service_task.start_running.remote())
                self.logger.debug(f"Started service task: {service_name}")
            except Exception as e:
                self.logger.error(
                    f"Failed to start service task {service_name}: {e}", exc_info=True
                )

        # 第四步：提交所有节点开始运行
        for node_name, task in list(self.tasks.items()):
            try:
                task.start_running()
                self.logger.debug(f"Started node: {node_name}")
            except Exception as e:
                self.logger.error(
                    f"Failed to start node {node_name}: {e}", exc_info=True
                )

        self.logger.info(
            f"Job submission completed: {len(self.tasks)} nodes, {len(self.services)} service tasks"
        )
        self.is_running = True

    def _create_service_context(self, service_name: str) -> "ServiceContext":
        """
        获取service task的ServiceContext（从execution graph中已创建的service node获取）

        Args:
            service_name: 服务名称

        Returns:
            从execution graph中获取的ServiceContext
        """
        try:
            # 从execution graph的service_nodes中查找对应的service_node
            service_node = None
            for node_name, node in self.graph.service_nodes.items():
                # 通过service_factory的名称匹配
                if (
                    hasattr(node, "service_factory")
                    and node.service_factory
                    and node.service_factory.service_name == service_name
                ):
                    service_node = node
                    break

            if service_node is None:
                self.logger.error(
                    f"Service node for service '{service_name}' not found in execution graph"
                )
                return None

            # 直接返回已经创建好的ServiceContext
            if not hasattr(service_node, "ctx") or service_node.ctx is None:
                self.logger.error(
                    f"ServiceContext not found in service node for service '{service_name}'"
                )
                return None

            self.logger.debug(
                f"Retrieved ServiceContext for service '{service_name}' from execution graph"
            )
            return service_node.ctx

        except Exception as e:
            self.logger.error(
                f"Failed to retrieve ServiceContext for service {service_name}: {e}",
                exc_info=True,
            )
            return None

    # Dispatcher will submit the job to LocalEngine or Ray Server.
    def submit(self):
        """编译图结构，创建节点并建立连接"""
        self.logger.info(f"Compiling Job for graph: {self.name}")

        # 第一步：调度所有服务任务
        for service_node_name, service_node in self.graph.service_nodes.items():
            try:
                service_name = service_node.service_name
                
                # 为service创建专用的runtime context
                service_ctx = self._create_service_context(service_name)
                
                # 使用调度器创建和调度服务任务
                service_task = self.scheduler.schedule_service(
                    service_node=service_node,
                    runtime_ctx=service_ctx
                )
                self.services[service_name] = service_task
                
                self.logger.debug(
                    f"Scheduled service task '{service_name}' of type '{service_task.__class__.__name__}'"
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to schedule service task {service_name}: {e}", exc_info=True
                )
                # 可以选择继续或停止，这里选择继续但记录错误

        # 第二步：调度所有计算任务节点
        for node_name, graph_node in self.graph.nodes.items():
            try:
                # 使用调度器创建和调度任务
                task = self.scheduler.schedule_task(
                    task_node=graph_node,
                    runtime_ctx=graph_node.ctx
                )
                self.tasks[node_name] = task

                self.logger.debug(
                    f"Scheduled task '{node_name}' of type '{task.__class__.__name__}'"
                )
            except Exception as e:
                self.logger.error(f"Failed to schedule task {node_name}: {e}", exc_info=True)
                raise e

        # 连接关系已经在execution graph层通过task context设置好了，无需在此处设置

        try:
            self.start()
        except Exception as e:
            self.logger.error(f"Error starting dispatcher: {e}", exc_info=True)
            raise e

    def stop(self):
        """停止所有任务和服务"""
        if not self.is_running:
            self.logger.warning("Dispatcher is not running")
            return

        self.logger.info(f"Stopping dispatcher '{self.name}'")

        # 发送停止信号给所有任务
        for node_name, node_instance in self.tasks.items():
            try:
                node_instance.stop()
                self.logger.debug(f"Sent stop signal to node: {node_name}")
            except Exception as e:
                self.logger.error(f"Error stopping node {node_name}: {e}")

        # 停止所有服务任务
        for service_name, service_task in self.services.items():
            try:
                service_task.stop()
                self.logger.debug(f"Stopped service task: {service_name}")
            except Exception as e:
                self.logger.error(f"Error stopping service task {service_name}: {e}")

        # 等待所有任务停止（最多等待10秒）
        self._wait_for_tasks_stop(timeout=10.0)

        self.is_running = False
        self.logger.info("Dispatcher stopped")

    def _wait_for_tasks_stop(self, timeout: float = 10.0):
        """等待所有任务停止"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            all_stopped = True

            for node_name, task in self.tasks.items():
                if hasattr(task, "is_running") and task.is_running:
                    all_stopped = False
                    break

            if all_stopped:
                self.logger.debug("All tasks stopped")
                return

            time.sleep(0.1)

        self.logger.warning(f"Timeout waiting for tasks to stop after {timeout}s")

    def cleanup(self):
        """清理所有资源"""
        self.logger.info(f"Cleaning up dispatcher '{self.name}'")

        try:
            # 停止所有任务和服务
            if self.is_running:
                self.stop()

            if self.remote:
                # 使用生命周期管理器清理所有Ray资源
                self.lifecycle_manager.cleanup_all(
                    tasks=self.tasks,
                    services=self.services,
                    cleanup_timeout=5.0
                )
            else:
                # 清理本地任务
                for node_name, task in self.tasks.items():
                    try:
                        task.cleanup()
                        self.logger.debug(f"Cleaned up task: {node_name}")
                    except Exception as e:
                        self.logger.error(f"Error cleaning up task {node_name}: {e}")

                # 清理本地服务任务
                for service_name, service_task in self.services.items():
                    try:
                        if hasattr(service_task, "cleanup"):
                            service_task.cleanup()
                        self.logger.debug(f"Cleaned up service task: {service_name}")
                    except Exception as e:
                        self.logger.error(
                            f"Error cleaning up service task {service_name}: {e}"
                        )

            # 清空任务和服务字典
            self.tasks.clear()
            self.services.clear()

            self.logger.info("Dispatcher cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during dispatcher cleanup: {e}")

    def get_task_status(self) -> Dict[str, Any]:
        """获取所有任务的状态"""
        status = {}

        for node_name, task in self.tasks.items():
            try:
                task_status = {
                    "name": node_name,
                    "running": getattr(task, "is_running", False),
                    "processed_count": getattr(task, "_processed_count", 0),
                    "error_count": getattr(task, "_error_count", 0),
                }
                status[node_name] = task_status
            except Exception as e:
                status[node_name] = {"name": node_name, "error": str(e)}

        return status

    def get_service_status(self) -> Dict[str, Any]:
        """获取所有服务任务的状态"""
        status = {}

        for service_name, service_task in self.services.items():
            try:
                if hasattr(service_task, "get_statistics"):
                    service_status = service_task.get_statistics()
                elif hasattr(service_task, "_actor") and hasattr(
                    service_task._actor, "get_statistics"
                ):
                    # ActorWrapper包装的服务
                    service_status = service_task._actor.get_statistics()
                else:
                    service_status = {
                        "service_name": service_name,
                        "type": service_task.__class__.__name__,
                        "status": "unknown",
                    }
                status[service_name] = service_status
            except Exception as e:
                status[service_name] = {"service_name": service_name, "error": str(e)}

        return status

    def get_statistics(self) -> Dict[str, Any]:
        """获取dispatcher统计信息"""
        return {
            "name": self.name,
            "is_running": self.is_running,
            "task_count": len(self.tasks),
            "service_count": len(self.services),
            "task_status": self.get_task_status(),
            "service_status": self.get_service_status(),
        }
