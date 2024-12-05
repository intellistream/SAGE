import logging
from src.core.operators.base_operator import BaseOperator


class HallucinationDetection(BaseOperator):
    """
    Operator for detecting hallucinations in generated responses.
    """

    def __init__(self, max_retries=3):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.max_retries = max_retries

    def execute(self, input_data, **kwargs):
        """
        Detect hallucinations in the response.
        :param input_data: Generated response.
        :param kwargs: Additional parameters (e.g., retriever for fallback retrieval).
        :return: A tuple (is_hallucination, corrected_data)
        """
        retriever = kwargs.get("retriever")
        retry_count = 0

        #TODO: XUDONG LI
        while retry_count < self.max_retries:
            self.logger.info(f"Hallucination detection attempt {retry_count + 1}.")
            if self._is_hallucination(input_data):
                self.logger.warning("Hallucination detected, retrying retrieval.")
                input_data = retriever.execute(input_data)
                retry_count += 1
            else:
                return False, input_data

        self.logger.error("Max retries reached, hallucination not resolved.")
        return True, input_data

    #TODO: LUAN ZHANG && XUDONG LI
    def _is_hallucination(self, response):
        """
        Placeholder for hallucination detection logic.
        :param response: Generated response to check.
        :return: True if hallucination detected, otherwise False.
        """
        # Replace with actual detection logic
        return "ERROR" in response
