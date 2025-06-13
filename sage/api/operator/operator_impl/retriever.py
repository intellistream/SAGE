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

    def __init__(self, config:dict):
        """
        Initializes the SimpleRetriever with configuration settings and memory modules.

        :param config: Dictionary containing retriever settings, including top_k and memory module options (STM, LTM, DCM).
        """
        super().__init__()  # Call the parent class's constructor
        self.config = config["retriever"]  # Retrieve retriever-specific configuration
        self.ltm = config["ltm_collection"] 
        self.stm = config["stm_collection"] 
        self.dcm = config["dcm_collection"]
        self.top_k = self.config["top_k"]  # Set the top_k parameter from config

        # 新增：检测memory collection的类型
        self.memory_adapter = self._create_memory_adapter()
    
    def _create_memory_adapter(self):
        """创建内存适配器，处理不同类型的memory collection"""
        from sage.core.runtime.memory_adapter import MemoryAdapter
        return MemoryAdapter()

    async def execute(self, data: Data[str]) -> Data[Tuple[str, List[str]]]:
        """
        :param data: A Data object containing a single string (the input query).
        :return: A Data object containing a tuple of (input_query, List of retrieved memory chunks).
        """
        input_query = data.data  # Unpack the input query
        chunks = []  # Initialize an empty list to store retrieved memory chunks
        print(input_query)
        # Retrieve memory chunks from each memory module if they are enabled in the configuration
        if self.config["stm"]:
            stm_results = await self.memory_adapter.retrieve(self.stm)
            chunks.extend(stm_results)
            # results = self.stm.retrieve.remote()
            # chunks.extend(ray.get(results))# Retrieve from Short-Term Memory (STM)
        if self.config["ltm"]:
            ltm_results = await self.memory_adapter.retrieve(self.ltm, input_query)
            chunks.extend(ltm_results)
            # 保留原有的延迟逻辑
            import asyncio
            await asyncio.sleep(1)
            # results = self.ltm.retrieve.remote(input_query)
            # chunks.extend(ray.get(results))# Retrieve from Long-Term Memory (LTM)
            # import time
            # time.sleep(1)
        if self.config["dcm"]:
            dcm_results = await self.memory_adapter.retrieve(self.dcm)
            chunks.extend(dcm_results)
            # results = self.dcm.retrieve.remote()
            # chunks.extend(ray.get(results))# Retrieve from Short-Term Memory (DCM)
        # Return the original query along with the list of retrieved memory chunks
        self.logger.info(f"{self._name} retrieve {len(chunks)} results")
        return Data((input_query, chunks))
