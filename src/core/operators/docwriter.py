import logging
from src.core.operators.base_operator import BaseOperator


class Docwriter(BaseOperator):
    """
    Operator for generating structured documentation or outputs.
    """

    def __init__(self, template="Document for {data}"):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template = template

    def execute(self, input_data, **kwargs):
        """
        Generate a structured document using the template.
        :param input_data: Input data to structure into documentation.
        :param kwargs: Additional parameters.
        :return: Generated document.
        """
        self.logger.info(f"Generating document for input: {input_data}")
        document = self.template.format(data=input_data)
        self.logger.info("Document generated successfully.")
        return document
