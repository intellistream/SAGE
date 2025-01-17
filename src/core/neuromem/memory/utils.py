import logging

from src.core.neuromem.manager.memory_manager import NeuronMemManager
from src.core.neuromem.memory.dynamic_contextual_memory import DynamicContextualMemory
from src.core.neuromem.memory.long_term_memory import LongTermMemory
from src.core.neuromem.memory.short_term_memory import ShortTermMemory
from src.utils.file_path import TEST_FILE
from src.utils.file_path import CORPUS_FILE
from src.utils.text_processing import process_text_to_embedding
from src.utils.external_corpus import Corpus

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
        corpus = Corpus(file_path)
        # Currently only the first five corpora are input for testing
        # for i in range(corpus.get_len()):
        for i in range(5):
            text = corpus.get_item_text(i)
            embedding = process_text_to_embedding(text)
            corpus.set_db_id(i, memory.store(embedding, text))
            logging.info(f"Preloaded text: {text}")
        logging.info("Preloading completed successfully.")

        # # Former test_corpus
        # with open(file_path, "r") as file:
        #     for line in file:
        #         line = line.strip()
        #         if line:  # Ensure the line is not empty
        #             # Process the text into an embedding
        #             embedding = process_text_to_embedding(line)
        #
        #             # Store embedding in memory
        #             memory.store(embedding, line)
        #             logging.info(f"Preloaded text: {line}")
        #
        # logging.info("Preloading completed successfully.")

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
    preload_dynamic_contextual_memory(dynamic_contextual_memory, CORPUS_FILE)

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
