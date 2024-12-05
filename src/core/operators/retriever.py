import logging

from torch.ao.nn.qat import Embedding

from src.core.operators.base_operator import BaseOperator


class Retriever(BaseOperator):
    """
    Operator for retrieving data from memory layers or external sources.
    """

    def __init__(self, memory_layers):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.memory_layers = memory_layers

    def execute(self, input_data, **kwargs):
        """
        Retrieve data relevant to the input query.
        :param input_data: Query or context to retrieve data for.
        :param kwargs: Additional parameters (e.g., number of results).
        :return: Retrieved data.
        """

        # # 1st execution
        # embedding =  Embedding(input_data)
        # model_state = memory.add (embedding)
        # if(model_state is not None):
        #         Embedding.update(model_state)
        #
        k = kwargs.get("k", 1)
        self.logger.info(f"Retrieving data for query: {input_data}")
        for memory in self.memory_layers:
            results = memory.retrieve(input_data, k)
            if results:
                self.logger.info("Data retrieved successfully.")
                return results
        self.logger.warning("No data found in any memory layer.")
        return None
