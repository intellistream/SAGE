"""
SAGE Service Base Classes

提供统一的service和function基础类，集成新的通信框架
"""

import asyncio
import threading
import time
from typing import Dict, Any, Optional, List, Callable
from abc import ABC, abstractmethod
import logging

from sage.core.communication.message_bus import (
    CommunicationBus, Message, MessageHandler, MessageType,
    CommunicationPattern, get_communication_bus
)

logger = logging.getLogger(__name__)


class ServiceFunction:
    """服务函数装饰器"""

    def __init__(self, name: Optional[str] = None, timeout: float = 30.0,
                 pattern: CommunicationPattern = CommunicationPattern.REQUEST_RESPONSE):
        self.name = name
        self.timeout = timeout
        self.pattern = pattern

    def __call__(self, func: Callable):
        func._sage_function = True
        func._sage_function_name = self.name or func.__name__
        func._sage_timeout = self.timeout
        func._sage_pattern = self.pattern
        return func


class BaseService(MessageHandler):
    """服务基类"""

    def __init__(self, service_name: str, service_id: Optional[str] = None):
        self.service_name = service_name
        self.service_id = service_id or f"{service_name}_{int(time.time())}"
        self.functions: Dict[str, Callable] = {}
        self.metadata: Dict[str, Any] = {}
        self._bus: Optional[CommunicationBus] = None
        self._running = False

        # 自动发现服务函数
        self._discover_functions()

    def _discover_functions(self):
        """自动发现带有@ServiceFunction装饰器的方法"""
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, '_sage_function'):
                func_name = attr._sage_function_name
                self.functions[func_name] = attr
                logger.info(f"Discovered function: {func_name} in service {self.service_name}")

    def start(self, bus: Optional[CommunicationBus] = None):
        """启动服务"""
        self._bus = bus or get_communication_bus()

        # 注册到通信总线
        self._bus.register_service(
            service_id=self.service_id,
            service_name=self.service_name,
            functions=list(self.functions.keys()),
            handler=self,
            metadata=self.metadata
        )

        self._running = True
        logger.info(f"Service {self.service_name} ({self.service_id}) started")

    def stop(self):
        """停止服务"""
        if self._bus:
            self._bus.unregister_service(self.service_id)

        self._running = False
        logger.info(f"Service {self.service_name} ({self.service_id}) stopped")

    async def handle_message(self, message: Message) -> Optional[Message]:
        """处理接收到的消息"""
        try:
            if message.function in self.functions:
                func = self.functions[message.function]

                # 调用函数
                if asyncio.iscoroutinefunction(func):
                    result = await func(message.payload, message=message)
                else:
                    result = func(message.payload, message=message)

                # 创建响应消息
                if message.type == MessageType.REQUEST:
                    response = Message(
                        type=MessageType.RESPONSE,
                        sender=self.service_id,
                        service=self.service_name,
                        function=message.function,
                        payload=result,
                        correlation_id=message.id
                    )
                    return response

            else:
                logger.warning(f"Function {message.function} not found in service {self.service_name}")

        except Exception as e:
            logger.error(f"Error handling message in {self.service_name}: {e}")

            # 返回错误响应
            if message.type == MessageType.REQUEST:
                error_response = Message(
                    type=MessageType.RESPONSE,
                    sender=self.service_id,
                    service=self.service_name,
                    function=message.function,
                    payload={'error': str(e)},
                    correlation_id=message.id
                )
                return error_response

        return None

    def call_function(self, target_service: str, function: str, payload: Any,
                     timeout: float = 30.0) -> Any:
        """调用其他服务的函数"""
        if not self._bus:
            raise RuntimeError("Service not started")

        return self._bus.send_request(
            service=target_service,
            function=function,
            payload=payload,
            timeout=timeout,
            sender=self.service_id
        )

    def broadcast(self, topic: str, payload: Any):
        """广播消息"""
        if not self._bus:
            raise RuntimeError("Service not started")

        self._bus.broadcast(topic, payload, sender=self.service_id)

    def subscribe(self, topic: str):
        """订阅主题"""
        if not self._bus:
            raise RuntimeError("Service not started")

        self._bus.subscribe(self.service_id, topic)

    @abstractmethod
    def initialize(self):
        """服务初始化（子类实现）"""
        pass

    @abstractmethod
    def cleanup(self):
        """服务清理（子类实现）"""
        pass


class FunctionClient:
    """函数客户端，用于调用远程service函数"""

    def __init__(self, client_id: Optional[str] = None, bus: Optional[CommunicationBus] = None):
        self.client_id = client_id or f"client_{int(time.time())}"
        self._bus = bus or get_communication_bus()

        # 注册客户端（作为一个特殊的服务）
        self._bus.register_service(
            service_id=self.client_id,
            service_name="function_client",
            functions=[],
            metadata={'type': 'client'}
        )

    def call(self, service: str, function: str, payload: Any, timeout: float = 30.0) -> Any:
        """调用远程函数"""
        return self._bus.send_request(
            service=service,
            function=function,
            payload=payload,
            timeout=timeout,
            sender=self.client_id
        )

    def call_async(self, service: str, function: str, payload: Any) -> bool:
        """异步调用远程函数（不等待响应）"""
        message = Message(
            type=MessageType.NOTIFICATION,
            sender=self.client_id,
            service=service,
            function=function,
            payload=payload
        )
        return self._bus.send_message(message, CommunicationPattern.POINT_TO_POINT)

    def broadcast(self, topic: str, payload: Any):
        """广播消息"""
        self._bus.broadcast(topic, payload, sender=self.client_id)

    def list_services(self) -> List[Dict[str, Any]]:
        """列出所有可用服务"""
        services = self._bus.router.list_services()
        return [
            {
                'service_id': s.service_id,
                'service_name': s.service_name,
                'functions': list(s.functions),
                'metadata': s.metadata
            }
            for s in services
        ]

    def list_functions(self) -> Dict[str, List[str]]:
        """列出所有可用函数"""
        return self._bus.router.list_functions()

    def close(self):
        """关闭客户端"""
        self._bus.unregister_service(self.client_id)


class ServiceManager:
    """服务管理器"""

    def __init__(self):
        self.services: Dict[str, BaseService] = {}
        self._bus = get_communication_bus()

    def register_service(self, service: BaseService) -> str:
        """注册并启动服务"""
        service.start(self._bus)
        self.services[service.service_id] = service
        return service.service_id

    def unregister_service(self, service_id: str):
        """注销并停止服务"""
        if service_id in self.services:
            service = self.services[service_id]
            service.stop()
            del self.services[service_id]

    def get_service(self, service_id: str) -> Optional[BaseService]:
        """获取服务实例"""
        return self.services.get(service_id)

    def list_services(self) -> List[str]:
        """列出所有服务ID"""
        return list(self.services.keys())

    def stop_all(self):
        """停止所有服务"""
        for service in list(self.services.values()):
            service.stop()
        self.services.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取管理器统计信息"""
        return {
            'local_services': len(self.services),
            'bus_stats': self._bus.get_stats()
        }


# 全局服务管理器
_global_service_manager: Optional[ServiceManager] = None
_manager_lock = threading.Lock()


def get_service_manager() -> ServiceManager:
    """获取全局服务管理器"""
    global _global_service_manager
    with _manager_lock:
        if _global_service_manager is None:
            _global_service_manager = ServiceManager()
        return _global_service_manager
