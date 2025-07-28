"""
SAGE Service Communication Framework

统一的service和function通信架构，提供消息路由、负载均衡和监控功能
"""

import uuid
import time
import threading
from typing import Dict, Any, Optional, Callable, List, Set
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging

from sage.utils.mmap_queue import SageQueue, SageQueueRef

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型"""
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    NOTIFICATION = "notification"
    HEARTBEAT = "heartbeat"


class CommunicationPattern(Enum):
    """通信模式"""
    POINT_TO_POINT = "p2p"          # 点对点
    REQUEST_RESPONSE = "req_resp"    # 请求-响应
    PUBLISH_SUBSCRIBE = "pub_sub"    # 发布-订阅
    LOAD_BALANCED = "load_balanced"  # 负载均衡


@dataclass
class Message:
    """统一消息格式"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.REQUEST
    sender: str = ""
    receiver: str = ""
    service: str = ""
    function: str = ""
    payload: Any = None
    timestamp: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    headers: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'type': self.type.value,
            'sender': self.sender,
            'receiver': self.receiver,
            'service': self.service,
            'function': self.function,
            'payload': self.payload,
            'timestamp': self.timestamp,
            'correlation_id': self.correlation_id,
            'reply_to': self.reply_to,
            'headers': self.headers
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """从字典创建消息"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            type=MessageType(data.get('type', MessageType.REQUEST.value)),
            sender=data.get('sender', ''),
            receiver=data.get('receiver', ''),
            service=data.get('service', ''),
            function=data.get('function', ''),
            payload=data.get('payload'),
            timestamp=data.get('timestamp', time.time()),
            correlation_id=data.get('correlation_id'),
            reply_to=data.get('reply_to'),
            headers=data.get('headers', {})
        )


class MessageHandler(ABC):
    """消息处理器接口"""

    @abstractmethod
    async def handle_message(self, message: Message) -> Optional[Message]:
        """处理消息并返回可选的响应"""
        pass


@dataclass
class ServiceEndpoint:
    """服务端点信息"""
    service_id: str
    service_name: str
    functions: Set[str] = field(default_factory=set)
    queue_name: str = ""
    last_heartbeat: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.queue_name:
            self.queue_name = f"service_{self.service_id}"


class MessageRouter:
    """消息路由器"""

    def __init__(self):
        self._endpoints: Dict[str, ServiceEndpoint] = {}
        self._function_registry: Dict[str, List[str]] = {}  # function -> list of service_ids
        self._subscribers: Dict[str, List[str]] = {}  # topic -> list of service_ids
        self._lock = threading.RLock()

    def register_service(self, endpoint: ServiceEndpoint):
        """注册服务端点"""
        with self._lock:
            self._endpoints[endpoint.service_id] = endpoint

            # 注册函数映射
            for func in endpoint.functions:
                if func not in self._function_registry:
                    self._function_registry[func] = []
                if endpoint.service_id not in self._function_registry[func]:
                    self._function_registry[func].append(endpoint.service_id)

            logger.info(f"Registered service: {endpoint.service_name} ({endpoint.service_id})")

    def unregister_service(self, service_id: str):
        """注销服务端点"""
        with self._lock:
            if service_id in self._endpoints:
                endpoint = self._endpoints[service_id]

                # 清理函数映射
                for func in endpoint.functions:
                    if func in self._function_registry:
                        if service_id in self._function_registry[func]:
                            self._function_registry[func].remove(service_id)
                        if not self._function_registry[func]:
                            del self._function_registry[func]

                del self._endpoints[service_id]
                logger.info(f"Unregistered service: {service_id}")

    def route_message(self, message: Message, pattern: CommunicationPattern = CommunicationPattern.POINT_TO_POINT) -> List[str]:
        """路由消息，返回目标服务ID列表"""
        with self._lock:
            targets = []

            if pattern == CommunicationPattern.POINT_TO_POINT:
                # 直接路由到指定接收者
                if message.receiver and message.receiver in self._endpoints:
                    targets.append(message.receiver)

            elif pattern == CommunicationPattern.REQUEST_RESPONSE:
                # 根据function路由到最佳服务
                if message.function and message.function in self._function_registry:
                    # 简单的负载均衡：选择第一个可用的服务
                    service_ids = self._function_registry[message.function]
                    if service_ids:
                        targets.append(service_ids[0])

            elif pattern == CommunicationPattern.LOAD_BALANCED:
                # 负载均衡路由
                if message.function and message.function in self._function_registry:
                    service_ids = self._function_registry[message.function]
                    # 简单轮询或基于负载的选择
                    if service_ids:
                        # 这里可以实现更复杂的负载均衡算法
                        targets.append(min(service_ids, key=lambda sid: self._get_service_load(sid)))

            elif pattern == CommunicationPattern.PUBLISH_SUBSCRIBE:
                # 发布-订阅模式
                topic = message.headers.get('topic', message.function)
                if topic and topic in self._subscribers:
                    targets.extend(self._subscribers[topic])

            return targets

    def _get_service_load(self, service_id: str) -> float:
        """获取服务负载（简化实现）"""
        # 这里可以实现真实的负载监控
        return 0.5

    def subscribe(self, service_id: str, topic: str):
        """订阅主题"""
        with self._lock:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            if service_id not in self._subscribers[topic]:
                self._subscribers[topic].append(service_id)

    def unsubscribe(self, service_id: str, topic: str):
        """取消订阅"""
        with self._lock:
            if topic in self._subscribers and service_id in self._subscribers[topic]:
                self._subscribers[topic].remove(service_id)
                if not self._subscribers[topic]:
                    del self._subscribers[topic]

    def get_service_info(self, service_id: str) -> Optional[ServiceEndpoint]:
        """获取服务信息"""
        return self._endpoints.get(service_id)

    def list_services(self) -> List[ServiceEndpoint]:
        """列出所有服务"""
        return list(self._endpoints.values())

    def list_functions(self) -> Dict[str, List[str]]:
        """列出所有函数及其服务"""
        return dict(self._function_registry)


class CommunicationBus:
    """统一通信总线"""

    def __init__(self, bus_name: str = "sage_bus"):
        self.bus_name = bus_name
        self.router = MessageRouter()
        self._message_queue = SageQueue(f"{bus_name}_messages", maxsize=10*1024*1024)
        self._response_queues: Dict[str, SageQueue] = {}
        self._handlers: Dict[str, MessageHandler] = {}
        self._running = False
        self._dispatcher_thread = None
        self._lock = threading.RLock()

    def start(self):
        """启动通信总线"""
        if not self._running:
            self._running = True
            self._dispatcher_thread = threading.Thread(target=self._message_dispatcher, daemon=True)
            self._dispatcher_thread.start()
            logger.info(f"Communication bus '{self.bus_name}' started")

    def stop(self):
        """停止通信总线"""
        self._running = False
        if self._dispatcher_thread:
            self._dispatcher_thread.join(timeout=5.0)

        # 清理资源
        self._message_queue.close()
        for queue in self._response_queues.values():
            queue.close()

        logger.info(f"Communication bus '{self.bus_name}' stopped")

    def register_service(self, service_id: str, service_name: str, functions: List[str],
                        handler: Optional[MessageHandler] = None, metadata: Dict[str, Any] = None):
        """注册服务"""
        endpoint = ServiceEndpoint(
            service_id=service_id,
            service_name=service_name,
            functions=set(functions),
            metadata=metadata or {}
        )

        self.router.register_service(endpoint)

        if handler:
            self._handlers[service_id] = handler

        # 创建服务专用的响应队列
        if service_id not in self._response_queues:
            self._response_queues[service_id] = SageQueue(
                f"{self.bus_name}_resp_{service_id}",
                maxsize=1024*1024
            )

    def unregister_service(self, service_id: str):
        """注销服务"""
        self.router.unregister_service(service_id)
        self._handlers.pop(service_id, None)

        # 清理响应队列
        if service_id in self._response_queues:
            self._response_queues[service_id].close()
            del self._response_queues[service_id]

    def send_message(self, message: Message, pattern: CommunicationPattern = CommunicationPattern.REQUEST_RESPONSE) -> bool:
        """发送消息"""
        try:
            # 路由消息
            targets = self.router.route_message(message, pattern)
            if not targets:
                logger.warning(f"No targets found for message: {message.function}")
                return False

            # 发送到目标服务
            for target in targets:
                message.receiver = target
                serialized = self._serialize_message(message)
                self._message_queue.put(serialized, timeout=1.0)

            return True

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    def send_request(self, service: str, function: str, payload: Any,
                    timeout: float = 30.0, sender: str = "") -> Optional[Any]:
        """发送请求并等待响应"""
        message = Message(
            type=MessageType.REQUEST,
            sender=sender,
            service=service,
            function=function,
            payload=payload,
            reply_to=sender
        )

        # 发送请求
        if not self.send_message(message, CommunicationPattern.REQUEST_RESPONSE):
            return None

        # 等待响应
        if sender and sender in self._response_queues:
            try:
                response_data = self._response_queues[sender].get(timeout=timeout)
                response = self._deserialize_message(response_data)
                if response.correlation_id == message.id:
                    return response.payload
            except Exception as e:
                logger.error(f"Failed to receive response: {e}")

        return None

    def broadcast(self, topic: str, payload: Any, sender: str = ""):
        """广播消息"""
        message = Message(
            type=MessageType.BROADCAST,
            sender=sender,
            function=topic,
            payload=payload,
            headers={'topic': topic}
        )

        self.send_message(message, CommunicationPattern.PUBLISH_SUBSCRIBE)

    def subscribe(self, service_id: str, topic: str):
        """订阅主题"""
        self.router.subscribe(service_id, topic)

    def _message_dispatcher(self):
        """消息分发器"""
        while self._running:
            try:
                # 从主消息队列获取消息
                serialized = self._message_queue.get(timeout=1.0)
                message = self._deserialize_message(serialized)

                # 分发到目标服务的处理器
                if message.receiver in self._handlers:
                    handler = self._handlers[message.receiver]
                    try:
                        response = handler.handle_message(message)

                        # 如果有响应且需要回复
                        if response and message.reply_to:
                            response.correlation_id = message.id
                            response.receiver = message.reply_to

                            if message.reply_to in self._response_queues:
                                response_data = self._serialize_message(response)
                                self._response_queues[message.reply_to].put(response_data, timeout=1.0)

                    except Exception as e:
                        logger.error(f"Handler error for service {message.receiver}: {e}")

            except Exception as e:
                if self._running:  # 只在运行时记录错误
                    logger.debug(f"Message dispatcher error: {e}")

    def _serialize_message(self, message: Message) -> bytes:
        """序列化消息"""
        import pickle
        return pickle.dumps(message.to_dict())

    def _deserialize_message(self, data: bytes) -> Message:
        """反序列化消息"""
        import pickle
        message_dict = pickle.loads(data)
        return Message.from_dict(message_dict)

    def get_stats(self) -> Dict[str, Any]:
        """获取通信统计信息"""
        return {
            'services': len(self.router._endpoints),
            'functions': len(self.router._function_registry),
            'subscribers': len(self.router._subscribers),
            'message_queue_size': self._message_queue.qsize(),
            'response_queues': len(self._response_queues)
        }


# 全局通信总线实例
_global_bus: Optional[CommunicationBus] = None
_bus_lock = threading.Lock()


def get_communication_bus(bus_name: str = "sage_bus") -> CommunicationBus:
    """获取全局通信总线实例"""
    global _global_bus
    with _bus_lock:
        if _global_bus is None:
            _global_bus = CommunicationBus(bus_name)
            _global_bus.start()
        return _global_bus


def shutdown_communication_bus():
    """关闭全局通信总线"""
    global _global_bus
    with _bus_lock:
        if _global_bus:
            _global_bus.stop()
            _global_bus = None
