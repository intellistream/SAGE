from sage.api.operator.base_operator_api import BaseOperator
from typing import Any, Tuple, List

class PromptFunction(BaseOperator):
    def __init__(self):
        super().__init__()
        # Placeholder: should be set to a prompt builder instance
        self.prompt_constructor = None


    def execute(self, inputs: Tuple[str, List[str]], context: Any = None) -> Tuple[str, str]:
        if self.prompt_constructor is None:
            raise ValueError("No prompt constructor assigned to PromptFunction")
        query, chunks = inputs
        prompt = self.prompt_constructor.construct(query, chunks)
        return query, prompt