import logging
from src.core.operators.base_operator import BaseOperator
from vllm import LLMEngine


class Generator(BaseOperator):
    """
    Operator for generating natural language responses using vLLM.
    """

    def __init__(self, llm_engine: LLMEngine):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.llm_engine = llm_engine

    def execute(self, input_data, **kwargs):
        """
        Generate a response using the LLM engine.
        :param input_data: Input query or context.
        :param kwargs: Additional parameters for generation.
        :return: Generated response.
        """
        max_tokens = kwargs.get("max_tokens", 50)
        self.logger.info(f"Generating response for input: {input_data}")
        response = self.llm_engine.generate(input_data, max_tokens=max_tokens)
        self.logger.info(f"Generated response: {response}")
        return response
