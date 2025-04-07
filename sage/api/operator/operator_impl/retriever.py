from sage.api.operator import RetrieverFunction
from sage.api.memory import connect,get_default_manager
from typing import Tuple, List
from sage.api.operator import Data

# Retriever operator: embeds the query and retrieves top-k relevant chunks from memory
class SimpleRetriever(RetrieverFunction):
    def __init__(self,config):
        super().__init__()
        self.config=config["retriever"]
        self.memory_manager=get_default_manager()
        self.top_k=self.config["top_k"]
        if self.config["stm"]:
            self.stm = connect(self.memory_manager,"short_term_memory")
        if self.config["ltm"]:
            self.ltm = connect(self.memory_manager,"long_term_memory")
        if self.config["dcm"]:
            self.dcm = connect(self.memory_manager,"dynamic_contextual_memory")

    # Returns both the original query and the retrieved memory chunks
    def execute(self, data:Data[str]) -> Data[Tuple[str, List[str]]]:
        input_query=data.data
        chunks = []
        if self.config["stm"]:
            chunks.extend(self.stm.retrieve(input_query))
        if self.config["ltm"]:
            chunks.extend(self.ltm.retrieve(input_query))
        if self.config["dcm"]:
            chunks.extend(self.dcm.retrieve(input_query))

        return Data((input_query,chunks))