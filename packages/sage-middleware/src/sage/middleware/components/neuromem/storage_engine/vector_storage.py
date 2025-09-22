# file sage/core/sage.middleware.services.neuromem./storage_engine/vector_storage.py
# python -m sage.core.sage.middleware.services.neuromem..storage_engine.vector_storage

import json
from typing import Any, List, Optional

import numpy as np
from sage.middleware.components.neuromem.storage_engine.kv_backend.base_kv_backend import \
    BaseKVBackend
from sage.middleware.components.neuromem.storage_engine.kv_backend.dict_kv_backend import \
    DictKVBackend


class VectorStorage:
    """
    Simple vector storage based on hash IDs.
    基于哈希ID的简单向量存储器。
    """

    def __init__(self, backend: Optional[BaseKVBackend] = None):
        self.backend = backend or DictKVBackend()

    def get_all_ids(self) -> List[str]:
        return self.backend.get_all_keys()

    def has(self, item_id: str) -> bool:
        return self.backend.has(item_id)

    def delete(self, item_id: str):
        self.backend.delete(item_id)

    def store(self, hash_id: str, vector: Any):
        self.backend.set(hash_id, vector)

    def get(self, hash_id: str) -> Any:
        return self.backend.get(hash_id)

    def clear(self):
        self.backend.clear()

    def store_to_disk(self, path: str):
        # type: ignore for IDE/static checker
        save_dict = {k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in self.backend._store.items()}  # type: ignore
        with open(path, "w", encoding="utf-8") as f:
            json.dump(save_dict, f, ensure_ascii=False, indent=2)

    def load_from_disk(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # type: ignore for IDE/static checker
        for k, v in data.items():
            self.backend._store[k] = np.array(v, dtype="float32")  # type: ignore

    def clear_disk_data(self, path: str):
        if not hasattr(self.backend, "clear_disk_data"):
            raise NotImplementedError("Backend does not support clear_disk_data")
        self.backend.clear_disk_data(path)


if __name__ == "__main__":
    import hashlib

    vs = VectorStorage()
    vector = [1, 2, 3]
    vector_id = hashlib.sha256(str(vector).encode()).hexdigest()
    disk_path = "test_vector_storage.json"

    # 存储并保存到磁盘
    vs.store(vector_id, vector)
    print("Step 1 | Retrieved:", vs.get(vector_id))
    vs.store_to_disk(disk_path)
    print(f"Step 2 | Data has been saved to {disk_path}")

    # 清空内存
    vs.clear()
    print("Step 3 | After clear (should be None):", vs.get(vector_id))

    # 等待用户输入 yes 再读取
    user_input = input("Step 4 | Enter 'yes' to load data from disk: ")
    if user_input.strip().lower() == "yes":
        vs.load_from_disk(disk_path)
        print("Step 5 | After reload, Retrieved:", vs.get(vector_id))
    else:
        print("Step 5 | Skipped loading from disk.")

    # 删除磁盘文件
    vs.clear_disk_data(disk_path)
    print(f"Step 6 | Disk file {disk_path} has been deleted.")
