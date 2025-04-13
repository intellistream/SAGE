from sage.core.dag.dag import DAG
from sage.core.dag.dag_node import BaseDAGNode

class LogicGraphConstructor:
    def __init__(self):
        pass
        # self.memory_manager = memory_manager

    def construct_logical_summarization_graph(self, dag, spout_node):
        """
        Add nodes and edges for a summarization pipeline.
        :param dag: The DAG instance to modify.
        :param spout_node: The Spout node to connect the pipeline to.
        """
        pass


    def construct_logical_qa_graph(self,dag,spout_node):
        """
        Add nodes and edges for a QA pipeline.
        :param dag: The DAG instance to modify.
        :param spout_node: The Spout node to connect the pipeline to.
        """
        # source_node = BaseDAGNode(
        #     name="Source",
        #     operator=None
        # )
        retriever_node = BaseDAGNode(
            name="Retriever",
            operator=None,
            config={"k": 5}  # Retrieve top-5 results
        )
        reranker_node = BaseDAGNode(
            name="Reranker",
            operator=None
        )
        refiner_node = BaseDAGNode(
            name="Refiner",
            operator=None
        )
        prompt_node = BaseDAGNode(
            name="Promptor",
            operator=None
        )

        generator_node = BaseDAGNode(
            name="Generator",
            operator=None
        )

        sink_node = BaseDAGNode(
            name="Sink",
            operator=None
        )

        # dag.add_node(source_node)
        dag.add_node(retriever_node)
        dag.add_node(reranker_node)
        dag.add_node(refiner_node)
        dag.add_node(prompt_node)
        dag.add_node(generator_node)
        dag.add_node(sink_node)

        # Define edges
        # dag.add_edge(spout_node, source_node)
        # dag.add_edge(source_node, retriever_node)
        dag.add_edge(retriever_node, reranker_node)
        dag.add_edge(reranker_node, refiner_node)
        dag.add_edge(refiner_node, prompt_node)
        dag.add_edge(prompt_node, generator_node)
        dag.add_edge(generator_node, sink_node)

        return dag

