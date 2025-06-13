# file: sage/core/neuromem/storage_engine/kv_backend/dict_kv_backend.py

from typing import Any, Dict
from .base_kv_backend import BaseKVBackend

class DictKVBackend(BaseKVBackend):
    """
    In-memory KV backend using a Python dictionary.
    """

    def __init__(self):
        self._store: Dict[str, Any] = {}

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
