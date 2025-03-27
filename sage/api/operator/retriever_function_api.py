from sage.api.operator.base_operator_api import BaseOperator
from typing import Any, Tuple, List

class RetrieverFunction(BaseOperator):
    def __init__(self):
        super().__init__()
        self.embedding_model = None
        self.memory_collections = None
        self.retrieval_func = None


    def execute(self, input_query: str, context: Any = None) -> Tuple[str, List[str]]:
        if self.embedding_model is None or self.memory_collections is None:
            raise ValueError("RetrieverFunction requires both embedding_model model and memory collections")
        embedding = self.embedding_model.embed(input_query)
        chunks = self.memory_collections.retrieve(embedding, self.retrieval_func)
        return input_query, chunks