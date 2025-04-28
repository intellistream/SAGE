# from app.datastream_rag_pipeline import SimpleRetriever
# from sage.api.operator.operator_impl.generator import OpenAIGenerator, HFGenerator
# from sage.api.operator.operator_impl.promptor import QAPromptor
# from sage.api.operator.operator_impl.refiner import AbstractiveRecompRefiner
# from sage.api.operator.operator_impl.reranker import BGEReranker, LLMbased_Reranker
# from sage.api.operator.operator_impl.sink import TerminalSink
# from sage.api.operator.operator_impl.source import FileSource
# from sage.api.operator.operator_impl.writer import SimpleWriter
import ray

from sage.core.compiler.optimizer import Optimizer
from sage.core.compiler.query_parser import QueryParser
from sage.core.dag.dag import DAG
from sage.core.dag.dag_node import BaseDAGNode,ContinuousDAGNode,OneShotDAGNode
from sage.core.compiler.logical_graph_constructor import LogicGraphConstructor
class QueryCompiler:
    def __init__(self, memory_manager = None,generate_func = None ):
        """
        Initialize the QueryCompiler with memory layers.
        :param memory_manager: Memory manager for managing memory layers.
        """
        self.logical_graph_constructor = LogicGraphConstructor()
        self.optimizer = Optimizer()

        self.parser = QueryParser(generate_func=generate_func)

        self.dag_dict = {}

        # self.operator_mapping = {
        #     "OpenAIGenerator": OpenAIGenerator,
        #     "HFGenerator":HFGenerator,
        #     "SimpleRetriever": SimpleRetriever,
        #     "QAPromptor": QAPromptor,
        #     "AbstractiveRecompRefiner": AbstractiveRecompRefiner,
        #     "BGEReranker": BGEReranker,
        #     "LLMbased_Reranker":LLMbased_Reranker,
        #     "TerminalSink": TerminalSink,
        #     "FileSource": FileSource,
        #     "SimpleWriter": SimpleWriter
        # }

    def _parse_query(self, natural_query):
        """
        Parse the query to extract relevant information.
        :param natural_query: The query to process.
        :return: The detected intent (retrieval, summarization, generation, etc.).
        """
        # # parser = QueryParser(generate_func=generate)
        # context = ""
        # parsed_query = self.parser.parse_query(natural_query = natural_query,context=context)
        # return parsed_query

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

    def compile(self, input_text=None, pipeline=None,config=None):
        """
        Compile a query or natural language input into a DAG.
        :param input_text: User-provided query or question.
        :return: Optimized DAG and execution type.
        """
        dag = None
        config_mapping = {}
        execution_type = None
        query = None
        if config.get("query"):
            query = config.get("query")
        if config.get("is_long_running",None) is None :

            dag,execution_type = self.compile_oneshot_pipeline(pipeline,query)
        elif not config.get("is_long_running", None):
            dag, execution_type = self.compile_oneshot_pipeline(pipeline,query)
        elif config.get("is_long_running", None):
            dag,config_mapping,execution_type  = self.compile_streaming_pipeline(pipeline)

        # Optimize the DAG

        optimized_dag = self.optimizer.optimize(dag)

        node_mapping = {}
        # for node in optimized_dag.nodes:
        #     if node.name is not None:
        #         node_mapping[node.name] = {
        #             "config": config_mapping[node.name] if node.name in config_mapping[node.name] else None,
        #             "operator": self.operator_mapping.get(node.name),
        #             "kwargs": None
        #         }

        return optimized_dag, execution_type,node_mapping

    def compile_streaming_pipeline(self,pipeline):
        """
        Compile the pipeline.
        :return: dag.
        """
        # Implement the pipeline compilation logic here
        dag = DAG(id="dag_1",strategy="streaming")
        nodes = []
        config_mapping = {}
        for i,datastream in enumerate(pipeline.data_streams):
            # Add the datastream to the DAG
            if i == 0 :
                node = ContinuousDAGNode(
                    name=datastream.name,
                    operator=datastream.operator,
                    is_spout=True
                )
            else :
                node = ContinuousDAGNode(
                    name=datastream.name,
                    operator=datastream.operator,
                    is_spout=False
                )
            # config_mapping[datastream.name] = {
            #     "config": datastream.config,
            # }
            nodes.append(node)
            dag.add_node(node)
        # Add Edges
        for i in range(len(nodes) - 1):
            dag.add_edge(nodes[i], nodes[i + 1])

        return dag, config_mapping,"streaming"

    def compile_oneshot_pipeline(self, pipeline,query):
        """
        Compile the pipeline.
        :return: dag.
        """
        # Implement the pipeline compilation logic here
        if pipeline.data_streams is None:
            raise ValueError("Pipeline data streams cannot be None.")
        source_stream = pipeline.data_streams[0]
        spout_node = OneShotDAGNode(
            name=source_stream.name,
            operator=source_stream.operator,
            is_spout=True
        )
        if query is None:
            print("query is None")
            input_ref = source_stream.operator.get_query.remote()
            query = ray.get(input_ref)

        intent= self.parser.parse_query(natural_query=query)
        # intent = "question_answering"
        print(f"intent in compiler:{intent}")
        print(pipeline)
        if self.dag_dict.get(intent) is not None:
            dag = self.dag_dict.get(intent)

            return dag, "oneshot"
        else:
            pipeline.data_streams = pipeline.data_streams[:1]

        dag = DAG(id="dag_1", strategy="oneshot")
        dag = self.logical_graph_constructor.construct_logical_graph(intent,dag, spout_node)

        operator_cls_mapping = pipeline.get_operator_cls()
        config_mapping = pipeline.get_operator_config()

        # build the pipeline
        # 遍历DAG,从spout结点开始，按边遍历结点
        def traverse_dag_from_node(start_node):
            """
            从指定的起始节点遍历整个 DAG。
            :param start_node: 起始节点 (BaseDAGNode 实例)。
            :return: 遍历的节点列表。
            """
            visited = set()  # 用于记录已访问的节点
            traversal_order = []  # 记录遍历顺序

            def dfs(node):
                if node in visited:
                    return
                visited.add(node)
                traversal_order.append(node)
                for downstream_node in node.downstream_nodes:
                    dfs(downstream_node)

            dfs(start_node)
            return traversal_order

        # traversal_result = []
        # node = spout_node
        # while node is not None:
        #     traversal_result.append(node)
        #     node = dag.edges.get(node)
        traversal_result = traverse_dag_from_node(spout_node)
        lst_stream = source_stream
        for node in traversal_result[1:]:
            op_cls = operator_cls_mapping.get(node.name)
            try:
                op = op_cls.remote(config_mapping)

                node.operator = op
                stream = lst_stream.generalize(node.name, op)
                lst_stream = stream
            except Exception as e:
                print(node.name)
                print(f"Error in operator instantiation: {e}")





        # nodes = []
        # config_mapping = {}
        # for i, datastream in enumerate(pipeline.data_streams):
        #     # Add the datastream to the DAG
        #     if i == 0:
        #         node = OneShotDAGNode(
        #             name=datastream.name,
        #             operator=datastream.operator,
        #             is_spout=True
        #         )
        #     else:
        #         node = OneShotDAGNode(
        #             name=datastream.name,
        #             operator=datastream.operator,
        #             is_spout=False
        #         )
        #
        #     nodes.append(node)
        #     dag.add_node(node)
        # # Add Edges
        # for i in range(len(nodes) - 1):
        #     dag.add_edge(nodes[i], nodes[i + 1])
        self.dag_dict[intent] = dag
        return dag,  "oneshot"

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

