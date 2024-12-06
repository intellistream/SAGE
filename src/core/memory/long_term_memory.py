from src.core.memory.persistent_memory import PersistentMemory


class LongTermMemory(PersistentMemory):
    """
    Long-term memory layer inheriting from PersistentMemory.
    """

    def __init__(self, vector_dim, search_algorithm):
        super().__init__(vector_dim, search_algorithm)
        self.logger.info("Long-term memory initialized.")