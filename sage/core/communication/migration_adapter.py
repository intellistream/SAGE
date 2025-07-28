"""
SAGE Communication Migration Adapter

提供向后兼容的适配器，帮助现有代码平滑迁移到新的通信架构
"""

import threading
import time
from typing import Dict, Any, Optional, Callable
import logging

from sage.core.communication.message_bus import get_communication_bus, Message, MessageType
from sage.core.communication.service_base import BaseService, ServiceFunction, FunctionClient
from sage.utils.mmap_queue import SageQueue

logger = logging.getLogger(__name__)


class LegacyQueueAdapter:
    """传统queue模式的适配器"""

    def __init__(self, queue_name: str, service_name: Optional[str] = None):
        self.queue_name = queue_name
        self.service_name = service_name or queue_name
        self._client = FunctionClient(f"legacy_{queue_name}")
        self._legacy_mode = True

        # 为了兼容性，仍然创建一个SageQueue实例
        self._legacy_queue = SageQueue(queue_name)

    def put(self, data: Any, timeout: Optional[float] = None) -> bool:
        """兼容原有的put接口"""
        if self._legacy_mode:
            # 新模式：通过通信总线发送
            try:
                success = self._client.call_async(
                    service=self.service_name,
                    function="process_data",
                    payload=data
                )
                return success
            except Exception as e:
                logger.warning(f"Failed to send via communication bus: {e}, falling back to legacy queue")
                # 降级到传统queue模式
                return self._put_legacy(data, timeout)
        else:
            return self._put_legacy(data, timeout)

    def get(self, timeout: Optional[float] = None) -> Any:
        """兼容原有的get接口"""
        # 由于新架构是基于请求-响应模式，get操作需要特殊处理
        # 这里提供一个简化的实现
        return self._get_legacy(timeout)

    def _put_legacy(self, data: Any, timeout: Optional[float] = None) -> bool:
        """传统queue模式的put"""
        try:
            self._legacy_queue.put(data, timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"Legacy queue put failed: {e}")
            return False

    def _get_legacy(self, timeout: Optional[float] = None) -> Any:
        """传统queue模式的get"""
        try:
            return self._legacy_queue.get(timeout=timeout)
        except Exception as e:
            logger.error(f"Legacy queue get failed: {e}")
            return None

    def qsize(self) -> int:
        """获取队列大小"""
        return self._legacy_queue.qsize()

    def empty(self) -> bool:
        """检查队列是否为空"""
        return self._legacy_queue.empty()

    def close(self):
        """关闭适配器"""
        self._client.close()
        self._legacy_queue.close()


class ServiceAdapter(BaseService):
    """将现有服务适配到新通信架构的适配器"""

    def __init__(self, service_name: str, queue_name: str, process_function: Callable):
        super().__init__(service_name, f"{service_name}_{queue_name}")
        self.queue_name = queue_name
        self.process_function = process_function
        self._legacy_queue = SageQueue(queue_name)
        self._processing_thread = None
        self._stop_event = threading.Event()

    def initialize(self):
        """初始化服务"""
        logger.info(f"Service adapter {self.service_name} initialized for queue {self.queue_name}")

        # 启动传统queue监听线程（用于向后兼容）
        self._processing_thread = threading.Thread(target=self._legacy_queue_processor, daemon=True)
        self._processing_thread.start()

    def cleanup(self):
        """清理服务"""
        self._stop_event.set()
        if self._processing_thread:
            self._processing_thread.join(timeout=5.0)
        self._legacy_queue.close()
        logger.info(f"Service adapter {self.service_name} cleaned up")

    def _legacy_queue_processor(self):
        """处理传统queue中的消息"""
        while not self._stop_event.is_set():
            try:
                data = self._legacy_queue.get(timeout=1.0)
                if data is not None:
                    # 调用处理函数
                    result = self.process_function(data)
                    logger.debug(f"Processed legacy queue data: {data} -> {result}")
            except Exception as e:
                if not self._stop_event.is_set():
                    logger.debug(f"Legacy queue processor error: {e}")

    @ServiceFunction(name="process_data")
    def process_data(self, data: Any, message=None) -> Any:
        """处理数据（新通信架构接口）"""
        try:
            result = self.process_function(data)
            logger.debug(f"Processed data via new communication: {data} -> {result}")
            return result
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            return {"error": str(e)}


class MigrationHelper:
    """迁移辅助工具"""

    def __init__(self):
        self.adapters: Dict[str, ServiceAdapter] = {}
        self.clients: Dict[str, LegacyQueueAdapter] = {}

    def create_service_adapter(self, service_name: str, queue_name: str,
                             process_function: Callable) -> ServiceAdapter:
        """创建服务适配器"""
        adapter = ServiceAdapter(service_name, queue_name, process_function)
        adapter.start()
        adapter.initialize()

        self.adapters[queue_name] = adapter
        logger.info(f"Created service adapter for {service_name} with queue {queue_name}")
        return adapter

    def create_client_adapter(self, queue_name: str, service_name: Optional[str] = None) -> LegacyQueueAdapter:
        """创建客户端适配器"""
        adapter = LegacyQueueAdapter(queue_name, service_name)
        self.clients[queue_name] = adapter
        logger.info(f"Created client adapter for queue {queue_name}")
        return adapter

    def migrate_existing_service(self, queue_name: str, service_instance: Any):
        """迁移现有服务实例"""
        # 检查服务实例是否有处理方法
        if hasattr(service_instance, 'process') and callable(service_instance.process):
            process_func = service_instance.process
        elif hasattr(service_instance, 'handle') and callable(service_instance.handle):
            process_func = service_instance.handle
        elif hasattr(service_instance, '__call__'):
            process_func = service_instance
        else:
            raise ValueError(f"Cannot find suitable process method in service instance")

        service_name = getattr(service_instance, '__class__', 'unknown').__name__
        return self.create_service_adapter(service_name, queue_name, process_func)

    def get_migration_stats(self) -> Dict[str, Any]:
        """获取迁移统计信息"""
        return {
            "service_adapters": len(self.adapters),
            "client_adapters": len(self.clients),
            "adapter_services": list(self.adapters.keys()),
            "adapter_clients": list(self.clients.keys())
        }

    def cleanup_all(self):
        """清理所有适配器"""
        for adapter in self.adapters.values():
            adapter.cleanup()
            adapter.stop()

        for client in self.clients.values():
            client.close()

        self.adapters.clear()
        self.clients.clear()
        logger.info("All migration adapters cleaned up")


# 全局迁移辅助器
_global_migration_helper: Optional[MigrationHelper] = None
_migration_lock = threading.Lock()


def get_migration_helper() -> MigrationHelper:
    """获取全局迁移辅助器"""
    global _global_migration_helper
    with _migration_lock:
        if _global_migration_helper is None:
            _global_migration_helper = MigrationHelper()
        return _global_migration_helper


def create_queue_adapter(queue_name: str, service_name: Optional[str] = None) -> LegacyQueueAdapter:
    """创建队列适配器的便捷函数"""
    helper = get_migration_helper()
    return helper.create_client_adapter(queue_name, service_name)


def migrate_service(queue_name: str, service_instance: Any) -> ServiceAdapter:
    """迁移现有服务的便捷函数"""
    helper = get_migration_helper()
    return helper.migrate_existing_service(queue_name, service_instance)
