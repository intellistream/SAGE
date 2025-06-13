from torch import chunk
from sage.api.operator import 
from sage.api.memory import connect,get_default_manager
from typing import Tuple, List
from sage.api.operator import Data
import ray


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
        self.memory_manager = config.get("memory_manager")  # Get the default memory manager
        self.top_k = self.config["top_k"]  # Set the top_k parameter from config

    def execute(self, data: Data[str]) -> Data[Tuple[str, List[str]]]:
        """
        :param data: A Data object containing a single string (the input query).
        :return: A Data object containing a tuple of (input_query, List of retrieved memory chunks).
        """
        input_query = data.data  # Unpack the input query
        chunks = []  # Initialize an empty list to store retrieved memory chunks
        print(input_query)
        # try:
        # Retrieve memory chunks from each memory module if they are enabled in the configuration
        if self.config["stm"]:
        #     pre_len=len(chunks)
        #     print(self.stm.retrieve(input_query))
        #     chunks.extend(self.stm.retrieve(input_query))  # Retrieve from Short-Term Memory (STM)
        #     self.logger.info(f"short_term_memory retrieve {len(chunks)-pre_len} results")
        # if self.config["ltm"]:
        #     pre_len=len(chunks)
        #     # print(self.ltm.retrieve(input_query))
        #     chunks.extend(self.ltm.retrieve(input_query))  # Retrieve from Long-Term Memory (LTM)
        #     self.logger.info(f"long_term_memory retrieve {len(chunks)-pre_len} results")
        # if self.config["dcm"]:
        #     pre_len=len(chunks)
        #     chunks.extend(self.dcm.retrieve(input_query))  # Retrieve from Dynamic Contextual Memory (DCM)
        #     self.logger.info(f"dynamic_contextual_memory retrieve {len(chunks)-pre_len} results")
        # except Exception as e:
        #     self.logger.error(f"{e} when RetrieverFuction")
            ref = self.memory_manager.retrieve.remote(input_query,"short_term_memory")
            chunks.extend(ray.get(ref))  # Retrieve from Short-Term Memory (STM)
        if self.config["ltm"]:
            ref = self.memory_manager.retrieve.remote(input_query,"long_term_memory")
            chunks.extend(ray.get(ref))  # Retrieve from Short-Term Memory (LTM)
        if self.config["dcm"]:
            ref = self.memory_manager.retrieve.remote(input_query,"dynamic_contextual_memory")
            chunks.extend(ray.get(ref))  # Retrieve from Short-Term Memory (DCM)

        # Return the original query along with the list of retrieved memory chunks
        self.logger.info(f"{self._name} retrieve {len(chunks)} results")
        return Data((input_query, chunks))
