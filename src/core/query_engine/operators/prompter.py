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

            # 合并 context_stm 和 context_ltm 到 history_dialogue
            history_dialogue = input_data.context_ltm + input_data.context_stm
            history_dialogue = "".join(history_dialogue) if history_dialogue else None

            # 将 external_docs 放入 external_corpus
            external_corpus = input_data.external_docs
            external_corpus = "".join(external_corpus) if external_corpus else None

            # 构建 prompt_data 字典
            prompt_data = {
                "question": input_data.natural_query,
                "history_dialogue": history_dialogue,
                "external_corpus": external_corpus
            }

            # Generate the prompt
            input_data.set_last_prompt(generate_prompt(self.prompt_template, **prompt_data))

            # Emit the generated prompt
            self.emit(input_data)
            self.logger.debug("Prompt generated successfully.")

        except Exception as e:
            self.logger.error(f"Error during prompt generation: {str(e)}")
            raise RuntimeError(f"Prompt generation failed: {str(e)}")
