import logging

import ray
from sage.core.compiler.optimizer import Optimizer
from sage.core.compiler.query_parser import QueryParser
from sage.core.dag.dag import DAG
from sage.core.dag.dag_node import BaseDAGNode, ContinuousDAGNode, OneShotDAGNode
from sage.core.compiler.logical_graph_constructor import LogicGraphConstructor


class QueryCompiler:

    def __init__(self,generate_func = None ):
        """
        Initialize the QueryCompiler with memory layers.
        :param memory_manager: Memory manager for managing memory layers.
        :param generate_func: Function for query generation
        """
        self.logical_graph_constructor = LogicGraphConstructor()
        self.optimizer = Optimizer()
        self.parser = QueryParser(generate_func=generate_func)
        self.dag_dict = {}

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

    def compile(self, pipeline=None,config=None):
        """
        Compile a query or natural language input into a DAG.
        :param pipeline: The pipeline object containing data streams.
        :type pipeline: Pipeline
        :param config: Configuration for the pipeline, including query and execution type.
        :type config: dict
        :return: Optimized DAG and execution type.
        """
        dag = None
        config_mapping = {} # Mapping of operator names to their configurations. Not used in this version.
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

        # TODO: Add the optimization logic
        optimized_dag = self.optimizer.optimize(dag)
        node_mapping = {} # Mapping of node names to their configurations. Not used in this version.
        return optimized_dag, execution_type,node_mapping

    def compile_streaming_pipeline(self, pipeline):
        """

        Compile the pipeline.
        :param pipeline: The pipeline object containing data streams.
        :type pipeline: Pipeline
        :raises ValueError: If pipeline data streams are None.
        :return: dag.
        """
        # Implement the pipeline compilation logic here
        
        dag = DAG(id="dag_1",strategy="streaming")
        nodes = []
        config_mapping = {}

        for i, datastream in enumerate(pipeline.data_streams):
            if i == 0:
                node = ContinuousDAGNode(
                    name=datastream.name,
                    operator=datastream.operator,
                    is_spout=True
                )
            else:
                node = ContinuousDAGNode(
                    name=datastream.name,
                    operator=datastream.operator,
                    is_spout=False
                )

      
            nodes.append(node)
            dag.add_node(node)

        # Add Edges
        for i in range(len(nodes) - 1):
            dag.add_edge(nodes[i], nodes[i + 1])

        return dag, config_mapping, "streaming"

    def compile_oneshot_pipeline(self, pipeline, query):
        """

        Compile the pipeline.
        :param pipeline: The pipeline object containing data streams.
        :type pipeline: Pipeline
        :param query: The natural language query string.
        :type query: str
        :raises ValueError: If pipeline data streams are None.
        :raises ValueError: If query is None.
        :raises ValueError: If the intent is not recognized.
        :raises ValueError: If the pipeline is not properly configured.
        :return: dag.
        """
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
            query = source_stream.operator.get_query()

        intent= self.parser.parse_query(natural_query=query)

        if self.dag_dict.get(intent) is not None:
            dag = self.dag_dict.get(intent)
            return dag, "oneshot"
        else:
            pipeline.data_streams = pipeline.data_streams[:1]
        dag = DAG(id="dag_1", strategy="oneshot")
        dag = self.logical_graph_constructor.construct_logical_graph(intent, dag, spout_node)
        operator_cls_mapping = pipeline.get_operator_cls()
        config_mapping = pipeline.get_operator_config()

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

        # 从 spout_node 开始遍历 DAG,并依据DAG的遍历结果构建pipeline
        traversal_result = traverse_dag_from_node(spout_node)
        lst_stream = source_stream
        for node in traversal_result[1:]:
            op_cls = operator_cls_mapping.get(node.name)
            try:
                stream = lst_stream.generalize(node.name, op_cls,pipeline.operator_config)
                node.operator = stream.operator
                lst_stream = stream
            except Exception as e:
                print(str(e))
        self.dag_dict[intent] = dag
        return dag, "oneshot"

    def add_oneshot_spout(self, natural_query):
        """
        Initialize a DAG with a Spout node.
        :param natural_query: The natural language query string.
        :return: Initialized DAG with a Spout node.
        """
        dag = DAG(id="dag_1", strategy="Oneshot")
        spout_node = BaseDAGNode(
            name="Spout",
            operator=None,
            is_spout=True
        )
        dag.add_node(spout_node)
        return dag