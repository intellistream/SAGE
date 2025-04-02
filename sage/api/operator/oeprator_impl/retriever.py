from sage.api.operator import RetrieverFunction
import sage
from typing import Tuple, List
# Retriever operator: embeds the query and retrieves top-k relevant chunks from memory
class SimpleRetriever(RetrieverFunction):
    def __init__(self):
        super().__init__()
        # Initialize the embedding_model model for vectorization
        self.embedding_model = sage.model.apply_embedding_model("default")
        # Connect to multiple memory collections (STM, LTM, DCM)
        # self.memory_collections = sage.memory.connect(
        #     "short_term_memory", "long_term_memory", "dynamic_contextual_memory"
        # )
        self.stm = sage.memory.connect("short_term_memory")
        self.ltm = sage.memory.connect("long_term_memory")
        self.dcm = sage.memory.connect("dynamic_contextual_memory")
        # Define the retrieval function (e.g., weighted aggregation, similarity ranking)
        self.retrieval_func = sage.memory.retrieve_func

    # Returns both the original query and the retrieved memory chunks
    def execute(self, input_query: str, context=None) -> Tuple[str, List[str]]:
        embedding = self.embedding_model.embed(input_query)
        chunks = self.stm.retrieve(embedding, self.retrieval_func)
        return input_query, chunks