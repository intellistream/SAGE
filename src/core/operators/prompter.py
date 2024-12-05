import logging
from src.core.operators.base_operator import BaseOperator


class Prompter(BaseOperator):
    """
    Operator for generating dynamic prompts based on user queries.
    """

    def __init__(self, template="Default prompt: {query}"):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template = template

    def execute(self, input_data, **kwargs):
        """
        Generate a prompt using the input query.
        :param input_data: User query.
        :param kwargs: Additional parameters.
        :return: Generated prompt.
        """
        self.logger.info(f"Generating prompt for query: {input_data}")
        prompt = self.template.format(query=input_data)
        return prompt
