import logging
from src.core.operators.base_operator import BaseOperator
from vllm import LLMEngine
from vllm.sampling_params import SamplingParams


class Generator(BaseOperator):
    """
    Operator for generating natural language responses using LLMEngine.
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
        try:
            sampling_params = SamplingParams(
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 50),
                top_p=kwargs.get("top_p", 0.9),
            )

            request_id = str(hash(input_data))
            self.logger.info(f"Adding request: {input_data}")

            # Add the request to the LLM engine
            self.llm_engine.add_request(
                request_id=request_id,
                prompt=input_data,
                params=sampling_params,
            )

            # Process the request using the engine
            self.logger.info("Processing request...")
            while self.llm_engine.has_unfinished_requests():
                outputs = self.llm_engine.step()
                for output in outputs:
                    if output.finished and output.request_id == request_id:
                        self.logger.info(f"Generated response: {output.text}")
                        return output.text

        except Exception as e:
            self.logger.error(f"Error during response generation: {str(e)}")
            raise RuntimeError(f"Response generation failed: {str(e)}")
