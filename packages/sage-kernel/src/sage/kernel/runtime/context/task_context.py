import os
import threading
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.runtime.communication.router.connection import Connection
from sage.kernel.runtime.communication.router.packet import StopSignal
from sage.kernel.runtime.communication.router.router import BaseRouter
from sage.kernel.runtime.context.base_context import BaseRuntimeContext

if TYPE_CHECKING:
    from sage.kernel.api.base_environment import BaseEnvironment
    from sage.kernel.api.transformation.base_transformation import BaseTransformation
    from sage.kernel.runtime.communication.router.packet import Packet
    from sage.kernel.runtime.graph.execution_graph import ExecutionGraph
    from sage.kernel.runtime.graph.graph_node import TaskNode
    from sage.platform.queue.base_queue_descriptor import (
        BaseQueueDescriptor,
    )
# task, operator和function "形式上共享"的运行上下文


class TaskContext(BaseRuntimeContext):
    # 定义不需要序列化的属性
    __state_exclude__ = ["_logger", "env", "_env_logger_cache"]

    def __init__(
        self,
        graph_node: "TaskNode",
        transformation: "BaseTransformation",
        env: "BaseEnvironment",
        execution_graph: "ExecutionGraph | None" = None,
    ):
        super().__init__()  # Initialize base context

        self.name: str = graph_node.name

        self.env_name = env.name
        self.env_base_dir: str | None = env.env_base_dir
        self.env_uuid = getattr(env, "uuid", None)  # 使用 getattr 以避免 AttributeError
        self.env_console_log_level = env.console_log_level  # 保存环境的控制台日志等级

        # 性能监控配置
        self.enable_monitoring: bool = getattr(env, "enable_monitoring", False)

        self.parallel_index: int = graph_node.parallel_index
        self.parallelism: int = graph_node.parallelism

        self._logger: Optional[CustomLogger] = None

        self.is_spout = transformation.is_spout

        self.delay = 0.01
        self.stop_signal_num = graph_node.stop_signal_num

        # 保存JobManager的网络地址信息而不是直接引用
        self.jobmanager_host = getattr(env, "jobmanager_host", "127.0.0.1")
        self.jobmanager_port = getattr(env, "jobmanager_port", 19001)

        # 为本地环境保存JobManager的弱引用
        self._local_jobmanager_ref: Any
        if hasattr(env, "_jobmanager") and env._jobmanager is not None:
            import weakref

            self._local_jobmanager_ref = weakref.ref(env._jobmanager)
        else:
            self._local_jobmanager_ref = None

        # 这些属性将在task层初始化，避免序列化问题
        self._stop_event: Optional[threading.Event] = None  # 延迟初始化
        self.received_stop_signals = None  # 延迟初始化
        self.stop_signal_count = 0

        # 服务相关 - service_manager已在BaseRuntimeContext中定义
        self._service_names: Optional[Dict[str, str]] = (
            None  # 只保存服务名称映射而不是实例
        )

        # 队列描述符管理 - 在构造时从graph_node和execution_graph获取
        self.input_qd: "BaseQueueDescriptor" = graph_node.input_qd
        self.response_qd: "BaseQueueDescriptor" = graph_node.service_response_qd

        # 从execution_graph的提取好的映射表获取service队列描述符 - 简化逻辑
        self.service_qds: Dict[str, "BaseQueueDescriptor"] = {}
        if execution_graph and hasattr(execution_graph, "service_request_qds"):
            self.service_qds = execution_graph.service_request_qds.copy()

        # 下游连接组管理 - 从execution_graph构建downstream_groups
        self.downstream_groups: Dict[int, Dict[int, "Connection"]] = {}
        if execution_graph:
            self._build_downstream_groups(graph_node, execution_graph)

        self.dispatcher: Any = None  # 延迟注入，避免循环依赖

    def _build_downstream_groups(
        self, graph_node: "TaskNode", execution_graph: "ExecutionGraph"
    ):
        """从execution_graph构建downstream_groups"""
        # 遍历输出通道，构建downstream_groups
        for broadcast_index, output_group in enumerate(graph_node.output_channels):
            if output_group:  # 确保输出组不为空
                self.downstream_groups[broadcast_index] = {}

                for edge in output_group:
                    if edge.downstream_node and edge.downstream_node.input_qd:
                        # 使用下游节点的单一输入队列描述符
                        downstream_queue_descriptor = edge.downstream_node.input_qd

                        # 创建Connection对象

                        connection = Connection(
                            broadcast_index=broadcast_index,
                            parallel_index=edge.downstream_node.parallel_index,
                            target_name=edge.downstream_node.name,
                            queue_descriptor=downstream_queue_descriptor,
                            target_input_index=edge.input_index,
                        )

                        # 使用downstream node的parallel_index作为key
                        self.downstream_groups[broadcast_index][
                            edge.downstream_node.parallel_index
                        ] = connection

    def cleanup(self):
        """清理运行时上下文资源"""
        self.cleanup_service_manager()  # 使用基类的清理方法

    @property
    def router(self):
        if hasattr(self, "_router") and self._router is not None:
            return self._router
        else:
            self._router = BaseRouter(self)
            return self._router

    @property
    def logger(self) -> CustomLogger:
        """懒加载logger"""
        if self._logger is None:
            base_dir = self.env_base_dir if self.env_base_dir is not None else "."
            self._logger = CustomLogger(
                [
                    (
                        "console",
                        self.env_console_log_level,
                    ),  # 使用环境设置的控制台日志等级
                    (
                        os.path.join(base_dir, f"{self.name}_debug.log"),
                        "DEBUG",
                    ),  # 详细日志
                    (os.path.join(base_dir, "Error.log"), "ERROR"),  # 错误日志
                    (
                        os.path.join(base_dir, f"{self.name}_info.log"),
                        "INFO",
                    ),  # 错误日志
                ],
                name=f"{self.name}",
            )
        return self._logger

    def get_service(self, service_name: str) -> Any:
        """
        获取服务实例，通过service_manager获取

        Args:
            service_name: 服务名称

        Returns:
            服务实例

        Raises:
            ValueError: 当服务不存在时
        """
        if self._service_names is None:
            raise RuntimeError("Services not available - dispatcher not initialized")

        if service_name not in self._service_names:
            available_services = list(self._service_names.keys())
            raise ValueError(
                f"Service '{service_name}' not found. Available services: {available_services}"
            )

        # 通过service_manager获取实际的服务队列
        return self.service_manager._get_service_queue(service_name)

    @property
    def stop_event(self) -> threading.Event:
        """获取共享的停止事件，延迟初始化"""
        if self._stop_event is None:
            self._stop_event = threading.Event()
        return self._stop_event

    def set_stop_signal(self):
        self.stop_event.set()

    def is_stop_requested(self) -> bool:
        return self.stop_event.is_set()

    def clear_stop_signal(self):
        self.stop_event.clear()

    def request_stop(self):
        """
        请求停止当前任务，向JobManager发送停止信号
        """
        self.send_stop_signal_back(self.name)

    def send_stop_signal_back(self, node_name: str):
        """
        通过网络向JobManager发送节点停止信号
        支持本地和远程(Ray Actor)环境
        """
        try:
            # 检查是否为本地环境 - 如果jobmanager_host是localhost相关，尝试直接调用
            if self.jobmanager_host in ["127.0.0.1", "localhost"] and hasattr(
                self, "_local_jobmanager_ref"
            ):
                # 直接调用本地JobManager实例
                self.logger.info(
                    f"Task {node_name} sending stop signal directly to local JobManager"
                )
                local_jobmanager = self._local_jobmanager_ref()
                if local_jobmanager:
                    local_jobmanager.receive_node_stop_signal(self.env_uuid, node_name)
                    self.logger.info(
                        "Successfully sent stop signal to local JobManager"
                    )
                    return

            # 导入JobManagerClient来发送网络请求
            from sage.kernel.runtime.jobmanager_client import JobManagerClient

            self.logger.info(
                f"Task {node_name} sending stop signal back to JobManager at {self.jobmanager_host}:{self.jobmanager_port}"
            )

            # 创建客户端并发送停止信号
            client = JobManagerClient(
                host=self.jobmanager_host, port=self.jobmanager_port
            )
            env_uuid = self.env_uuid if self.env_uuid is not None else ""
            response = client.receive_node_stop_signal(env_uuid, node_name)

            if response.get("status") == "success":
                self.logger.debug(f"Successfully sent stop signal for node {node_name}")
            else:
                self.logger.warning(f"JobManager response: {response}")

        except Exception as e:
            self.logger.error(
                f"Failed to send stop signal back for node {node_name}: {e}",
                exc_info=True,
            )

    def handle_stop_signal(self, signal: StopSignal):
        """Handle the received stop signal."""
        source_node = signal.name
        self.logger.info(f"Task {self.name} received stop signal from {source_node}")

        # Check if this is a JoinOperator that should handle stop signals specially
        if hasattr(self, "operator") and hasattr(self.operator, "handle_stop_signal"):
            # Let the operator handle the stop signal itself
            self.operator.handle_stop_signal(signal=signal)
            return

        # Initialize stop signal tracking attributes if they don't exist
        if not hasattr(self, "num_expected_stop_signals"):
            # 对于某些类型的操作符，我们需要等待多个停止信号
            # 特别是对于那些可能有多个上游输入的操作符
            operator_name = getattr(self, "name", "")
            if "KeyBy" in operator_name and "_1" in operator_name:
                # 这是一个合并了多个输入的KeyBy节点，等待2个停止信号
                self.num_expected_stop_signals = 2
                self.logger.info(
                    f"Task {self.name} (KeyBy merge node) expecting 2 stop signals"
                )
            else:
                self.num_expected_stop_signals = 0
        if not hasattr(self, "stop_signals_received"):
            self.stop_signals_received = set()

        if self.num_expected_stop_signals > 0:
            self.stop_signals_received.add(source_node)
            self.logger.info(
                f"Task {self.name} received stop signals ({len(self.stop_signals_received)}/{self.num_expected_stop_signals}) from: {list(self.stop_signals_received)}"
            )

            if len(self.stop_signals_received) >= self.num_expected_stop_signals:
                self.logger.info(
                    f"Task {self.name} received all expected stop signals, requesting stop and forwarding signal"
                )
                # Send stop signal to job manager
                self.request_stop()

                # Forward the signal to downstream nodes
                if hasattr(self, "router") and self.router:
                    self.router.send_stop_signal(signal)
            else:
                self.logger.info(f"Task {self.name} waiting for more stop signals")
                # 不要停止或转发信号，继续等待
                return
        else:
            # No specific number expected, just forward the signal
            self.logger.info(
                f"Task {self.name} forwarding stop signal from {source_node}"
            )

            # Send stop signal to job manager
            self.request_stop()

            # Forward the signal to downstream nodes
            if hasattr(self, "router") and self.router:
                self.router.send_stop_signal(signal)

    def __del__(self):
        """析构函数 - 确保资源被正确清理"""
        try:
            self.cleanup()
        except Exception:
            # 在析构函数中不记录错误，避免在程序退出时产生问题
            pass

    # ================== 路由接口 - 封装BaseRouter功能 ==================

    def _get_router(self):
        """延迟初始化router，避免直接暴露BaseRouter给core组件"""
        if not hasattr(self, "_router") or self._router is None:
            from sage.kernel.runtime.communication.router.router import BaseRouter

            self._router = BaseRouter(self)
            self.logger.debug(f"Initialized router for TaskContext {self.name}")
        return self._router

    def send_packet(self, packet: "Packet") -> bool:
        """
        通过TaskContext发送数据包，隐藏BaseRouter实现细节
        这是核心API组件与kernel通信的统一接口
        """
        try:
            router = self._get_router()
            return router.send(packet)
        except Exception as e:
            self.logger.error(f"Failed to send packet through TaskContext: {e}")
            return False

    def send_stop_signal(self, stop_signal: "StopSignal") -> None:
        """
        通过TaskContext发送停止信号，隐藏BaseRouter实现细节
        """
        try:
            router = self._get_router()
            router.send_stop_signal(stop_signal)
            self.logger.debug("Sent stop signal through TaskContext")
        except Exception as e:
            self.logger.error(f"Failed to send stop signal through TaskContext: {e}")

    def get_routing_info(self) -> Dict[str, Any]:
        """
        获取路由连接信息，提供给上层调试和监控
        """
        try:
            router = self._get_router()
            return router.get_connections_info()
        except Exception as e:
            self.logger.error(f"Failed to get routing info: {e}")
            return {}

    # ================== 队列描述符管理方法 ==================

    def set_input_queue_descriptor(self, descriptor: "BaseQueueDescriptor"):
        """设置输入队列描述符"""
        self.input_qd = descriptor

    def get_input_queue_descriptor(self) -> Optional["BaseQueueDescriptor"]:
        """获取输入队列描述符"""
        return self.input_qd

    def set_service_response_queue_descriptor(self, descriptor: "BaseQueueDescriptor"):
        """设置服务响应队列描述符"""
        self._service_response_queue_descriptor = descriptor
        self.response_qd = descriptor

    def get_service_response_queue_descriptor(self) -> Optional["BaseQueueDescriptor"]:
        """获取服务响应队列描述符"""
        return self._service_response_queue_descriptor

    def set_upstream_queue_descriptors(
        self, descriptors: Dict[int, List["BaseQueueDescriptor"]]
    ):
        """设置上游队列描述符映射"""
        self._upstream_queue_descriptors = descriptors

    def get_upstream_queue_descriptors(
        self,
    ) -> Optional[Dict[int, List["BaseQueueDescriptor"]]]:
        """获取上游队列描述符映射"""
        return self._upstream_queue_descriptors

    def set_downstream_queue_descriptors(
        self, descriptors: List[List["BaseQueueDescriptor"]]
    ):
        """设置下游队列描述符映射"""
        self._downstream_queue_descriptors = descriptors
        self.downstream_qds = descriptors

    def get_downstream_queue_descriptors(
        self,
    ) -> Optional[List[List["BaseQueueDescriptor"]]]:
        """获取下游队列描述符映射"""
        return self._downstream_queue_descriptors

    def set_service_request_queue_descriptors(
        self, descriptors: Dict[str, "BaseQueueDescriptor"]
    ):
        """设置服务请求队列描述符映射"""
        self._service_request_queue_descriptors = descriptors
        self.service_qds = descriptors

    def get_service_request_queue_descriptors(
        self,
    ) -> Optional[Dict[str, "BaseQueueDescriptor"]]:
        """获取服务请求队列描述符映射"""
        return self._service_request_queue_descriptors
