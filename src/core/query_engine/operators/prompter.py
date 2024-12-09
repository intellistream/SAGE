import logging
from src.core.query_engine.operators.base_operator import BaseOperator
from src.core.prompts.utils import generate_prompt


class PromptOperator(BaseOperator):
    """
    Operator for generating prompts based on input data and context.
    """

    def __init__(self, prompt_template):
        """
        Initialize the PromptOperator.
        :param prompt_template: Path to the prompt template.
        """
        super().__init__()
        self.prompt_template = prompt_template
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute(self, input_data, **kwargs):
        """
        Generate a prompt using the provided template.
        :param input_data: A dictionary containing keys required by the template.
                           Example: {"question": <query>, "context": <context>, "summary_length": <length>}
        :param kwargs: Additional parameters for prompt generation.
        :return: Generated prompt.
        """
        try:
            if not isinstance(input_data, dict):
                raise ValueError("input_data must be a dictionary with keys matching the template placeholders.")

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
