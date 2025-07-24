from sage_core.function.map_function import MapFunction

from sage_utils.clients.generator_model import apply_generator_model
from typing import Tuple,List


class AbstractiveRecompRefiner(MapFunction):
    """
    AbstractiveRecompRefiner is an abstractive refiner using the RECOMP approach. 
    This class is responsible for refining retrieved documents by generating concise summaries
    that directly answer a given question. The summary is generated using an external model.

    Attributes:
        logger: Logger for logging errors and information.
        config: Configuration dictionary that holds settings for the refiner (e.g., model parameters).
        model: A model instance used for generating summaries based on the provided input.
    """

    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        """
        Initializes the AbstractiveRecompRefiner instance with configuration and model.

        :param config: Dictionary containing configuration for the refiner, including model details 
                       (method, model_name, base_url, api_key, etc.).
        """
        self.config = config  # Store the refiner configuration
        # Apply the generator model based on provided configuration
        self.model = apply_generator_model(
            method=self.config["method"],
            model_name=self.config["model_name"],
            base_url=self.config["base_url"],
            api_key=self.api_key,
            seed=42  # Set a seed for reproducibility of results
        )

    def execute(self, data: Tuple[str, List[str]]) -> Tuple[str, List[str]]:
        """
        Executes the refining process by generating concise summaries for retrieved documents.

        :param data: A Data object containing a tuple of (query, doc_set), where:
                     - query: The user question that needs to be answered.
                     - doc_set: A list of retrieved documents relevant to the query.

        :return: A Data object containing a tuple (query, emit_docs), where:
                 - query: The original user question.
                 - emit_docs: A list of generated summaries corresponding to the documents.
        """
        try:
            # Unpack the input data into the query and document set
            query, doc_set = data
            emit_docs = []  # List to hold the summaries of the documents
            
            # Process each retrieved document
            for retrieval_docs in doc_set:
                # Format the input for the model (question + document content)
                query, processed_docs = self._format_input(query, retrieval_docs)
                # Build the prompt for the model
                input_prompt = self.build_prompt(query, processed_docs)
                # Generate a summary for the document
                summary = self.model.generate(input_prompt)
                summary = [summary]  # Wrap the summary in a list
                emit_docs.append(summary)  # Add the summary to the list of emitted documents

        except Exception as e:
            # Log any errors that occur during the refining process
            self.logger.error(f"{str(e)} when RefinerFuction")
            raise RuntimeError(f"Refining error: {str(e)}")
        
        # Return the refined results as a Data object
        return (query, emit_docs[0])

    def _format_input(self, question, retrieval_result):
        """
        Formats the input for the model by processing the retrieved documents.

        :param question: The user query that needs to be answered.
        :param retrieval_result: A list of documents retrieved for the question.

        :return: A tuple containing the question and the processed documents, where:
                 - The question remains unchanged.
                 - The documents are formatted into a single string.
        """
        # Process the documents by joining all the lines in each document
        processed_docs = [
            "\n".join(doc.split("\n")[:])  # Here we are just splitting and joining to simulate processing
            for doc in retrieval_result
        ]
        processed_docs = '\n'.join(processed_docs)  # Join all processed documents into one string
        return question, processed_docs

    def build_prompt(self, question, docs):
        """
        Builds the prompt for the model to generate a summary from the provided documents.

        :param question: The user query that needs to be answered.
        :param docs: The processed documents that will be used to generate the summary.

        :return: A list containing a single dictionary, which represents the user prompt in the required format.
        """
        user_content = f"""
        Generate a concise, factual summary from the document below that specifically answers the question. Follow these requirements:
        1. Extract ONLY information directly related to the question
        2. Present results using bullet points or short structured paragraphs
        3. Include critical elements: 
        - Numerical data/percentages 
        - Time periods/dates 
        - Definitive conclusions
        - Named entities (people/organizations/locations)
        4. Exclude speculative statements and irrelevant details

        Question:
        {question}

        Document:
        """
