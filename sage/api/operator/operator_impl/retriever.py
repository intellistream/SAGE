from torch import chunk
from sage.api.operator import RetrieverFunction
from sage.api.memory import connect,get_default_manager
from typing import Tuple, List
from sage.api.operator import Data

class SimpleRetriever(RetrieverFunction):
    """
    A simple retriever that retrieves memory chunks (short-term, long-term, or dynamic-contextual) based on the input query.

    The retriever checks different memory modules (STM, LTM, DCM) and fetches relevant memory chunks from them.

    Input: A Data object containing a query string.
    Output: A Data object containing a tuple of (input_query, List of retrieved memory chunks).

    Attributes:
        config: Configuration dictionary containing retriever settings (top_k, memory modules).
        memory_manager: A memory manager instance used for accessing various memory modules.
        top_k: The number of top memory chunks to retrieve (defined in config).
        stm: Short-Term Memory module (if enabled).
        ltm: Long-Term Memory module (if enabled).
        dcm: Dynamic Contextual Memory module (if enabled).
    """

    def __init__(self, config):
        """
        Initializes the SimpleRetriever with configuration settings and memory modules.

        :param config: Dictionary containing retriever settings, including top_k and memory module options (STM, LTM, DCM).
        """
        super().__init__()  # Call the parent class's constructor
        self.config = config["retriever"]  # Retrieve retriever-specific configuration
        self.memory_manager = get_default_manager()  # Get the default memory manager
        self.top_k = self.config["top_k"]  # Set the top_k parameter from config

        # Conditionally initialize memory modules based on the configuration
        if self.config["stm"]:
            self.stm = connect(self.memory_manager, "short_term_memory")  # Connect to Short-Term Memory
        if self.config["ltm"]:
            self.ltm = connect(self.memory_manager, "long_term_memory")  # Connect to Long-Term Memory
        if self.config["dcm"]:
            self.dcm = connect(self.memory_manager, "dynamic_contextual_memory")  # Connect to Dynamic Contextual Memory

    def execute(self, data: Data[str]) -> Data[Tuple[str, List[str]]]:
        """
        :param data: A Data object containing a single string (the input query).
        :return: A Data object containing a tuple of (input_query, List of retrieved memory chunks).
        """
        input_query = data.data  # Unpack the input query
        chunks = []  # Initialize an empty list to store retrieved memory chunks

        # Retrieve memory chunks from each memory module if they are enabled in the configuration
        if self.config["stm"]:
            chunks.extend(self.stm.retrieve(input_query))  # Retrieve from Short-Term Memory (STM)
        if self.config["ltm"]:
            chunks.extend(self.ltm.retrieve(input_query))  # Retrieve from Long-Term Memory (LTM)
        if self.config["dcm"]:
            chunks.extend(self.dcm.retrieve(input_query))  # Retrieve from Dynamic Contextual Memory (DCM)

        # Return the original query along with the list of retrieved memory chunks
        return Data((input_query, chunks))
