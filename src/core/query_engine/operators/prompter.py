import logging
from src.core.query_engine.operators.base_operator import BaseOperator
from src.core.prompts.utils import generate_prompt


class PromptOperator(BaseOperator):
    """
    Operator for generating prompts based on input data and context.
    """

    def __init__(self, prompt_template, format_keys=None):
        """
        Initialize the PromptOperator.
        :param prompt_template: Path to the prompt template.
        :param format_keys: List of keys expected in the input dictionary.
                            Example: ["question", "context", "summary_length"]
        """
        super().__init__()
        self.prompt_template = prompt_template
        self.format_keys = format_keys or []  # Default to an empty list if not provided
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute(self, input_data, **kwargs):
        """
        Generate a prompt using the provided template.
        :param input_data: Input data in any format (tuple, list, dict, etc.).
        :param kwargs: Additional parameters for prompt generation.
        :return: Generated prompt.
        """
        try:
            # Convert input_data to a dictionary if needed
            input_data = self._convert_to_text(input_data[0])
            if not isinstance(input_data, dict):
                if self.format_keys and isinstance(input_data, (tuple, list)):
                    input_data = dict(zip(self.format_keys, input_data))
                else:
                    raise ValueError(
                        "input_data must be a dictionary or match the structure defined in format_keys."
                    )

            # Log the input data for debugging
            self.logger.debug(f"Generating prompt with input data: {input_data}")

            # Generate the prompt
            prompt = generate_prompt(self.prompt_template, **input_data)

            # Emit the generated prompt
            self.emit({"prompt": prompt, "raw_data": input_data})
            self.logger.debug("Prompt generated successfully.")
        except Exception as e:
            self.logger.error(f"Error during prompt generation: {str(e)}")
            raise RuntimeError(f"Prompt generation failed: {str(e)}")

    def _convert_to_text(self, data):
        cleaned_data = {}
        for key, value in data.items():
            if isinstance(value, list):
                # 将列表中的多个字符串用空格连接成一个字符串
                cleaned_data[key] = " ".join(value)
            else:
                # 如果值不是列表，直接保留
                cleaned_data[key] = value
        return cleaned_data
