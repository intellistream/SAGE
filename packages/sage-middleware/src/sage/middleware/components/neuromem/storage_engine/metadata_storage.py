# file sage/core/sage.middleware.services.neuromem./storage_engine/metadata_storage.py
# python -m sage.core.sage.middleware.services.neuromem..storage_engine.metadata_storage

from typing import Any, Dict, List, Optional

from sage.middleware.components.neuromem.storage_engine.kv_backend.base_kv_backend import \
    BaseKVBackend
from sage.middleware.components.neuromem.storage_engine.kv_backend.dict_kv_backend import \
    DictKVBackend


class MetadataStorage:
    """
    A lightweight metadata manager that handles field registration,
    validation, and per-item metadata storage.
    简单的元数据管理器，用于处理字段注册、字段校验和每条数据的元数据存储。

    Attributes:
        fields (set): Set of registered metadata field names
        backend (BaseKVBackend): Backend storage implementation
    """

    def __init__(self, backend: Optional[BaseKVBackend] = None):
        # Registered metadata fields 已注册的元数据字段名集合
        self.fields = set()
        # 底层存储后端，默认是内存字典
        self.backend = backend or DictKVBackend()

    def add_field(self, field_name: str) -> None:
        """
        Register a new metadata field. If the field is already registered,
        this operation is ignored.
        注册新的元数据字段。如果字段已存在，则忽略此操作。

        Args:
            field_name: Name of the field to register

        Raises:
            ValueError: If field_name is None or empty
        """
        if not field_name or not isinstance(field_name, str):
            raise ValueError("Field name must be a non-empty string")
        self.fields.add(field_name)

    def has_field(self, field_name: str) -> bool:
        """
        Check if a field is registered.
        检查字段是否已注册。

        Args:
            field_name: Name of the field to check

        Returns:
            bool: True if the field is registered, False otherwise
        """
        return field_name in self.fields

    def validate_fields(self, metadata: Dict[str, Any]) -> None:
        """
        Validate that all fields in the metadata are registered.
        验证所有元数据字段是否已注册。

        Args:
            metadata: Metadata dictionary to validate

        Raises:
            ValueError: If any field is not registered or if metadata is invalid
        """
        if not isinstance(metadata, dict):
            raise ValueError("Metadata must be a dictionary")

        unregistered = set(metadata.keys()) - self.fields
        if unregistered:
            raise ValueError(f"Unregistered metadata fields: {unregistered}")

    def store(self, item_id: str, metadata: Dict[str, Any]) -> None:
        """
        Store metadata for an item.
        存储条目的元数据。

        Args:
            item_id: ID of the item
            metadata: Metadata dictionary to store

        Raises:
            ValueError: If item_id is invalid or metadata validation fails
        """
        if not item_id or not isinstance(item_id, str):
            raise ValueError("Item ID must be a non-empty string")
        if metadata is None:
            metadata = {}
        elif not isinstance(metadata, dict):
            raise ValueError("Metadata must be a dictionary")

        self.validate_fields(metadata)
        self.backend.set(item_id, metadata.copy())

    def get_all_ids(self) -> List[str]:
        """
        Get all stored item IDs.
        获取所有已存储的条目ID。

        Returns:
            List of item IDs
        """
        return self.backend.get_all_keys()

    def get(self, item_id: str) -> Dict[str, Any]:
        """
        Get metadata for an item.
        获取条目的元数据。

        Args:
            item_id: ID of the item

        Returns:
            Metadata dictionary, empty dict if item doesn't exist

        Raises:
            ValueError: If item_id is invalid
        """
        if not item_id or not isinstance(item_id, str):
            raise ValueError("Item ID must be a non-empty string")
        return self.backend.get(item_id) or {}

    def has(self, item_id: str) -> bool:
        """
        Check if an item has metadata stored.
        检查条目是否有存储的元数据。

        Args:
            item_id: ID of the item to check

        Returns:
            bool: True if item has metadata, False otherwise

        Raises:
            ValueError: If item_id is invalid
        """
        if not item_id or not isinstance(item_id, str):
            raise ValueError("Item ID must be a non-empty string")
        return self.backend.has(item_id)

    def delete(self, item_id: str) -> None:
        """
        Delete metadata for an item.
        删除条目的元数据。

        Args:
            item_id: ID of the item to delete

        Raises:
            ValueError: If item_id is invalid
        """
        if not item_id or not isinstance(item_id, str):
            raise ValueError("Item ID must be a non-empty string")
        self.backend.delete(item_id)

    def clear(self) -> None:
        """Clear all metadata and registered fields."""
        self.fields.clear()
        self.backend.clear()

    def store_to_disk(self, path: str) -> None:
        """
        Store all data to disk as JSON file.
        将所有数据存储到磁盘JSON文件。

        Args:
            path: Path to the JSON file

        Raises:
            NotImplementedError: If backend doesn't support disk operations
            ValueError: If path is invalid
        """
        if not path or not isinstance(path, str):
            raise ValueError("Path must be a non-empty string")
        if not hasattr(self.backend, "store_data_to_disk"):
            raise NotImplementedError("Backend does not support store_data_to_disk")
        self.backend.store_data_to_disk(path)

    def load_from_disk(self, path: str) -> None:
        """
        Load all data from disk JSON file (overwrites memory).
        从磁盘JSON文件加载所有数据（覆盖内存）。

        Args:
            path: Path to the JSON file

        Raises:
            NotImplementedError: If backend doesn't support disk operations
            ValueError: If path is invalid
            FileNotFoundError: If file doesn't exist
        """
        if not path or not isinstance(path, str):
            raise ValueError("Path must be a non-empty string")
        if not hasattr(self.backend, "load_data_to_memory"):
            raise NotImplementedError("Backend does not support load_data_to_memory")
        self.backend.load_data_to_memory(path)

    def clear_disk_data(self, path: str) -> None:
        """
        Delete the disk JSON file.
        删除磁盘JSON文件。

        Args:
            path: Path to the JSON file

        Raises:
            NotImplementedError: If backend doesn't support disk operations
            ValueError: If path is invalid
        """
        if not path or not isinstance(path, str):
            raise ValueError("Path must be a non-empty string")
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
    metadata = {"author": "Alice", "topic": "AI"}

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
    if user_input.strip().lower() == "yes":
        metadata_store.load_from_disk(disk_path)
        print("Step 5 | After reload, retrieved:", metadata_store.get(item_id))
    else:
        print("Step 5 | Skipped loading from disk.")

    # 删除磁盘文件
    metadata_store.clear_disk_data(disk_path)
    print(f"Step 6 | Disk file {disk_path} has been deleted.")

    # 可选：检查磁盘上确实没这个文件
    print("Step 7 | File exists after deletion?:", os.path.exists(disk_path))
