import logging

from sage.core.neuromem.manager.memory_manager import NeuronMemManager
from sage.core.neuromem.memory.dynamic_contextual_memory import DynamicContextualMemory
from sage.core.neuromem.memory.long_term_memory import LongTermMemory
from sage.core.neuromem.memory.short_term_memory import ShortTermMemory
from sage.utils.file_path import TEST_FILE
from sage.utils.text_processing import process_text_to_embedding


def preload_short_term_memory(memory, file_path):
    """
    Preload data into the dynamic-external memory.
    :param memory: The memory layer to store embeddings.
    :param file_path: Path to the file containing text data to be preloaded.
    """
    logging.info(f"Preloading data into short-term memory from {file_path}...")

    raise NotImplementedError("Preloading to STM not implemented yet.")


def preload_long_term_memory(memory, file_path):
    """
    Preload data into the dynamic-external memory.
    :param memory: The memory layer to store embeddings.
    :param file_path: Path to the file containing text data to be preloaded.
    """
    logging.info(f"Preloading data into long-term memory from {file_path}...")

    raise NotImplementedError("Preloading to LTM not implemented yet.")


def preload_dynamic_contextual_memory(memory, file_path):
    """
    Preload data into the dynamic-external memory.
    :param memory: The memory layer to store embeddings.
    :param file_path: Path to the file containing text data to be preloaded.
    """
    logging.info(f"Preloading data into dynamic-external memory from {file_path}...")

    try:
        with open(file_path, "r") as file:
            for line in file:
                line = line.strip()
                if line:  # Ensure the line is not empty
                    # Process the text into an embedding_model
                    embedding = process_text_to_embedding(line)

                    # Store embedding_model in memory
                    memory.store(embedding, line)
                    logging.info(f"Preloaded text: {line}")

        logging.info("Preloading completed successfully.")
    except Exception as e:
        logging.error(f"Error during preloading: {str(e)}")
        raise RuntimeError(f"Failed to preload long-term memory: {str(e)}")


def initialize_memory_manager():
    """
    Initialize short-term and long-term memory layers.
    Initilaize NeuronMem Manager for STM LTM and DCM management.
    """
    logging.info("Initializing memory layers...")

    # Short-term memory
    short_term_memory = ShortTermMemory()

    # Long-term memory
    long_term_memory = LongTermMemory(
        vector_dim=128,  # Vector dimensions
        search_algorithm="knnsearch"  # Search algorithm
    )

    # Dynamic-contextual memory
    dynamic_contextual_memory = DynamicContextualMemory(
        vector_dim=128,  # Vector dimensions
        search_algorithm="knnsearch"  # Search algorithm
    )

    # Preload data into long-term memory
    preload_dynamic_contextual_memory(dynamic_contextual_memory, TEST_FILE)

    # Return memory layers
    memory_layers = {
        "short_term": short_term_memory,
        "long_term": long_term_memory,
        "dynamic_contextual": dynamic_contextual_memory
    }

    logging.info("Memory layers initialized successfully.")


    # Initialize Memory Manager
    memory_manager = NeuronMemManager(memory_layers)

    return memory_manager
