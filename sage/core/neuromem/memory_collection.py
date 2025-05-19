# File sage/core/neuromem/memory_collection.py

from sage.core.neuromem.memory_backend import MemoryBackend
from typing import Dict, Optional, List, Any, Callable
import hashlib

class MemoryCollection:
    """
    A unified memory collection wrapper with simplified metadata support.
    """
    def __init__(
        self, 
        name, 
        embedding_model, 
        backend: str | None = None, 
        enable_metadata: bool = False
    ):
        
        self.name = name
        self.memory, self.backend_type = MemoryBackend.create_table(name, backend)
        self.embedding_model = embedding_model
        self.enable_metadata = enable_metadata
        self.metadata_fields = set()  # Track registered fields
        self._metadata_store = {}     # {item_id: {field: value}} 

    def add_field(self, field_name: str):
        """Register a metadata field"""
        if not self.enable_metadata:
            raise ValueError("Metadata is not enabled for this collection")
        self.metadata_fields.add(field_name)

    def retrieve(
        self,
        raw_data: str | None = None,
        metadata_filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
        **metadata_kwargs
    ):
        """
        Retrieve data with optional metadata filtering. 
        Supports:
            - metadata_filter_func (callable): for custom filter logic
            - metadata_kwargs: additional metadata conditions
        """
        if self.backend_type == "kv_backend":
            results = self.memory.retrieve()
        else:
            embedding = self.embedding_model.encode(raw_data)
            results = self.memory.retrieve(embedding)

        if (metadata_filter_func or metadata_kwargs) and not self.enable_metadata:
            raise ValueError("Metadata filtering is not enabled")

        # Merge metadata_kwargs into the filtering function logic
        if metadata_filter_func is None:
            metadata_filter_func = lambda meta: all(meta.get(k) == v for k, v in metadata_kwargs.items())

        if metadata_filter_func:
            filtered_results = []
            for item in results:
                text = item if isinstance(item, str) else getattr(item, 'text', None)
                if not text:
                    continue
                stable_id = self._get_stable_id(text)
                item_metadata = self._metadata_store.get(stable_id, {})

                if not metadata_filter_func(item_metadata):
                    continue
                filtered_results.append(item)
            results = filtered_results

        return results

    def store(
        self, 
        raw_data, 
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Store data and support custom storage function 'write _func'
        """
        stable_id = self._get_stable_id(raw_data)
        if self.backend_type == "kv_backend":
            return self.memory.store(raw_data)
        else:
            embedding = self.embedding_model.encode(raw_data)
            self.memory.store(raw_data, embedding)

        # Store metadata locally if provided
        if metadata:
            if not self.enable_metadata:
                raise ValueError("Metadata storage is not enabled")
            self._validate_metadata_fields(metadata.keys())
            self._metadata_store[stable_id] = metadata.copy()
            
        return stable_id

    def _validate_metadata_fields(self, fields):
        """Check if fields are registered"""
        unregistered = set(fields) - self.metadata_fields
        if unregistered:
            raise ValueError(f"Unregistered metadata fields: {unregistered}")
        
        
    def _get_stable_id(self, raw_text: str) -> str:
        return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    
    def clean(self):
        """Clear both data and metadata"""
        self.metadata_fields.clear()
        self._metadata_store.clear()
        return self.memory.clean()

# ---------- 测试 ----------
if __name__=="__main__":
    # python -m sage.core.neuromem.memory_collection
    from sage.core.neuromem.mem_test.mem_test import default_model
    collection = MemoryCollection("long_term_memory", default_model, enable_metadata=True)
    collection.add_field("user_id")
    collection.add_field("category")
    collection.add_field("timestamp")

    # 存储数据
    collection.store(
        raw_data="hello world",
        metadata={"user_id": 123, "category": "greeting", "timestamp": "2023-10-01"}
    )
    collection.store(
        raw_data="hello world nihao",
        metadata={"user_id": 456, "category": "info", "timestamp": "2025-10-01"}
    )
    collection.store(
        raw_data="hello world qiezi1",
        metadata={"user_id": 123, "category": "greeting", "timestamp": "2025-11-01"}
    )
    collection.store(
        raw_data="good night moon",
        metadata={"user_id": 789, "category": "farewell", "timestamp": "2024-01-01"}
    )

    # --- 测试 1 ---
    print("\n All Metadata:")
    print(collection._metadata_store)

    # --- 测试 2 ---
    print("\n Retrieve: default (raw only)")
    expected = ['hello world', 'hello world nihao', 'hello world qiezi1', 'good night moon']  # 期望返回的结果
    result = collection.retrieve("hello world nihao")
    print("Expected:", expected)
    print("Actual:", result)

    # --- 测试 3 ---
    print("\n Retrieve: dict filter + multiple keys")
    expected = ['hello world', 'hello world qiezi1']  # 期望返回的结果
    result = collection.retrieve(raw_data="hello world", user_id=123, category="greeting")
    print("Expected:", expected)
    print("Actual:", result)

    # --- 测试 4 ---
    print("\n Retrieve: custom function filter")
    def custom_filter(meta):
        return meta.get("user_id") == 123 and meta.get("timestamp", "") >= "2024-01-01"
    expected = ['hello world qiezi1']  # 期望返回的结果
    result = collection.retrieve(raw_data="hello world", metadata_filter_func=custom_filter)
    print("Expected:", expected)
    print("Actual:", result)

    # --- 测试 5 ---
    print("\n Retrieve: combined (func + keyword args)")
    def custom_and(meta):
        return int(meta.get("user_id", 0)) < 200
    expected = ['hello world', 'hello world qiezi1']  # 期望返回的结果
    result = collection.retrieve(raw_data="hello world", category="greeting", metadata_filter_func=custom_and)
    print("Expected:", expected)
    print("Actual:", result)
