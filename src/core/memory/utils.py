import logging

from src.core.memory.long_term_memory import LongTermMemory
from src.core.memory.short_term_memory import ShortTermMemory
from src.utils.file_path import TEST_FILE
from src.utils.text_processing import process_text_to_embedding


def preload_long_term_memory(memory, file_path):
    """
    Preload data into the long-term memory.
    :param memory: The memory layer to store embeddings.
    :param file_path: Path to the file containing text data to be preloaded.
    """
    logging.info(f"Preloading data into long-term memory from {file_path}...")

    try:
        with open(file_path, "r") as file:
            for line in file:
                line = line.strip()
                if line:  # Ensure the line is not empty
                    # Process the text into an embedding
                    embedding = process_text_to_embedding(line)

                    # Store embedding in memory
                    memory.store(embedding, line)
                    logging.info(f"Preloaded text: {line}")

        logging.info("Preloading completed successfully.")
    except Exception as e:
        logging.error(f"Error during preloading: {str(e)}")
        raise RuntimeError(f"Failed to preload long-term memory: {str(e)}")


def initialize_memory_layers():
    """
    Initialize short-term and long-term memory layers.
    """
    logging.info("Initializing memory layers...")

    # Short-term memory
    short_term_memory = ShortTermMemory()

    # Long-term memory
    long_term_memory = LongTermMemory(
        vector_dim=128,  # Vector dimensions
        search_algorithm="knnsearch"  # Search algorithm
    )

    # Preload data into long-term memory
    preload_long_term_memory(long_term_memory, TEST_FILE)

    # Return memory layers
    memory_layers = {
        "short_term": short_term_memory,
        "long_term": long_term_memory
    }

    logging.info("Memory layers initialized successfully.")
    return memory_layers
