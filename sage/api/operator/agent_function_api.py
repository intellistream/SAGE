from sage.api.operator.base_operator_api import BaseOperator
from typing import Any

class AgentFunction(BaseOperator):
    """
    Operator for get Agent response
    """
    def __init__(self):
        super().__init__()
        # Default model can be set or passed by subclass
        self.model = None
        self.tools = None
        self.tool_names = None

    def execute(self, combined_prompt: str, context: Any = None) -> str:
        if self.model is None:
            raise ValueError("No model has been assigned to AgentFunction")
        return self.model.generate(combined_prompt)