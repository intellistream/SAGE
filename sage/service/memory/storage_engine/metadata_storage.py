# file sage/core/sage_memory/storage_engine/metadata_storage.py
# python -m sage.core.sage_memory.storage_engine.metadata_storage

from typing import Dict, Any, Optional, List

from sage.service.memory.storage_engine.kv_backend.base_kv_backend import BaseKVBackend
from sage.service.memory.storage_engine.kv_backend.dict_kv_backend import DictKVBackend


class MetadataStorage:
    """
    A lightweight metadata manager that handles field registration,
    validation, and per-item metadata storage.
    简单的元数据管理器，用于处理字段注册、字段校验和每条数据的元数据存储。
    """

    def __init__(self, backend: Optional[BaseKVBackend] = None):
        # Registered metadata fields 已注册的元数据字段名集合
        self.fields = set()
        # 底层存储后端，默认是内存字典
        self.backend = backend or DictKVBackend()

    def add_field(self, field_name: str):
        self.fields.add(field_name)

    def validate_fields(self, metadata: Dict[str, Any]):
        unregistered = set(metadata.keys()) - self.fields
        if unregistered:
            raise ValueError(f"Unregistered metadata fields: {unregistered}")

    def store(self, item_id: str, metadata: Dict[str, Any]):
        self.validate_fields(metadata)
        self.backend.set(item_id, metadata.copy())
        
    def get_all_ids(self) -> List[str]:
        return self.backend.get_all_keys()

    def get(self, item_id: str) -> Dict[str, Any]:
        return self.backend.get(item_id) or {}

    def has(self, item_id: str) -> bool:
        return self.backend.has(item_id)

    def delete(self, item_id: str):
        self.backend.delete(item_id)

    def clear(self):
        self.fields.clear()
        self.backend.clear()
        
    def store_to_disk(self, path: str):
        """存储所有数据到磁盘 json 文件"""
        if not hasattr(self.backend, "store_data_to_disk"):
            raise NotImplementedError("Backend does not support store_data_to_disk")
        self.backend.store_data_to_disk(path)

    def load_from_disk(self, path: str):
        """从磁盘 json 文件加载所有数据（覆盖内存）"""
        if not hasattr(self.backend, "load_data_to_memory"):
            raise NotImplementedError("Backend does not support load_data_to_memory")
        self.backend.load_data_to_memory(path)

    def clear_disk_data(self, path: str):
        """删除磁盘上的 json 文件"""
        if not hasattr(self.backend, "clear_disk_data"):
            raise NotImplementedError("Backend does not support clear_disk_data")
        self.backend.clear_disk_data(path)

if __name__ == "__main__":
    import os

    metadata_store = MetadataStorage()
    disk_path = "test_metadata_storage.json"

    # 注册元数据字段
    metadata_store.add_field("author")
    metadata_store.add_field("topic")

    # 构造示例数据
    item_id = "abc123"
    metadata = {
        "author": "Alice",
        "topic": "AI"
    }

    # 存储元数据
    metadata_store.store(item_id, metadata)
    print("Step 1 | Retrieved metadata:", metadata_store.get(item_id))

    # 保存到磁盘
    metadata_store.store_to_disk(disk_path)
    print(f"Step 2 | Metadata saved to {disk_path}")

    # 清空内存
    metadata_store.clear()
    print("Step 3 | After clear, retrieved:", metadata_store.get(item_id))

    # 等待用户输入 yes 再加载
    user_input = input("Step 4 | Enter 'yes' to load metadata from disk: ")
    if user_input.strip().lower() == 'yes':
        metadata_store.load_from_disk(disk_path)
        print("Step 5 | After reload, retrieved:", metadata_store.get(item_id))
    else:
        print("Step 5 | Skipped loading from disk.")

    # 删除磁盘文件
    metadata_store.clear_disk_data(disk_path)
    print(f"Step 6 | Disk file {disk_path} has been deleted.")

    # 可选：检查磁盘上确实没这个文件
    print("Step 7 | File exists after deletion?:", os.path.exists(disk_path))

