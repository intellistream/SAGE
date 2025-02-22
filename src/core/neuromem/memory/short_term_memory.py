from src.core.neuromem.memory.base_memory import BaseMemory


class ShortTermMemory(BaseMemory):
    """
    A simple in-memory key-value store.
    Used for short-term memory in the system.
    """

    def __init__(self):
        super().__init__()
        self.storage = {} # {random_id: q->a, random_id: q->a, ...}

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
        :param key: Specific key to retrieve.
        :param k: Number of items to retrieve if no key is provided.
        :return: Retrieved data.
        """
        if key is not None:
            value = self.storage.get(key)
            return [value] if value is not None else []
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


if __name__ == '__main__':
    memory = ShortTermMemory()
    memory.store({"question": "What is AI?", "answer": "Artificial Intelligence"})
    memory.store({"question": "What is ML?", "answer": "Machine Learning"})
    print(memory.storage)  # {0: {...}, 1: {...}}