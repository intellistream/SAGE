from src.core.memory.base_memory import BaseMemory


class LongTermMemory(BaseMemory):
    """
    Long-term memory for persistent knowledge storage and retrieval.
    """

    def __init__(self, vector_dim=128, search_algorithm="knnsearch"):
        super().__init__(vector_dim, search_algorithm, multimodal=True)
