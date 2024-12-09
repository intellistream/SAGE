from src.core.query_engine.dag import DAGNode
from src.core.operators.generator import Generator
from src.core.operators.retriever import Retriever
from src.core.operators.summarizer import Summarizer


class PipelineManager:
    """
    Manages the addition of pipelines to a DAG based on intent.
    """

    def __init__(self, memory_layers):
        """
        Initialize the manager with necessary resources.
        :param memory_layers: A dictionary of memory layers (e.g., long-term, short-term).
        """
        self.memory_layers = memory_layers

    def add_summarization_pipeline(self, dag, spout_node):
        """
        Add nodes and edges for a summarization pipeline.
        :param dag: The DAG instance to modify.
        :param spout_node: The Spout node to connect the pipeline to.
        """
        retriever_node = DAGNode(
            name="Retriever",
            operator=Retriever(self.memory_layers.get("long_term")),
            config={"k": 5}
        )
        summarizer_node = DAGNode(
            name="Summarizer",
            operator=Summarizer(),
            config={"summary_length": 100}
        )
        dag.add_node(retriever_node)
        dag.add_node(summarizer_node)
        dag.add_edge(spout_node, retriever_node)
        dag.add_edge(retriever_node, summarizer_node)

    def add_question_answering_pipeline(self, dag, spout_node):
        """
        Add nodes and edges for a question-answering pipeline.
        :param dag: The DAG instance to modify.
        :param spout_node: The Spout node to connect the pipeline to.
        """
        retriever_node = DAGNode(
            name="Retriever",
            operator=Retriever(self.memory_layers.get("long_term")),
            config={"k": 3}
        )
        generator_node = DAGNode(
            name="Generator",
            operator=Generator(),
            config={"max_length": 50}
        )
        dag.add_node(retriever_node)
        dag.add_node(generator_node)
        dag.add_edge(spout_node, retriever_node)
        dag.add_edge(retriever_node, generator_node)
