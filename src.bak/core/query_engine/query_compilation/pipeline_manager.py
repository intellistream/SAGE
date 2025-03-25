from urllib3.filepost import writer

from sage.core.query_engine.operators.generator import Generator
from sage.core.query_engine.operators.memwriter import MemWriter
from sage.core.query_engine.operators.prompter import PromptOperator
from sage.core.query_engine.operators.retriever import Retriever
from sage.core.query_engine.operators.summarizer import Summarizer
from sage.core.query_engine.dag.one_shot_dag_node import OneShotDAGNode
from sage.utils.file_path import SUMMARIZATION_PROMPT_TEMPLATE, QAPROMPT_TEMPLATE


class PipelineManager:
    """
    Manages the addition of pipelines to a DAG based on intent.
    """

    def __init__(self, memory_manager):
        """
        Initialize the manager with necessary resources.
        :param memory_manager: A manager of memory layers (e.g., long-term, short-term, dynamic-contextual).
        """
        self.memory_manager = memory_manager

    def add_summarization_pipeline(self, dag, spout_node):
        """
        Add nodes and edges for a summarization pipeline.
        :param dag: The DAG instance to modify.
        :param spout_node: The Spout node to connect the pipeline to.
        """
        retriever_node = OneShotDAGNode(
            name="Retriever",
            operator=Retriever(self.memory_manager),
            config={"k": 5}  # Retrieve top-5 results
        )
        prompt_node = OneShotDAGNode(
            name="PromptGenerator",
            operator=PromptOperator(prompt_template=SUMMARIZATION_PROMPT_TEMPLATE, format_keys = ["context", "summary_length"])
        )
        summarizer_node = OneShotDAGNode(
            name="Summarizer",
            operator=Summarizer(),
            config={"summary_length": 100}  # Example configuration for summarization
        )

        dag.add_node(retriever_node)
        dag.add_node(prompt_node)
        dag.add_node(summarizer_node)

        # Define edges
        dag.add_edge(spout_node, retriever_node)
        dag.add_edge(retriever_node, prompt_node)
        dag.add_edge(prompt_node, summarizer_node)

    def add_question_answering_pipeline(self, dag, spout_node):
        """
        Add nodes and edges for a question-answering pipeline.
        :param dag: The DAG instance to modify.
        :param spout_node: The Spout node to connect the pipeline to.
        """
        retriever_node = OneShotDAGNode(
            name="Retriever",
            operator=Retriever(self.memory_manager),
            config={"k": 5}  # Retrieve top-5 results
        )
        prompt_node = OneShotDAGNode(
            name="PromptGenerator",
            operator=PromptOperator(prompt_template=QAPROMPT_TEMPLATE, format_keys = ["question", "context"])
        )
        generator_node = OneShotDAGNode(
            name="Generator",
            operator=Generator(),
            config={"max_length": 50}  # Example configuration for generation
        )

        writer_node = OneShotDAGNode(
            name="MemWriter",
            operator=MemWriter(self.memory_manager),
        )

        dag.add_node(retriever_node)
        dag.add_node(prompt_node)
        dag.add_node(generator_node)
        dag.add_node(writer_node)

        # Define edges
        dag.add_edge(spout_node, retriever_node)
        dag.add_edge(retriever_node, prompt_node)
        dag.add_edge(prompt_node, generator_node)
        dag.add_edge(generator_node, writer_node)
