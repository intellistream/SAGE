from sage.api.operator.base_operator_api import BaseOperator
from typing import Any, Tuple, List
from abc import abstractmethod
class PromptFunction(BaseOperator):
    """
    Operator for construct prompt
    """
    def __init__(self):
        super().__init__()
        # Placeholder: should be set to a prompt builder instance
        # self.prompt_constructor = None

    # def set_prompt_constructor(self, prompt_constructor):
    #     self.prompt_constructor = create_prompt_constructor(prompt_constructor)

    @abstractmethod
    def execute(self):
        raise NotImplementedError("PromptFunction must implement execute().")


# # TODO: move this constructor to core
# class PromptConstructorImpl:
#     """
#     Default prompt constructor implementation.
#     Combines query and chunks with a simple template.
#     """
#     def construct(self, query: str, chunks: list[str]) -> str:
#         return query + "\n\n" + "\n".join(chunks)


# def create_prompt_constructor(name: str = "default") -> PromptConstructorImpl:
#     """
#     Factory method to create a prompt constructor instance.

#     Args:
#         name: name of the prompt strategy (default only supported now)

#     Returns:
#         An instance of a prompt constructor.
#     """
#     if name == "default":
#         return PromptConstructorImpl()
#     else:
#         raise ValueError(f"Unknown prompt constructor: {name}")