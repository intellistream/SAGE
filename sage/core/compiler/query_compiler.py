# deprecated


from typing import Dict, Type, Any, TYPE_CHECKING, Union
# from sage.core.compiler.optimizer import Optimizer
from sage.core.compiler.query_parser import QueryParser
from sage.core.dag.local.dag import DAG
from sage.core.dag.local.dag_node import BaseDAGNode, OneShotDAGNode
from sage.core.compiler.logical_graph_constructor import LogicGraphConstructor
from sage.core.runtime.local.local_dag_node import LocalDAGNode
from sage.core.io.message_queue import MessageQueue
from sage.core.dag.ray.ray_dag import RayDAG
if TYPE_CHECKING:
    from sage.core.graph import SageGraph, GraphEdge
from sage.utils.custom_logger import CustomLogger

class QueryCompiler:

    def __init__(self):
        """
        Initialize the QueryCompiler with memory layers.
        :param memory_manager: Memory manager for managing memory layers.
        :param generate_func: Function for query generation
        """
        self.session_folder = CustomLogger.get_session_folder()
        self.logical_graph_constructor = LogicGraphConstructor()
        # self.optimizer = Optimizer()
        self.parser = QueryParser(generate_func=None)
        self.dag_dict = {}
        self.logger = CustomLogger(
            object_name=f"QueryCompiler",
            log_level="DEBUG",
            console_output=False,
            file_output=True
        )

    def compile_graph(self, graph:'SageGraph') -> Union[DAG, RayDAG]: # deprecated
        platform = graph.config.get("platform", "local")
        self.logger.info(f"Compiling graph '{graph.name}' ")

        if platform == "ray":
            return self._compile_graph_for_ray(graph)
        else:
            return self._compile_graph_for_local(graph)
        

    def _compile_graph_for_ray(self, graph:'SageGraph') -> RayDAG: # deprecated
        """Ray-specific compilation logic returning RayDAG."""
        if(graph.config.get("is_long_running", False) is False):
            strategy = "oneshot"
        else:
            strategy = "streaming"
        self.logger.info(f"Compiling graph '{graph.name}' for Ray with strategy '{strategy}'")
        
        ray_dag = RayDAG(name=f"{graph.name}", strategy=strategy, session_folder = self.session_folder)
        ray_dag.platform = "ray"
        # operator_factory = OperatorFactory(True)  # Ray-enabled factory
        
        # Step 1: Create all Ray Actor DAG nodes
        for node_name, graph_node in graph.nodes.items():
            # Extract operator class and configuration instead of creating instance
            function_class = graph_node.operator
            operator_config = graph_node.config or {}
            
            from sage.core.runtime.ray.ray_dag_node import RayDAGNode
            from sage.core.runtime.collection_wrapper import CollectionWrapper
            
            # Create Ray Actor with operator class, not instance
            #print("ltm_collection 类型：", type(operator_config["retriever"]["ltm_collection"]))
            
            # wrapper:CollectionWrapper = operator_config["retriever"]["ltm_collection"]
            # operator_config["retriever"]["ltm_collection"] = wrapper._collection
            ray_actor = RayDAGNode.remote(
                name=graph_node.name,
                function_class=function_class,
                operator_config=operator_config,
                is_spout=(graph_node.type == "source"), 
                session_folder = self.session_folder
            )
            # Add to RayDAG - use graph's get_upstream_nodes method
            upstream_nodes = graph.get_upstream_nodes(node_name)
            ray_dag.add_ray_actor(
                name=node_name,
                actor=ray_actor,
                is_spout=(graph_node.type == "source"),
                upstream_nodes=upstream_nodes
            )
        
        # Step 2: Connect Ray actors with proper channel mapping
        for edge_name, edge in graph.edges.items():
            
            # Get channel information from edge
            upstream_output_channel = edge.upstream_channel
            downstream_input_channel = edge.downstream_channel
            self.logger.info(f"Connecting actors '{edge.upstream_node.name}' "
                             f"to {edge.downstream_node.name}")
            
            # Connect actors with correct channel mapping
            ray_dag.connect_actors(
                upstream_name=edge.upstream_node.name,
                upstream_output_channel=upstream_output_channel,
                downstream_name=edge.downstream_node.name,
                downstream_input_channel=downstream_input_channel
            )
        return ray_dag

    def _compile_graph_for_local(self, graph:'SageGraph')->DAG: # deprecated
        strategy = "streaming" if graph.config.get("is_long_running", False) else "oneshot"
        
        dag = DAG(name=graph.name, strategy=strategy, session_folder=self.session_folder)
        dag.platform = "local"
        # operator_factory = OperatorFactory(graph.config["platform"] == "ray")
        
        # Step 1: Create MessageQueue instances for all edges
        edge_to_queue:Dict[str,MessageQueue] = {}
        for edge_name, edge in graph.edges.items():
            edge_to_queue[edge_name] = MessageQueue(name = edge_name, session_folder=self.session_folder)


        # Step 2: Create all DAG nodes first
        dag_nodes:Dict[str, LocalDAGNode] = {}
        for node_name, graph_node in graph.nodes.items():
            # Create operator instance
            # operator = operator_factory.create(graph_node.operator, graph_node.config)
            graph_node.config["session_folder"] = self.session_folder
            operator_instance = graph_node.operator(graph_node.config)
            # Create DAG node
            dag_node = LocalDAGNode(
                graph_node.name,
                operator_instance,
                config=graph_node.config,
                is_spout=(graph_node.type == "source"), 
                session_folder=self.session_folder
            )
            dag_nodes[node_name] = dag_node
            dag.add_node(dag_node)

        # Step 3: Connect nodes through message queues
        for node_name, graph_node in graph.nodes.items():
            current_dag_node = dag_nodes[node_name]
            
            # Add downstream channels for output edges
            for output_edge in graph_node.output_channels:
                # Add downstream channel and connect to message queue
                output_queue = edge_to_queue[output_edge.name]
                current_dag_node.add_downstream_channel(output_queue)
            
            # Add upstream channels for input edges  
            for input_edge in graph_node.input_channels:
                input_queue = edge_to_queue[input_edge.name]
                current_dag_node.upstream_channels.append(input_queue)
        
        return dag

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

        query = None
        if config.get("query"):
            query = config.get("query")
        
        # if is_long_running is None, we assume it is a oneshot pipeline
        if config.get("is_long_running",None) is None :
            dag = self.compile_oneshot_pipeline(pipeline,query) # execution type在里边
        elif not config.get("is_long_running", None):
            dag = self.compile_oneshot_pipeline(pipeline,query)
        elif config.get("is_long_running", None):
            dag,config_mapping,execution_type  = self.compile_streaming_pipeline(pipeline)

        # Optimize the DAG

        # TODO: Add the optimization logic
        optimized_dag = self.optimizer.optimize(dag)
        optimized_dag.node_mapping = {} # Mapping of node names to their configurations. Not used in this version.
        optimized_dag.working_config = config
        if(pipeline.use_ray == False):
            optimized_dag.platform = "local"
        else:
            optimized_dag.platform = "ray"
        return optimized_dag

    def compile_oneshot_pipeline(self, pipeline, query): # deprecated
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
            # print("query is None")
            # query = source_stream.operator.get_query()
            return self.compile_one_shot_defined_pipeline(pipeline)
        else:
            intent= self.parser.parse_query(natural_query=query)

            print(f"[QueryCompiler] intent: {intent}")

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
        dag.execution_type = "oneshot"
        return dag

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