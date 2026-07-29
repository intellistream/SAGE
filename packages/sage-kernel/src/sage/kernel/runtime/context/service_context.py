from __future__ import annotations

import os
from typing import TYPE_CHECKING

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.runtime.context.base_context import BaseRuntimeContext

if TYPE_CHECKING:
    from sage.kernel.api.base_environment import BaseEnvironment
    from sage.kernel.runtime.graph.execution_graph import ExecutionGraph
    from sage.kernel.runtime.graph.service_node import ServiceNode
    from sage.platform.queue.base_queue_descriptor import BaseQueueDescriptor

# task, operator和function "形式上共享"的运行上下文


class ServiceContext(BaseRuntimeContext):
    # 定义不需要序列化的属性
    __state_exclude__ = ["_logger", "env", "_env_logger_cache"]

    def __init__(
        self,
        service_node: ServiceNode,
        env: BaseEnvironment,
        execution_graph: ExecutionGraph | None = None,
    ):
        super().__init__()  # Initialize base context

        self.name: str = service_node.name

        self.env_name: str = env.name
        self.env_base_dir: str | None = env.env_base_dir
        self.env_uuid: str | None = getattr(env, "uuid", None)  # 使用 getattr 以避免 AttributeError
        self.env_console_log_level = env.console_log_level  # 保存环境的控制台日志等级

        self._logger: CustomLogger | None = None

        # 队列描述符管理 - 在构造时从service_node和execution_graph获取
        self._request_queue_descriptor: BaseQueueDescriptor | None = (
            service_node.service_qd
        )  # 用于service task接收请求

        # 维护自己的service response queue descriptor (用于接收service调用的响应)
        self._own_service_response_qd: BaseQueueDescriptor | None = None
        if hasattr(service_node, "service_response_qd"):
            self._own_service_response_qd = service_node.service_response_qd

        # 提供response_qd属性以兼容ServiceManager（指向自己的service response queue）
        self.response_qd: BaseQueueDescriptor | None = self._own_service_response_qd

        # 从execution_graph的提取好的映射表获取service response队列描述符 - 简化逻辑
        self._service_response_queue_descriptors: dict[str, BaseQueueDescriptor] = {}
        if execution_graph and hasattr(execution_graph, "service_response_qds"):
            self._service_response_queue_descriptors = execution_graph.service_response_qds.copy()

        # 从execution_graph获取service request队列描述符 - 用于service-to-service调用
        self._service_request_queue_descriptors: dict[str, BaseQueueDescriptor] = {}
        if execution_graph and hasattr(execution_graph, "service_request_qds"):
            self._service_request_queue_descriptors = execution_graph.service_request_qds.copy()

        # 兼容ServiceManager - 提供service_qds属性（指向service request queue descriptors）
        self.service_qds: dict[str, BaseQueueDescriptor] = self._service_request_queue_descriptors

        # 服务调用相关 - service_manager已在BaseRuntimeContext中定义

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

    def set_request_queue_descriptor(self, descriptor: BaseQueueDescriptor):
        """设置请求队列描述符（用于service task）"""
        self._request_queue_descriptor = descriptor

    def get_request_queue_descriptor(self) -> BaseQueueDescriptor | None:
        """获取请求队列描述符"""
        return self._request_queue_descriptor

    def set_service_response_queue_descriptors(self, descriptors: dict[str, BaseQueueDescriptor]):
        """设置service response队列描述符（让service可以访问各个response队列）"""
        self._service_response_queue_descriptors = descriptors

    def get_service_response_queue_descriptors(
        self,
    ) -> dict[str, BaseQueueDescriptor]:
        """获取service response队列描述符"""
        return (
            self._service_response_queue_descriptors
            if self._service_response_queue_descriptors
            else {}
        )

    def get_service_response_queue_descriptor(self, node_name: str) -> BaseQueueDescriptor | None:
        """获取指定节点的service response队列描述符"""
        if self._service_response_queue_descriptors:
            return self._service_response_queue_descriptors.get(node_name)
        return None

    def get_service_request_queue_descriptors(self) -> dict[str, BaseQueueDescriptor]:
        """获取service request队列描述符（用于service-to-service调用）"""
        return (
            self._service_request_queue_descriptors
            if self._service_request_queue_descriptors
            else {}
        )

    def get_service_request_queue_descriptor(self, service_name: str) -> BaseQueueDescriptor | None:
        """获取指定服务的service request队列描述符"""
        if self._service_request_queue_descriptors:
            return self._service_request_queue_descriptors.get(service_name)
        return None

    def get_own_service_response_queue_descriptor(
        self,
    ) -> BaseQueueDescriptor | None:
        """获取自己的service response队列描述符（用于接收service调用的响应）"""
        return self._own_service_response_qd
