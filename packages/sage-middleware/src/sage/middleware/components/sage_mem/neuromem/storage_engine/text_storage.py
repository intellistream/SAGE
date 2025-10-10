# file sage/core/sage.middleware.services.neuromem./storage_engine/text_storage.py
# python -m sage.core.sage.middleware.services.neuromem..storage_engine.text_storage

from typing import List, Optional

from .kv_backend.base_kv_backend import (
    BaseKVBackend,
)
from .kv_backend.dict_kv_backend import (
    DictKVBackend,
)


class TextStorage:
    """
    Simple raw text storage based on externally provided IDs.

    简单的原始文本存储器，由外部提供稳定 ID（不生成哈希）。
    """

    def __init__(self, backend: Optional[BaseKVBackend] = None):
        # 支持自定义后端，默认用内存字典
        self.backend = backend or DictKVBackend()

    def get_all_ids(self) -> List[str]:
        return self.backend.get_all_keys()

    def has(self, item_id: str) -> bool:
        return self.backend.has(item_id)

    def delete(self, item_id: str):
        self.backend.delete(item_id)

    def store(self, item_id: str, text: str):
        """
        Store text under a given item_id.

        使用外部提供的 ID 存储原始文本。
        """
        self.backend.set(item_id, text)

    def get(self, item_id: str) -> str:
        """
        Retrieve text using item_id.

        使用 ID 获取文本内容。
        """
        return self.backend.get(item_id) or ""

    def clear(self):
        """
        Clear all stored text.

        清空所有存储内容。
        """
        self.backend.clear()

    def store_to_disk(self, path: str):
        """存储所有数据到磁盘 json 文件"""
        # 要求 backend 有该方法
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


"""测试预期输出
Retrieved: hello world
After clear:
"""

if __name__ == "__main__":
    import hashlib

    ts = TextStorage()
    text = "hello world"
    text_id = hashlib.sha256(text.encode()).hexdigest()
    disk_path = "test_text_storage.json"

    # 1. 存储并保存到磁盘
    ts.store(text_id, text)
    print("Step 1 | Retrieved:", ts.get(text_id))
    ts.store_to_disk(disk_path)
    print(f"Data has been saved to {disk_path}")

    # 2. 清空内存
    ts.clear()
    print("Step 2 | After clear (should be empty):", ts.get(text_id))

    # 3. 等待用户输入 yes 再读取
    user_input = input("Step 3 | Enter 'yes' to load data from disk: ")
    if user_input.strip().lower() == "yes":
        ts.load_from_disk(disk_path)
        print("Step 3 | After reload, Retrieved:", ts.get(text_id))
    else:
        print("Step 3 | Skipped loading from disk.")

    # 4. 删除磁盘数据
    ts.clear_disk_data(disk_path)
    print(f"Step 4 | Disk file {disk_path} has been deleted.")
