# file sage/core/neuromem/storage_engine/vector_storage.py
# python sage/core/neuromem/storage_engine/vector_storage.py

from typing import Any, Dict

class VectorStorage:
    """
    Simple vector storage based on hash IDs.

    基于哈希ID的简单向量存储器。
    """

    def __init__(self):
        # 存储结构：{hash_id: vector}
        # Storage structure: {hash_id: vector}
        self._store: Dict[str, Any] = {}

    def has(self, item_id: str) -> bool:
        return item_id in self._store
    
    def delete(self, item_id: str):
        self._store.pop(item_id, None)
        
    def store(self, hash_id: str, vector: Any):
        """
        Store vector under a given hash_id.

        使用给定的hash_id存储向量。
        """
        self._store[hash_id] = vector

    def get(self, hash_id: str) -> Any:
        """
        Retrieve vector using hash_id.

        使用hash_id获取向量。
        """
        return self._store.get(hash_id)

    def clear(self):
        """
        Clear all stored vectors.

        清空所有存储的向量。
        """
        self._store.clear()


"""测试预期输出
Retrieved: [1, 2, 3]
After clear: None
"""

if __name__ == "__main__":
    import hashlib
    vs = VectorStorage()
    vector = [1, 2, 3]
    vector_id = hashlib.sha256(str(vector).encode()).hexdigest()

    vs.store(vector_id, vector)
    print("Retrieved:", vs.get(vector_id))

    vs.clear()
    print("After clear:", vs.get(vector_id))  # 应为None