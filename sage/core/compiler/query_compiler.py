from app.datastream_rag_pipeline import SimpleRetriever
from sage.api.operator.operator_impl import generator, retriever, promptor, refiner, reranker, sink, source, writer
from sage.api.operator.operator_impl.generator import OpenAIGenerator, HFGenerator
from sage.api.operator.operator_impl.promptor import QAPromptor
from sage.api.operator.operator_impl.refiner import AbstractiveRecompRefiner
from sage.api.operator.operator_impl.reranker import BGEReranker, LLMbased_Reranker
from sage.api.operator.operator_impl.sink import TerminalSink
from sage.api.operator.operator_impl.source import FileSource
from sage.api.operator.operator_impl.writer import SimpleWriter
from sage.core.compiler.optimizer import Optimizer
from sage.core.compiler.query_parser import QueryParser
from sage.core.dag.dag import DAG
from sage.core.dag.dag_node import BaseDAGNode
from sage.core.compiler.logical_graph_constructor import LogicGraphConstructor
from sage.api.operator.operator_impl import *
class QueryCompiler:
    def __init__(self, memory_manager = None,generate_func = None ):
        """
        Initialize the QueryCompiler with memory layers.
        :param memory_manager: Memory manager for managing memory layers.
        """
        self.memory_manager = memory_manager
        self.optimizer = Optimizer()
        self.parser = QueryParser(generate_func=generate_func)

        self.operator_mapping = {
            "OpenAIGenerator": OpenAIGenerator,
            "HFGenerator":HFGenerator,
            "SimpleRetriever": SimpleRetriever,
            "QAPromptor": QAPromptor,
            "AbstractiveRecompRefiner": AbstractiveRecompRefiner,
            "BGEReranker": BGEReranker,
            "LLMbased_Reranker":LLMbased_Reranker,
            "TerminalSink": TerminalSink,
            "FileSource": FileSource,
            "SimpleWriter": SimpleWriter
        }

    def _parse_query(self, natural_query):
        """
        Parse the query to extract relevant information.
        :param natural_query: The query to process.
        :return: The detected intent (retrieval, summarization, generation, etc.).
        """
        # parser = QueryParser(generate_func=generate)
        context = ""
        parsed_query = self.parser.parse_query(natural_query = natural_query,context=context)
        return parsed_query

    # def add_spout(self, natural_query):
    #     """
    #     Initialize a DAG with a Spout node.
    #     :param natural_query: The natural language query string.
    #     :return: Initialized DAG with a Spout node.
    #     """
    #     dag = DAG(id="dag_1",strategy="Oneshot")
    #     spout_node = BaseDAGNode(
    #         name="Spout",
    #         operator=None,
    #         is_spout=True
    #     )
    #     dag.add_node(spout_node)
    #     return dag


    def compile_natural_query(self, natural_query):
        """
        Compile a natural language query into a DAG.
        :param natural_query: The natural language query string.
        :return: DAG instance.
        """
        # Step 1: Parse the question to understand the user's intent
        intent = self._parse_query(natural_query)

        # Step 2: Initialize the DAG and add the Spout node
        dag = self.add_oneshot_spout(natural_query)

        # Step 3: Construct the logical graph based on the intent
        logical_graph_constructor = LogicGraphConstructor()
        spout_node = dag.get_node_by_name("Spout")

        if intent == "summarization":
            pass
        elif intent == "question_answering":
            logical_graph_constructor.construct_logical_qa_graph(dag, spout_node)
        elif intent == "retrieval":
            pass
        elif intent == "generation":
            pass
        elif intent == "classification":
            pass
        else:
            raise ValueError(f"Unsupported query type: {intent}")

        return dag

    def compile(self, input_text=None, pipeline=None):
        """
        Compile a query or natural language input into a DAG.
        :param input_text: User-provided query or question.
        :return: Optimized DAG and execution type.
        """
        dag = None
        config_mapping = {}
        execution_type = None
        if input_text is not None :
            dag, execution_type = self.compile_natural_query(input_text), "oneshot"
        if pipeline is not None:
            dag,config_mapping,execution_type  = self.compile_pipeline(pipeline)
        # Optimize the DAG

        optimized_dag = self.optimizer.optimize(dag)

        node_mapping = {}
        for node in optimized_dag.nodes:
            if node.name is not None:
                node_mapping[node.name] = {
                    "config": config_mapping[node.name] if node.name in config_mapping[node.name] else None,
                    "operator": self.operator_mapping.get(node.name),
                    "kwargs": None
                }

        return optimized_dag, execution_type,node_mapping

    def compile_pipeline(self,pipeline):
        """
        Compile the pipeline.
        :return: dag.
        """
        # Implement the pipeline compilation logic here
        dag = DAG(id="dag_1",strategy="streaming")
        nodes = []
        config_mapping = {}
        for datastream in pipeline.datastreams:
            # Add the datastream to the DAG
            node = BaseDAGNode(
                name=datastream.name,
                operator=None,
                is_spout=False
            )
            config_mapping[datastream.name] = {
                "config": datastream.config,
            }
            nodes.append(node)
            dag.add_node(node)
        # Add Edges
        for i in range(len(nodes) - 1):
            dag.add_edge(nodes[i], nodes[i + 1])

        return dag, config_mapping,"streaming"

    def add_oneshot_spout(self, natural_query):
        """
        Initialize a DAG with a Spout node.
        :param natural_query: The natural language query string.
        :return: Initialized DAG with a Spout node.
        """
        dag = DAG(id="dag_1",strategy="Oneshot")
        spout_node = BaseDAGNode(
            name="Spout",
            operator=None,
            is_spout=True
        )
        dag.add_node(spout_node)
        return dag

