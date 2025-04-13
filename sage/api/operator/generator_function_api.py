from sage.api.operator.base_operator_api import BaseOperator
from typing import Any

class GeneratorFunction(BaseOperator):
    """
    Operator for get LLM response
    """
    def __init__(self):
        super().__init__()
        # Default model can be set or passed by subclass
        self.model = None

    def execute(self, combined_prompt: str, context: Any = None) -> str:
        if self.model is None:
            raise ValueError("No model has been assigned to GeneratorFunction")
        return self.model.generate(combined_prompt)