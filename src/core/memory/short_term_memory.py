from src.core.memory.base_memory import BaseMemory


class ShortTermMemory(BaseMemory):
    """
    Short-term memory for storing session-specific key-value pairs generated during interactions.
    """

    def __init__(self, vector_dim=128, search_algorithm="knnsearch"):
        super().__init__(vector_dim, search_algorithm, multimodal=False)
