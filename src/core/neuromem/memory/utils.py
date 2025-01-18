import logging
import json
from src.core.neuromem.memory.external_memory import ExternalMemory
from src.core.neuromem.memory.internal_memory import KVCacheMemory
from src.utils.file_path import TEST_FILE
from src.utils.text_processing import process_text_to_embedding
from bs4 import BeautifulSoup
from langchain.text_splitter import TokenTextSplitter


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

def preload_web_long_term_memory(memory, search_results):
    """
    Preload web search result into the long-term memory.
    :param memory: The memory layer to store embeddings.
    :param file_path: Path to the file containing text data to be preloaded.
    """

    try:
        # Initialize the TokenTextSplitter
        splitter = TokenTextSplitter(chunk_size=500)
        split_chunks = []
        # extract chunks from search results (5个网页)
        for search_result in search_results:
            page_snippet = search_result['page_snippet']
            html_source = search_result['page_result']
            soup = BeautifulSoup(html_source, "lxml")
            text = soup.get_text(" ", strip=True)  # Use space as a separator, strip whitespaces

            chunks = []            
            # Use LangChain to split text into chunks of 500 tokens
            split_text = splitter.split_text(text)
            split_snippet = splitter.split_text(page_snippet)
            split_chunks.extend(split_text + split_snippet)

        # Filter out empty chunks
        chunks.extend([chunk for chunk in split_chunks if chunk.strip()])

        for chunk in chunks:
            embedding = process_text_to_embedding(chunk)
            memory.store(embedding, chunk)
        
        logging.info(f"Preloading completed successfully. All chunks are {len(chunks)}")
        
    except Exception as e:
        logging.error(f"Error during preloading: {str(e)}")
        raise RuntimeError(f"Failed to preload long-term memory: {str(e)}")

def initialize_memory_layers(query, query_time, search_results):
    """
    Initialize short-term and long-term memory layers.
    """
    logging.info("Initializing memory layers...")

    # Short-term memory
    short_term_memory = KVCacheMemory()

    # Long-term memory
    long_term_memory = ExternalMemory(
        vector_dim=128,  # Vector dimensions
        search_algorithm="knnsearch"  # Search algorithm
    )

    # Store query and query time in short-term memory
    short_term_memory.store(query, "query")
    short_term_memory.store(query_time, "query_time")

    preload_web_long_term_memory(long_term_memory, search_results)

    # Return memory layers
    memory_layers = {
        "short_term": short_term_memory,
        "long_term": long_term_memory
    }

    logging.info("Memory layers initialized successfully.")
    return memory_layers
