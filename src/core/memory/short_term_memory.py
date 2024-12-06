from src.core.memory.persistent_memory import PersistentMemory


class ShortTermMemory(PersistentMemory):
    """
    Short-term memory layer inheriting from PersistentMemory.
    """

    def __init__(self, vector_dim, search_algorithm):
        super().__init__(vector_dim, search_algorithm)
        self.logger.info("Short-term memory initialized.")