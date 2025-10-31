# file: sage/core/sage.middleware.services.neuromem./storage_engine/kv_backend/dict_kv_backend.py

import json
import os
from typing import Any

from .base_kv_backend import BaseKVBackend


class DictKVBackend(BaseKVBackend):
    """
    In-memory KV backend using a Python dictionary.
    """

    def __init__(self):
        self._store: dict[str, Any] = {}

    def has(self, key: str) -> bool:
        return key in self._store

    def get(self, key: str) -> Any:
        return self._store.get(key)

    def set(self, key: str, value: Any):
        self._store[key] = value

    def delete(self, key: str):
        self._store.pop(key, None)

    def clear(self):
        self._store.clear()

    def get_all_keys(self):
        """
        Get all keys in the store.
        获取所有存储的key。
        """
        return list(self._store.keys())

    def store_data_to_disk(self, path: str):
        """将当前内存数据存储为 JSON 文件"""
        with open(path, "w", encoding="utf-8") as f:
            # 用 ensure_ascii=False 保证 utf-8 兼容中文，indent=2 可读性高
            json.dump(self._store, f, ensure_ascii=False, indent=2)

    def load_data_to_memory(self, path: str):
        """从指定 JSON 文件加载数据到内存（覆盖当前 _store）"""
        if not os.path.exists(path):
            raise FileNotFoundError(f"File '{path}' does not exist.")
        with open(path, encoding="utf-8") as f:
            self._store = json.load(f)

    def clear_disk_data(self, path: str):
        """删除指定 JSON 文件"""
        if os.path.exists(path):
            os.remove(path)
