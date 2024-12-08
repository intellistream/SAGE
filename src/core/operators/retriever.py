import logging
from src.core.embedding.text_preprocessor import TextPreprocessor
from src.core.operators.base_operator import BaseOperator


class Retriever(BaseOperator):
    """
    Operator for retrieving data from memory layers or external sources.
    """

    def __init__(self, memory_layers, embedder_model="sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the Retriever operator.
        :param memory_layers: Dictionary of memory layers to retrieve data from.
        :param embedder_model: The model to use for embedding generation.
        """
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.memory_layers = memory_layers
        self.embedder = TextPreprocessor(model_name=embedder_model)  # Instantiate the embedder

    def execute(self, input_data, **kwargs):
        """
        Retrieve data relevant to the input query.
        :param input_data: Query or context to retrieve data for.
        :param kwargs: Additional parameters (e.g., number of results).
        :return: Retrieved data.
        """
        try:
            k = kwargs.get("k", 1)
            self.logger.info(f"Generating embedding for query: {input_data}")
            query_embedding = self.embedder.generate_embedding(input_data)

            self.logger.info(f"Retrieving data for query: {input_data}")
            for layer_name, memory in self.memory_layers.items():  # Iterate over dictionary
                results = memory.retrieve(query_embedding, k)
                if results:
                    self.logger.info(f"Data retrieved successfully from {layer_name}.")
                    return results

            self.logger.warning("No data found in any memory layer.")
            return None
        except Exception as e:
            self.logger.error(f"Error during retrieval: {str(e)}")
            raise RuntimeError(f"Retriever execution failed: {str(e)}")
