from src.core.query_engine.operators.web_workflow.html_parser import HTML_Parser
from src.core.query_engine.operators.web_workflow.first_retriever import FirstRetriever
from src.core.query_engine.operators.web_workflow.hybrid_retriever import HybridRetriever
from src.core.query_engine.operators.web_workflow.web_prompter import WebPrompter
from src.core.query_engine.operators.web_workflow.sa_generator import SAGenerator
from src.core.neuromem.memory.utils import initialize_memory_layers
from src.utils.file_path import QA_SELF_EVAL_PROMPT_TEMPLATE, KG_RESULTS_FILE
import logging

class WebWorkFlow():
    """
    WebWorkFlow class responsible for orchestrating the web-based retrieval-augmented generation (RAG) workflow.
    This class handles the parsing of HTML content, multi-stage retrieval of web results, user prompting for relevance feedback,
    and the generation of the final response based on the retrieved information.
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.K = 10  # Number of results to retrieve in the first stage
        self.M = 5   # Number of results to sparse retrieve in the second stage
        self.N = 5   # Number of results to dense retrieve in the second stage

    def execute(self, memory_layers):
        """
        Execute the web workflow operator.
        :param memory_layers: The memory layers to store the processed data.
        :return: None
        """
        try:
            long_term_memory = memory_layers.get("long_term")
            short_term_memory = memory_layers.get("short_term")

            # Extract the kg results from file
            kg_results = ""
            try:
                with open(KG_RESULTS_FILE, "r", encoding="utf-8") as file:
                    kg_results = file.read()
            except Exception as e:
                self.logger.error(f"Error reading KG results: {str(e)}")
                pass

            # Step1: Initialize the HTML parser and Store the search results in long-term memory
            # NOTE: 初始时已将search_results存入long-term memory，代替了Step1
            # parser = HTML_Parser(long_memory, search_results)
            # parser.execute()

            # Step2: Multi-stage retrieval
            query = short_term_memory.retrieve("query")
            query_time = short_term_memory.retrieve("query_time")

            first_retriever = FirstRetriever(long_term_memory)
            first_results = first_retriever.execute(query=query, K=self.K)

            hybrid_retriever = HybridRetriever()
            web_results = hybrid_retriever.execute(query=query,first_results=first_results, M=self.M, N=self.N)
            
            # Step3: Prompt the user to select the most relevant result
            prompter = WebPrompter(QA_SELF_EVAL_PROMPT_TEMPLATE)
            format_prompt = prompter.execute(query, query_time, web_results, kg_results)

            # Step4: Generate the final response
            generator = SAGenerator()
            response = generator.execute(format_prompt)
            
        except Exception as e:
            self.logger.error(f"WebWorkflow: Error during web workflow execution: {str(e)}")
            raise RuntimeError(f"WebWorkflow: Failed to execute web workflow: {str(e)}")
