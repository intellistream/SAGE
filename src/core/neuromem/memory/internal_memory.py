from src.core.neuromem.memory.base_memory import BaseMemory


class KVCacheMemory(BaseMemory):
    """
    A simple in-memory key-value store.
    Used for short-term memory in the system.
    """

    def __init__(self):
        super().__init__()
        self._store = {}

    def store(self, item, key=None):
        """
        Store an item in memory with an optional key.
        """
        key = key or len(self.store)  # Auto-generate key if not provided
        self._store[key] = item
        self.logger.info(f"Stored item with key: {key}")

    def retrieve(self, key, k=1, **kwargs):
        """
        Retrieve an item by key or return the first `k` items.
        """
        if key is not None:
            return self._store.get(key)
        return list(self._store.values())[:k]

    def delete(self, key):
        """
        Delete an item by key.
        """
        if key in self.store:
            del self.store[key]
            self.logger.info(f"Deleted item with key: {key}")
        else:
            self.logger.warning(f"Key '{key}' not found.")

    def clean(self):
        """
        Clear all items in memory.
        """
        self._store.clear()
        self.logger.info("Memory cleared.")
