from sage.core.dag.dag import DAG
from sage.core.dag.dag_node import BaseDAGNode, OneShotDAGNode


class LogicGraphConstructor:
    def __init__(self):
        pass
        # self.memory_manager = memory_manager
    def construct_logical_graph(self,intent, dag, spout_node):

        if intent == "question_answering":
            return self.construct_logical_qa_graph(dag, spout_node)
        elif intent == "summarization":
            return self.construct_logical_summarization_graph(dag, spout_node)
        elif intent == "retrieval":
            return self.construct_logical_retrieval_graph(dag, spout_node)
        elif intent == "generation":
            return self.construct_logical_generation_graph(dag, spout_node)
        elif intent == "classification":
            return self.construct_logical_classification_graph(dag, spout_node)
        return None

    def construct_logical_summarization_graph(self, dag, spout_node):
        """
        Add nodes and edges for a summarization pipeline.
        :param dag: The DAG instance to modify.
        :param spout_node: The Spout node to connect the pipeline to.
        """

        retriever_node = OneShotDAGNode(
            name="SimpleRetriever",
            operator=None,
            is_spout=False
        )
        prompt_node = OneShotDAGNode(
            name="SummarizationPromptor",
            operator=None,
            is_spout=False
        )
        generator_node = OneShotDAGNode(
            name="OpenAIGenerator",
            operator=None,
            is_spout=False
        )
        writer_node = OneShotDAGNode(
            name="LongTimeWriter",
            operator=None,
            is_spout=False
        )
        sink_node = OneShotDAGNode(
            name="TerminalSink",
            operator=None,
            is_spout=False
        )

        dag.add_node(spout_node)
        dag.add_node(retriever_node)
        dag.add_node(prompt_node)
        dag.add_node(generator_node)
        dag.add_node(writer_node)
        dag.add_node(sink_node)

        # Define edges
        dag.add_edge(spout_node, retriever_node)
        dag.add_edge(retriever_node, prompt_node)
        dag.add_edge(prompt_node, generator_node)
        dag.add_edge(generator_node, writer_node)
        dag.add_edge(writer_node, sink_node)
        return dag

    def construct_logical_qa_graph(self, dag, spout_node):
        """
        Add nodes and edges for a summarization pipeline.
        :param dag: The DAG instance to modify.
        :param spout_node: The Spout node to connect the pipeline to.
        """

        retriever_node = OneShotDAGNode(
            name="SimpleRetriever",
            operator=None,
            is_spout=False
        )
        prompt_node = OneShotDAGNode(
            name="QAPromptor",
            operator=None,
            is_spout=False
        )
        generator_node = OneShotDAGNode(
            name="OpenAIGenerator",
            operator=None,
            is_spout=False
        )
        writer_node = OneShotDAGNode(
            name="LongTimeWriter",
            operator=None,
            is_spout=False
        )
        sink_node = OneShotDAGNode(
            name="TerminalSink",
            operator=None,
            is_spout=False
        )

        dag.add_node(spout_node)
        dag.add_node(retriever_node)
        dag.add_node(prompt_node)
        dag.add_node(generator_node)
        dag.add_node(writer_node)
        dag.add_node(sink_node)

        # Define edges
        dag.add_edge(spout_node, retriever_node)
        dag.add_edge(retriever_node, prompt_node)
        dag.add_edge(prompt_node, generator_node)
        dag.add_edge(generator_node, writer_node)
        dag.add_edge(writer_node, sink_node)
        return dag

    def construct_logical_retrieval_graph(self, dag, spout_node):
        retriever_node = OneShotDAGNode(
            name="SimpleRetriever",
            operator=None,
            is_spout=False
        )

        sink_node = OneShotDAGNode(
            name="RetriveSink",
            operator=None,
            is_spout=False
        )
        dag.add_node(spout_node)
        dag.add_node(retriever_node)
        dag.add_node(sink_node)
        # Define edges
        dag.add_edge(spout_node, retriever_node)
        dag.add_edge(retriever_node, sink_node)
        return dag


    def construct_logical_generation_graph(self, dag, spout_node):
        pass


    def construct_logical_classification_graph(self, dag, spout_node):
        pass