import os
import time
from typing import TYPE_CHECKING, Any

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.fault_tolerance.factory import (
    create_fault_handler_from_config,
    create_lifecycle_manager,
)
from sage.kernel.runtime.heartbeat_monitor import HeartbeatMonitor
from sage.kernel.scheduler.api import BaseScheduler
from sage.kernel.utils.ray.actor import ActorWrapper
from sage.kernel.utils.ray.ray_utils import ensure_ray_initialized

if TYPE_CHECKING:
    from sage.kernel.api.base_environment import BaseEnvironment
    from sage.kernel.runtime.context.service_context import ServiceContext
    from sage.kernel.runtime.graph.execution_graph import ExecutionGraph
    from sage.kernel.runtime.service.local_service_task import LocalServiceTask
    from sage.kernel.runtime.task.local_task import LocalTask


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
        self.tasks: dict[str, LocalTask | ActorWrapper] = {}
        self.services: dict[str, LocalServiceTask | ActorWrapper] = {}  # 存储服务实例
        self.is_running: bool = False
        # HeartbeatMonitor 实例 (监控线程)
        self.heartbeat_monitor: HeartbeatMonitor | None = None

        # 容错配置
        self.fault_tolerance_config = {
            "enabled": False,  # 是否启用容错
            "heartbeat_interval": 5.0,  # 心跳间隔 (秒)
            "heartbeat_timeout": 15.0,  # 超时阈值 (秒)
            "max_restart_attempts": 3,  # 最大重启次数
        }

        # 使用调度器和容错管理器（重构后架构）
        # 调度器：纯决策者（返回 PlacementDecision）
        # PlacementExecutor：纯执行者（接收决策，执行放置）
        # Dispatcher：协调者（决策 → 执行）

        # 初始化调度器
        self.scheduler: BaseScheduler
        if hasattr(env, "scheduler") and env.scheduler is not None:
            self.scheduler = env.scheduler
        else:
            from sage.kernel.scheduler.impl import FIFOScheduler

            self.scheduler = FIFOScheduler(platform=env.platform)

        # 初始化放置执行器（由 Dispatcher 持有，不在 Scheduler 中）
        from sage.kernel.scheduler.placement import PlacementExecutor

        self.placement_executor = PlacementExecutor()

        # 从 Environment 配置创建容错处理器
        fault_tolerance_config = env.config.get("fault_tolerance", {})
        self.fault_handler = create_fault_handler_from_config(fault_tolerance_config)
        self.lifecycle_manager = create_lifecycle_manager()

        self.setup_logging_system()

        # 注入 logger 到容错管理器
        self.fault_handler.logger = self.logger
        if hasattr(self.lifecycle_manager, "logger"):
            self.lifecycle_manager.logger = self.logger  # type: ignore
        self.fault_handler.dispatcher = self

        self.logger.info(f"Dispatcher '{self.name}' construction complete")
        if fault_tolerance_config:
            strategy = fault_tolerance_config.get("strategy", "restart")
            self.logger.info(f"Fault tolerance enabled: strategy={strategy}")
        if env.platform == "remote":
            self.logger.info(f"Dispatcher '{self.name}' is running in remote mode")
            ensure_ray_initialized()

    def enable_fault_tolerance(
        self,
        heartbeat_interval: float = 5.0,
        heartbeat_timeout: float = 15.0,
        max_restart_attempts: int = 3,
    ):
        """
        启用 Remote 环境故障容错

        Args:
            heartbeat_interval: 心跳发送间隔 (秒)
            heartbeat_timeout: 心跳超时阈值 (秒)
            max_restart_attempts: 最大重启尝试次数
        """
        self.fault_tolerance_config.update(
            {
                "enabled": True,
                "heartbeat_interval": heartbeat_interval,
                "heartbeat_timeout": heartbeat_timeout,
                "max_restart_attempts": max_restart_attempts,
            }
        )

        self.logger.info(
            f"🛡️  Fault tolerance enabled: "
            f"interval={heartbeat_interval}s, timeout={heartbeat_timeout}s"
        )

    def _init_heartbeat_monitor(self):
        """
        初始化 HeartbeatMonitor 监控线程

        在所有任务创建后调用,开始心跳监控
        """
        if not self.fault_tolerance_config["enabled"]:
            return

        if self.heartbeat_monitor is not None:
            self.logger.warning("HeartbeatMonitor already initialized")
            return

        try:
            from sage.kernel.runtime.heartbeat_monitor import HeartbeatMonitor

            # 创建 HeartbeatMonitor
            self.heartbeat_monitor = HeartbeatMonitor(
                dispatcher=self,
                check_interval=self.fault_tolerance_config["heartbeat_interval"],
            )
            # 启动监控线程
            self.heartbeat_monitor.start()

            self.logger.info("🔍 HeartbeatMonitor started")

        except Exception as e:
            self.logger.error(
                f"❌ Failed to initialize HeartbeatMonitor: {e}", exc_info=True
            )

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
                    if hasattr(task.operator, "handle_stop_signal"):
                        task.operator.handle_stop_signal(stop_signal)  # type: ignore
                        self.logger.info(
                            f"Notified JoinOperator {task_name} about source {source_node_name} stopping"
                        )
                except Exception as e:
                    self.logger.error(f"Failed to notify JoinOperator {task_name}: {e}")

    def _cleanup_services_after_batch_completion(self):
        """在批处理完成后清理所有服务"""
        self.logger.info("Cleaning up services after batch completion")

        if self.remote:
            # 清理 Ray 服务 (使用生命周期管理器)
            try:
                self.lifecycle_manager.cleanup_all(
                    tasks={}, services=self.services, cleanup_timeout=5.0
                )
            except Exception as e:
                self.logger.error(f"Error cleaning up Ray services: {e}")
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
        base_dir = self.env.env_base_dir if self.env.env_base_dir is not None else "."
        self.logger = CustomLogger(
            [
                ("console", "INFO"),  # 控制台显示重要信息
                (
                    os.path.join(base_dir, "Dispatcher.log"),
                    "DEBUG",
                ),  # 详细日志
                (os.path.join(base_dir, "Error.log"), "ERROR"),  # 错误日志
            ],
            name=f"Dispatcher_{self.name}",
        )

    def start(self):
        # 第三步：启动所有服务任务
        for service_name, service_task in self.services.items():
            try:
                if hasattr(service_task, "start_running"):
                    service_task.start_running()
                elif hasattr(service_task, "_actor"):
                    # ActorWrapper包装的服务
                    import ray

                    actor_ref = service_task._actor
                    if hasattr(actor_ref, "start_running"):
                        ray.get(actor_ref.start_running.remote())  # type: ignore
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
        if self.fault_tolerance_config["enabled"] and self.remote:
            self._init_heartbeat_monitor()
        self.is_running = True

    def _create_service_context(self, service_name: str) -> "ServiceContext | None":
        """
        获取service task的ServiceContext（从execution graph中已创建的service node获取）

        Args:
            service_name: 服务名称

        Returns:
            从execution graph中获取的ServiceContext，如果未找到则返回 None
        """
        try:
            # 从execution graph的service_nodes中查找对应的service_node
            service_node = None
            for _node_name, node in self.graph.service_nodes.items():
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
        """
        编译图结构，创建节点并建立连接

        重构后的流程：
        1. 调用 Scheduler 获取调度决策
        2. 根据决策等待（如果需要延迟调度）
        3. 调用 PlacementExecutor 执行物理放置
        4. 启动所有任务
        """
        self.logger.info(f"Compiling Job for graph: {self.name}")

        # 第一步：调度所有服务任务
        for service_node_name, service_node in self.graph.service_nodes.items():
            service_name = None
            try:
                service_name = service_node.service_name

                # 为service创建专用的runtime context
                service_ctx = self._create_service_context(service_name)

                # === 新架构：Scheduler → Decision → Placement ===
                # 1. 获取调度决策
                decision = self.scheduler.make_service_decision(service_node)

                self.logger.debug(
                    f"Service scheduling decision for '{service_name}': {decision}"
                )

                # 2. 根据决策等待（如果需要延迟）
                if decision.delay > 0:
                    self.logger.debug(
                        f"Delaying service placement of '{service_name}' by {decision.delay}s"
                    )
                    time.sleep(decision.delay)

                # 3. 执行物理放置
                service_task = self.placement_executor.place_service(
                    service_node=service_node,
                    decision=decision,
                    runtime_ctx=service_ctx,
                )
                self.services[service_name] = service_task

                self.logger.debug(
                    f"Placed service task '{service_name}' of type '{service_task.__class__.__name__}'"
                )
            except Exception as e:
                error_service = service_name if service_name else service_node_name
                self.logger.error(
                    f"Failed to schedule and place service task {error_service}: {e}",
                    exc_info=True,
                )
                # 可以选择继续或停止，这里选择继续但记录错误

        # 第二步：调度所有计算任务节点
        for node_name, graph_node in self.graph.nodes.items():
            try:
                # === 新架构：Scheduler → Decision → Placement ===
                # 注入 dispatcher 引用到 context (用于容错处理)
                graph_node.ctx.dispatcher = self

                # 1. 获取调度决策
                decision = self.scheduler.make_decision(graph_node)

                self.logger.debug(
                    f"Task scheduling decision for '{node_name}': {decision}"
                )

                # 2. 根据决策等待（如果需要延迟调度）
                if decision.delay > 0:
                    self.logger.debug(
                        f"Delaying task placement of '{node_name}' by {decision.delay}s"
                    )
                    time.sleep(decision.delay)

                # 3. 执行物理放置
                task = self.placement_executor.place_task(
                    task_node=graph_node, decision=decision, runtime_ctx=graph_node.ctx
                )
                self.tasks[node_name] = task

                self.logger.debug(
                    f"Placed task '{node_name}' of type '{task.__class__.__name__}' "
                    f"on node '{decision.target_node or 'default'}'"
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to schedule and place task {node_name}: {e}", exc_info=True
                )
                raise e

        # 连接关系已经在execution graph层通过task context设置好了，无需在此处设置

        try:
            self.start()
        except Exception as e:
            self.logger.error(f"Error starting dispatcher: {e}", exc_info=True)
            raise e

    def stop(self):
        """停止所有任务和服务"""
        if self.heartbeat_monitor is not None:
            self.logger.info("🔍 Stopping HeartbeatMonitor...")
            self.heartbeat_monitor.stop()
            self.heartbeat_monitor = None

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

            for _node_name, task in self.tasks.items():
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
                    tasks=self.tasks, services=self.services, cleanup_timeout=5.0
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

    def get_task_status(self) -> dict[str, Any]:
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

    def get_service_status(self) -> dict[str, Any]:
        """获取所有服务任务的状态"""
        status = {}

        for service_name, service_task in self.services.items():
            try:
                if hasattr(service_task, "get_statistics"):
                    service_status = service_task.get_statistics()
                elif hasattr(service_task, "_actor"):
                    # ActorWrapper包装的服务
                    actor_ref = service_task._actor
                    if hasattr(actor_ref, "get_statistics"):
                        service_status = actor_ref.get_statistics()  # type: ignore
                    else:
                        service_status = {
                            "service_name": service_name,
                            "type": service_task.__class__.__name__,
                            "status": "unknown",
                        }
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

    def restart_task(self, task_id: str, restore_state: dict | None = None) -> bool:
        """
        重启任务（用于容错恢复）

        Args:
            task_id: 要重启的任务 ID
            restore_state: 可选的状态，如果提供则在启动前恢复

        Returns:
            True 如果重启成功
        """
        self.logger.info(f"🔄 Restarting task {task_id}")

        if task_id not in self.tasks:
            self.logger.error(f"❌ Task {task_id} not found")
            return False

        try:
            task = self.tasks[task_id]

            # === 步骤 1: 停止旧任务 ===
            if hasattr(task, "is_running") and task.is_running:
                self.logger.debug(f"Stopping old task {task_id}...")
                if hasattr(task, "stop"):
                    task.stop()

                # 等待任务停止
                import time

                max_wait = 5.0
                waited = 0.0
                while (
                    hasattr(task, "is_running")
                    and task.is_running
                    and waited < max_wait
                ):
                    time.sleep(0.1)
                    waited += 0.1

                if hasattr(task, "is_running") and task.is_running:
                    self.logger.warning(f"⚠️ Task {task_id} did not stop gracefully")

            # === 步骤 2: 清理旧任务资源 ===
            if hasattr(task, "cleanup"):
                try:
                    self.logger.debug(f"Cleaning up old task {task_id}...")
                    task.cleanup()
                except Exception as cleanup_error:
                    self.logger.warning(f"⚠️ Error during cleanup: {cleanup_error}")

            # === 步骤 3: 获取 graph node 并重新创建任务 ===
            graph_node = self.graph.nodes.get(task_id)
            if not graph_node:
                self.logger.error(f"❌ Graph node for {task_id} not found")
                return False

            # 重新注入 dispatcher 引用到 context
            if graph_node.ctx is not None:
                graph_node.ctx.dispatcher = self

            self.logger.debug(f"Creating new task instance for {task_id}...")

            decision = self.scheduler.make_decision(graph_node)
            new_task = self.placement_executor.place_task(
                task_node=graph_node, decision=decision, runtime_ctx=graph_node.ctx
            )

            # 替换旧任务
            self.tasks[task_id] = new_task

            self.logger.info(f"✅ New task instance created for {task_id}")

            # === 步骤 4: 如果有状态，先恢复状态 ===
            if restore_state and hasattr(new_task, "restore_state"):
                self.logger.debug(f"Restoring state for {task_id}...")
                try:
                    new_task.restore_state(restore_state)
                    self.logger.info(f"✅ State restored for task {task_id}")
                except Exception as restore_error:
                    self.logger.error(
                        f"❌ Failed to restore state for {task_id}: {restore_error}",
                        exc_info=True,
                    )
                    return False

            # === 步骤 5: 启动新任务 ===
            self.logger.debug(f"Starting new task {task_id}...")
            new_task.start_running()

            self.logger.info(f"🎉 Task {task_id} restarted successfully")
            return True

        except Exception as e:
            self.logger.error(
                f"❌ Failed to restart task {task_id}: {e}", exc_info=True
            )
            return False

    def restart_task_with_state(self, task_id: str, state: dict) -> bool:
        """
        重启任务并恢复状态（专门用于 checkpoint 恢复）

        这是 restart_task 的便捷方法，明确表示要恢复状态

        Args:
            task_id: 要重启的任务 ID
            state: 要恢复的状态

        Returns:
            True 如果重启和恢复成功
        """
        return self.restart_task(task_id, restore_state=state)
