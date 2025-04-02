from sage.api.operator.base_operator_api import BaseOperator
from typing import Any, Tuple, List

class RetrieverFunction(BaseOperator):
    def __init__(self):
        super().__init__()
        self.memory_collections = None
        self.retrieval_func = None


    def execute(self, input_query: str, context: Any = None) -> Tuple[str, List[str]]:

        if self.memory_collections is None:
        chunks = self.memory_collections.retrieve(input_query, self.retrieval_func)
        
        return input_query, chunks