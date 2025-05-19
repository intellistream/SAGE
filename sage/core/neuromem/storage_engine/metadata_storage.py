# file sage/core/neuromem/storage_engine/metadata_storage.py

from typing import Dict, Any

class MetadataStorage:
    """
    A lightweight metadata manager that handles field registration,
    validation, and per-item metadata storage.

    简单的元数据管理器，用于处理字段注册、字段校验和每条数据的元数据存储。
    """

    def __init__(self):
        # Registered metadata fields 已注册的元数据字段名集合
        self.fields = set()

        # Internal storage of metadata for each item
        # 每条数据的元数据映射：{item_id: {field: value}}
        self._store: Dict[str, Dict[str, Any]] = {}

    def add_field(self, field_name: str):
        """
        Register a new metadata field name.
        注册一个新的元数据字段名。
        """
        self.fields.add(field_name)

    def validate_fields(self, metadata: Dict[str, Any]):
        """
        Ensure all metadata keys are registered.
        校验提供的元数据字段是否已注册。
        """
        unregistered = set(metadata.keys()) - self.fields
        if unregistered:
            raise ValueError(f"Unregistered metadata fields: {unregistered}")

    def store(self, item_id: str, metadata: Dict[str, Any]):
        """
        Store metadata for a specific item.
        为指定的数据项存储元数据（会校验字段是否合法）。
        """
        self.validate_fields(metadata)
        self._store[item_id] = metadata.copy()

    def get(self, item_id: str) -> Dict[str, Any]:
        """
        Retrieve metadata for a specific item.
        获取指定数据项的元数据（如果不存在则返回空字典）。
        """
        return self._store.get(item_id, {})

    def clear(self):
        """
        Clear all stored metadata and registered fields.
        清除所有已注册的字段和已存储的元数据。
        """
        self.fields.clear()
        self._store.clear()

"""测试预期输出
Retrieved metadata: {'author': 'Alice', 'topic': 'AI'}
Expected error: Unregistered metadata fields: {'unknown_field'}
After clear, retrieved: {}
"""

if __name__ == "__main__":
    # 创建一个元数据存储实例
    metadata_store = MetadataStorage()

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

    # 读取元数据
    retrieved = metadata_store.get(item_id)
    print("Retrieved metadata:", retrieved)

    # 尝试存储未注册字段，应该抛出异常
    try:
        metadata_store.store("item2", {"unknown_field": "value"})
    except ValueError as e:
        print("Expected error:", e)

    # 清空元数据
    metadata_store.clear()
    print("After clear, retrieved:", metadata_store.get(item_id))
