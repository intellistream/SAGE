import logging
from src.core.memory.short_term_memory import ShortTermMemory
from src.core.memory.long_term_memory import LongTermMemory

def initialize_memory_layers():
    """
    Initialize memory layers for the system.
    :return: A dictionary containing initialized short-term and long-term memory layers.
    """
    logging.info("Initializing memory layers...")

    # Initialize short-term memory
    short_term_memory = ShortTermMemory(
        vector_dim=128,  # Use the fixed vector dimension expected by the system
        search_algorithm="knnsearch"  # Example search algorithm
    )

    # Initialize long-term memory
    long_term_memory = LongTermMemory(
        vector_dim=128,  # Use the fixed vector dimension expected by the system
        search_algorithm="knnsearch"  # Example search algorithm
    )

    # Return the memory layers as a dictionary
    memory_layers = {
        "short_term": short_term_memory,
        "long_term": long_term_memory
    }

    logging.info("Memory layers initialized successfully.")
    return memory_layers
