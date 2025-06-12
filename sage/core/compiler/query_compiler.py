import ray
from sage.core.compiler.optimizer import Optimizer
from sage.core.compiler.query_parser import QueryParser
from sage.core.dag.dag import DAG
from sage.core.dag.dag_node import BaseDAGNode, ContinuousDAGNode, OneShotDAGNode
from sage.core.compiler.logical_graph_constructor import LogicGraphConstructor


class QueryCompiler:
    def __init__(self, memory_manager=None, generate_func=None):
        """
        Initialize the QueryCompiler with memory layers.
        :param memory_manager: Memory manager for managing memory layers.
        :param generate_func: Function for query generation
        """
        self.logical_graph_constructor = LogicGraphConstructor()
        self.optimizer = Optimizer()
        self.parser = QueryParser(generate_func=generate_func)
        self.dag_dict = {}

    def _parse_query(self, natural_query):
        """
        Parse the query to extract relevant information.
        :param natural_query: The query to process.
        :return: The detected intent (retrieval, summarization, generation, etc.).
        """
        pass  # Placeholder implementation

    def compile(self, input_text=None, pipeline=None, config=None):
        """
        Compile a query or natural language input into a DAG.
        :param input_text: User-provided query or question.
        :param pipeline: Data processing pipeline
        :param config: Configuration dictionary
        :return: Optimized DAG, execution type, and node mapping
        """
        dag = None
        config_mapping = {}
        execution_type = None
        query = config.get("query") if config else None

        if config and config.get("is_long_running") is not None:
            if not config.get("is_long_running"):
                dag, execution_type = self.compile_oneshot_pipeline(pipeline, query)
            else:
                dag, config_mapping, execution_type = self.compile_streaming_pipeline(pipeline)

        # Optimize the DAG
        optimized_dag = self.optimizer.optimize(dag) if dag else None

        node_mapping = {}
        return optimized_dag, execution_type, node_mapping

    def compile_streaming_pipeline(self, pipeline):
        """
        Compile the streaming pipeline.
        :param pipeline: Data processing pipeline
        :return: DAG, configuration mapping and execution type
        """
        dag = DAG(id="dag_1", strategy="streaming")
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
        Compile the oneshot pipeline.
        :param pipeline: Data processing pipeline
        :param query: Natural language query
        :return: DAG and execution type
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
            input_ref = source_stream.operator.get_query.remote()
            query = ray.get(input_ref)

        intent = self.parser.parse_query(natural_query=query)
        print(f"intent in compiler:{intent}")
        print(pipeline)

        if self.dag_dict.get(intent) is not None:
            dag = self.dag_dict.get(intent)
            return dag, "oneshot"
        else:
            pipeline.data_streams = pipeline.data_streams[:1]

        dag = DAG(id="dag_1", strategy="oneshot")
        dag = self.logical_graph_constructor.construct_logical_graph(intent, dag, spout_node)

        operator_cls_mapping = pipeline.get_operator_cls()
        config_mapping = pipeline.get_operator_config()

        # Traverse DAG and update operators
        traversal_result = []
        current_node = spout_node
        while current_node is not None:
            traversal_result.append(current_node)
            current_node = dag.edges.get(current_node)

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