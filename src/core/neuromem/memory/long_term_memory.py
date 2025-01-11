from src.core.neuromem.memory.base_memory import BaseMemory


class LongTermMemory(BaseMemory):
    """
    A simple in-memory key-value store.
    Used for short-term memory in the system.
    """

    def __init__(self):
        super().__init__()
        self.storage = {} # {userid|session_id -> {q->a, q->a, ...}}

    def store(self, item, key=None):
        """
        Store an item in memory with an optional key.
        """
        key = key or len(self.storage)  # Auto-generate key if not provided
        self.storage[key] = item
        self.logger.info(f"Stored item with key: {key}")

    def retrieve(self, key=None, k=1, **kwargs):
        """
        Retrieve an item by key or return the first `k` items.
        """
        if key is not None:
            return self.storage.get(key)
        return list(self.storage.values())[:k]

    def delete(self, key):
        """
        Delete an item by key.
        """
        if key in self.storage:
            del self.storage[key]
            self.logger.info(f"Deleted item with key: {key}")
        else:
            self.logger.warning(f"Key '{key}' not found.")

    def clean(self):
        """
        Clear all items in memory.
        """
        self.storage.clear()
        self.logger.info("Memory cleared.")
