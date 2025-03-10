import logging
from idlelib import history

from pandas.tests.series.methods.test_rank import results

from src.core.embedding.text_preprocessor import TextPreprocessor
from src.core.neuromem.manager.memory_manager import NeuronMemManager
from src.core.query_engine.operators.base_operator import BaseOperator


def _aggregate_results(*results):
    """
    Aggregate and deduplicate results from multiple memory layers.

    :param results: Lists of results from memory layers.
    :return: Combined, deduplicated list of results.
    """
    seen = set()
    aggregated = []
    for result_list in results:
        for result in result_list:
            result_key = str(result)  # Convert result to a hashable key
            if result_key not in seen:
                aggregated.append(result)
                seen.add(result_key)
    return aggregated


class Retriever(BaseOperator):
    """
    Operator for retrieving data from the long-term memory.
    """
    memory_manager: NeuronMemManager

    def __init__(self, memory_manager, embedder_model="sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the Retriever operator.
        :param memory_manager: The memory manager instance to retrieve memory from varying layers.
        :param embedder: An embedder instance to generate embeddings.
        """
        super().__init__()
        self.memory_manager = memory_manager
        self.embedder = TextPreprocessor(model_name=embedder_model)  # Instantiate the embedder
        self.logger = logging.getLogger(self.__class__.__name__)

    # TODO: determine the type of the input data, the current type is list, but we need to figure out why we need a list here.
    def execute(self, input_data, **kwargs):
        """
        Retrieve data relevant to the input query from long-term memory.
        :param input_data: Query or context to retrieve data for.
        :param kwargs: Additional parameters (e.g., number of results).
        :return: Retrieved data.
        """
        try:
            k = kwargs.get("k", 1)  # Number of results to retrieve
            self.logger.info(f"Generating embedding for query: {input_data.natural_query}")

            # Generate embedding from the query
            query_embedding = self.embedder.generate_embedding(input_data.natural_query) ### NLPer how to best embedding the question.

            # Retrieve results from memory layers
            self.logger.info(f"Retrieving data from memory layers for query: {input_data.natural_query}")

            short_term_results = self.memory_manager.retrieve_from_memory(memory_layer="short_term", k=k)
            long_term_results = self.memory_manager.retrieve_from_memory(
                memory_layer="long_term", query_embedding=query_embedding, k=k
            )
            contextual_results = self.memory_manager.retrieve_from_memory(
                memory_layer="dynamic_contextual", query_embedding=query_embedding, k=k
            )

            contextual_results = [item for item in contextual_results if item is not None]
            short_term_results = [item for item in short_term_results if item is not None]
            long_term_results = [item for item in long_term_results if item is not None]

            input_data.add_external_doc(contextual_results)
            input_data.add_context_stm(short_term_results)
            input_data.add_context_ltm(long_term_results)

            self.emit(input_data)
            self.logger.warning("No data found in memory.")

        except Exception as e:
            self.logger.error(f"Error during retrieval: {str(e)}")
            raise RuntimeError(f"Retriever execution failed: {str(e)}")

