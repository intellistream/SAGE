import logging
from sage.core.query_engine.operators.base_operator import BaseOperator
from sage.core.prompts.utils import generate_prompt


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
            self.emit(prompt)
            self.logger.debug("Prompt generated successfully.")
        except Exception as e:
            self.logger.error(f"Error during prompt generation: {str(e)}")
            raise RuntimeError(f"Prompt generation failed: {str(e)}")
