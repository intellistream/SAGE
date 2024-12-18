import logging
from src.core.query_engine.operators.base_operator import BaseOperator
from vllm import LLMEngine
from vllm.lora.request import LoRARequest


class ModelEditor(BaseOperator):
    """
    Operator for dynamically updating the LLM model.
    """

    def __init__(self, llm_engine: LLMEngine):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.llm_engine = llm_engine

    def execute(self, input_data, **kwargs):
        """
        Modify the LLM model based on the input command.
        :param input_data: Command or updates for the LLM model.
        :param kwargs: Additional parameters (e.g., LoRA configurations).
        :return: Success or failure message.
        """
        try:
            lora_request = kwargs.get("lora_request", LoRARequest(**input_data))
            success = self.llm_engine.add_lora(lora_request)

            if success:
                self.logger.info("Model successfully updated with LoRA.")
                return "Model update successful."
            else:
                self.logger.warning("Failed to update model with LoRA.")
                return "Model update failed."

        except Exception as e:
            self.logger.error(f"Error during model update: {str(e)}")
            raise RuntimeError(f"Model update failed: {str(e)}")
