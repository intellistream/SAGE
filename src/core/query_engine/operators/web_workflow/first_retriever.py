import logging
from src.core.embedding.text_preprocessor import TextPreprocessor


class FirstRetriever():
    """
    Operator for retrieving data from the long-term memory.
    """

    def __init__(self, long_term_memory, embedder_model="sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the Retriever operator.
        :param long_term_memory: The long-term memory instance to retrieve data from.
        :param embedder: An embedder instance to generate embeddings.
        """
        super().__init__()
        self.long_term_memory = long_term_memory
        self.embedder = TextPreprocessor(model_name=embedder_model)  # Instantiate the embedder
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute(self, query, **kwargs):
        """
        Retrieve data relevant to the input query from long-term memory.
        :param input_data: Query or context to retrieve data for.
        :param kwargs: Additional parameters (e.g., number of results).
        :return: Retrieved data.
        """
        try:
            k = kwargs.get("K", 1)  # Number of results to retrieve
            self.logger.info(f"Generating embedding for query: {query}")

            # Generate embedding from the query
            query_embedding = self.embedder.generate_embedding(query) ### NLPer how to best embedding the question.

            self.logger.info(f"Retrieving data from long-term memory for query: {query}")

            results = self.long_term_memory.retrieve(query=query_embedding, k=k)
            
            if results:
                self.logger.info(f"Data retrieved successfully: {len(results)} result(s) found.")
                # Emit the raw query and results
                return results
            else:
                self.logger.warning("No data found in long-term memory.")

        except Exception as e:
            self.logger.error(f"Error during retrieval: {str(e)}")
            raise RuntimeError(f"Retriever execution failed: {str(e)}")
