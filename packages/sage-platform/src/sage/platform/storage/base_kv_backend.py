"""Base Key-Value Backend Abstract Class

Layer: L2 (Platform Services - Storage)

Abstract base class for key-value storage backends.
Defines the interface that all KV storage implementations must follow.

Architecture:
- Pure L2 abstraction, no dependencies on upper layers
- Provides backend-agnostic storage interface
"""

# file: sage/core/sage.middleware.services.neuromem./storage_engine/kv_backend/base_kv_backend.py

from abc import ABC, abstractmethod
from typing import Any


class BaseKVBackend(ABC):
    """Abstract base class for key-value backends.

    抽象基类，用于定义 KV 存储后端接口规范。
    """

    @abstractmethod
    def get_all_keys(self) -> list[str]:
        pass

    @abstractmethod
    def has(self, key: str) -> bool:
        """
        Check whether the key exists.
        检查指定键是否存在。
        """
        pass

    @abstractmethod
    def get(self, key: str) -> Any:
        """
        Retrieve value by key.
        根据键获取对应的值。
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any):
        """
        Set a key-value pair.
        存储键值对。
        """
        pass

    @abstractmethod
    def delete(self, key: str):
        """
        Delete a key-value pair.
        删除指定键及其对应的值。
        """
        pass

    @abstractmethod
    def clear(self):
        """
        Clear the entire store.
        清空所有键值对。
        """
        pass

    @abstractmethod
    def load_data_to_memory(self, path: str):
        pass

    @abstractmethod
    def store_data_to_disk(self, path: str):
        pass

    @abstractmethod
    def clear_disk_data(self, path: str):
        pass
