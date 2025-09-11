"""
KV Service - 键值存储微服务
提供键值存储功能的服务任务，集成到SAGE DAG中
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sage.core.api.service.base_service import BaseService

if TYPE_CHECKING:
    from sage.core.factory.service_factory import ServiceFactory
    from sage.kernel import ServiceContext


@dataclass
class KVConfig:
    """KV服务配置"""

    backend_type: str = "memory"  # "memory" 或 "redis"
    redis_url: Optional[str] = None
    max_size: int = 10000
    ttl_seconds: Optional[int] = None


class MemoryKVBackend:
    """内存KV后端"""

    def __init__(self, max_size: int = 10000, ttl_seconds: Optional[int] = None):
        self.store: Dict[str, Any] = {}
        self.timestamps: Dict[str, float] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.logger = logging.getLogger(__name__)

    def get(self, key: str) -> Optional[Any]:
        """获取值"""
        if self._is_expired(key):
            self.delete(key)
            return None
        return self.store.get(key)

    def put(self, key: str, value: Any) -> bool:
        """存储值"""
        try:
            if len(self.store) >= self.max_size and key not in self.store:
                # 清理过期项或最老的项
                self._evict_if_needed()

            self.store[key] = value
            self.timestamps[key] = time.time()
            return True
        except Exception as e:
            self.logger.error(f"Error storing key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除值"""
        removed = key in self.store
        self.store.pop(key, None)
        self.timestamps.pop(key, None)
        return removed

    def list_keys(self, prefix: str = "") -> List[str]:
        """列出所有键"""
        # 先清理过期键
        expired_keys = [k for k in self.store.keys() if self._is_expired(k)]
        for k in expired_keys:
            self.delete(k)

        if prefix:
            return [k for k in self.store.keys() if k.startswith(prefix)]
        return list(self.store.keys())

    def size(self) -> int:
        """获取存储大小"""
        return len(self.store)

    def clear(self) -> None:
        """清空存储"""
        self.store.clear()
        self.timestamps.clear()

    def _is_expired(self, key: str) -> bool:
        """检查键是否过期"""
        if self.ttl_seconds is None:
            return False

        timestamp = self.timestamps.get(key)
        if timestamp is None:
            return True

        return time.time() - timestamp > self.ttl_seconds

    def _evict_if_needed(self):
        """在需要时清理存储"""
        # 先尝试清理过期项
        expired_keys = [k for k in self.store.keys() if self._is_expired(k)]
        for k in expired_keys:
            self.delete(k)

        # 如果还是太满，删除最老的项
        if len(self.store) >= self.max_size:
            # 按时间排序，删除最老的
            sorted_keys = sorted(self.timestamps.items(), key=lambda x: x[1])
            keys_to_remove = len(sorted_keys) - self.max_size + 1
            for key, _ in sorted_keys[:keys_to_remove]:
                self.delete(key)


class RedisKVBackend:
    """Redis KV后端"""

    def __init__(self, redis_url: str, ttl_seconds: Optional[int] = None):
        try:
            import redis

            self.redis_client = redis.from_url(redis_url)
            self.ttl_seconds = ttl_seconds
            self.logger = logging.getLogger(__name__)

            # 测试连接
            self.redis_client.ping()
            self.logger.info(f"Connected to Redis: {redis_url}")
        except ImportError:
            raise ImportError("Redis package not installed. Run: pip install redis")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Redis: {e}")

    def get(self, key: str) -> Optional[Any]:
        """获取值"""
        try:
            value = self.redis_client.get(key)
            if value is None:
                return None
            return json.loads(value.decode("utf-8"))
        except Exception as e:
            self.logger.error(f"Error getting key {key}: {e}")
            return None

    def put(self, key: str, value: Any) -> bool:
        """存储值"""
        try:
            serialized = json.dumps(value, ensure_ascii=False)
            if self.ttl_seconds:
                return self.redis_client.setex(key, self.ttl_seconds, serialized)
            else:
                return self.redis_client.set(key, serialized)
        except Exception as e:
            self.logger.error(f"Error storing key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除值"""
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            self.logger.error(f"Error deleting key {key}: {e}")
            return False

    def list_keys(self, prefix: str = "") -> List[str]:
        """列出所有键"""
        try:
            pattern = f"{prefix}*" if prefix else "*"
            keys = self.redis_client.keys(pattern)
            return [key.decode("utf-8") for key in keys]
        except Exception as e:
            self.logger.error(f"Error listing keys: {e}")
            return []

    def size(self) -> int:
        """获取数据库大小"""
        try:
            return self.redis_client.dbsize()
        except Exception as e:
            self.logger.error(f"Error getting size: {e}")
            return 0

    def clear(self) -> None:
        """清空数据库"""
        try:
            self.redis_client.flushdb()
        except Exception as e:
            self.logger.error(f"Error clearing database: {e}")


class KVService(BaseService):
    """
    KV服务任务

    提供键值存储功能，可以在SAGE DAG中作为服务节点使用
    支持内存和Redis后端
    """

    def __init__(self, service_factory: "ServiceFactory", ctx: "ServiceContext" = None):
        super().__init__(service_factory, ctx)

        # 从service_factory获取配置
        self.config: KVConfig = getattr(service_factory, "config", KVConfig())

        # 初始化后端
        if self.config.backend_type == "redis":
            if not self.config.redis_url:
                raise ValueError("Redis URL required for Redis backend")
            self.backend = RedisKVBackend(
                self.config.redis_url, self.config.ttl_seconds
            )
            self.logger.info(
                f"KV Service '{self.service_name}' initialized with Redis backend"
            )
        else:
            self.backend = MemoryKVBackend(
                self.config.max_size, self.config.ttl_seconds
            )
            self.logger.info(
                f"KV Service '{self.service_name}' initialized with memory backend"
            )

    def _start_service_instance(self):
        """启动KV服务实例"""
        self.logger.info(f"KV Service '{self.service_name}' started")

    def _stop_service_instance(self):
        """停止KV服务实例"""
        self.logger.info(f"KV Service '{self.service_name}' stopped")

    # KV操作方法 - 这些方法可以通过服务调用机制被调用

    def get(self, key: str) -> Optional[Any]:
        """获取键值"""
        self.logger.debug(f"GET key: {key}")
        result = self.backend.get(key)
        self.logger.debug(f"GET result: {result is not None}")
        return result

    def put(self, key: str, value: Any) -> bool:
        """存储键值"""
        self.logger.debug(f"PUT key: {key}")
        result = self.backend.put(key, value)
        self.logger.debug(f"PUT result: {result}")
        return result

    def delete(self, key: str) -> bool:
        """删除键值"""
        self.logger.debug(f"DELETE key: {key}")
        result = self.backend.delete(key)
        self.logger.debug(f"DELETE result: {result}")
        return result

    def list_keys(self, prefix: str = "") -> List[str]:
        """列出键"""
        self.logger.debug(f"LIST keys with prefix: {prefix}")
        result = self.backend.list_keys(prefix)
        self.logger.debug(f"LIST result: {len(result)} keys")
        return result

    def size(self) -> int:
        """获取存储大小"""
        result = self.backend.size()
        self.logger.debug(f"SIZE result: {result}")
        return result

    def clear(self) -> None:
        """清空存储"""
        self.logger.debug("CLEAR storage")
        self.backend.clear()

    def stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        base_stats = self.get_statistics()
        kv_stats = {
            "backend_type": self.config.backend_type,
            "storage_size": self.backend.size(),
            "max_size": getattr(self.backend, "max_size", None),
            "ttl_seconds": self.config.ttl_seconds,
        }
        base_stats.update(kv_stats)
        return base_stats


# 工厂函数，用于在DAG中创建KV服务
def create_kv_service_factory(
    service_name: str = "kv_service",
    backend_type: str = "memory",
    redis_url: Optional[str] = None,
    max_size: int = 10000,
    ttl_seconds: Optional[int] = None,
):
    """
    创建KV服务工厂

    Args:
        service_name: 服务名称
        backend_type: 后端类型 ("memory" 或 "redis")
        redis_url: Redis连接URL (当backend_type="redis"时需要)
        max_size: 最大存储条目数 (仅内存后端)
        ttl_seconds: 数据过期时间(秒)

    Returns:
        ServiceFactory: 可以用于注册到环境的服务工厂
    """
    from sage.core.factory.service_factory import ServiceFactory

    config = KVConfig(
        backend_type=backend_type,
        redis_url=redis_url,
        max_size=max_size,
        ttl_seconds=ttl_seconds,
    )

    factory = ServiceFactory(service_name, KVService)
    factory.config = config
    return factory
