
from __future__ import annotations
import os
from typing import TYPE_CHECKING
from typing import Dict, List, Set, Union
from sage.core.api.base_environment import BaseEnvironment
from sage.core.transformation.base_transformation import BaseTransformation
from sage.utils.custom_logger import CustomLogger
from sage.jobmanager.utils.name_server import get_name
from sage.runtime.runtime_context import RuntimeContext
if TYPE_CHECKING:
    from sage.jobmanager.job_manager import JobManager
    from ray.actor import ActorHandle


class GraphNode:
    def __init__(self, name: str, transformation: BaseTransformation, parallel_index: int, env:BaseEnvironment):
        self.name: str = name
        self.transformation: BaseTransformation = transformation
        self.parallel_index: int = parallel_index  # 在该transformation中的并行索引
        self.parallelism: int = transformation.parallelism
        self.is_spout: bool = transformation.is_spout
        self.is_sink: bool = transformation.is_sink
        self.input_channels:dict[int, List[GraphEdge]] = {}
        self.output_channels:List[List[GraphEdge]] = []

        self.stop_signal_num: int = 0  # 预期的源节点数量
        self.ctx: RuntimeContext = None


class GraphEdge:
    def __init__(self,name:str,  output_node: GraphNode,  input_node:GraphNode = None, input_index:int = 0):
        """
        Initialize a compiler edge with a source and target node.
        Args:
            source (str): The name of the source node.
            target (str): The name of the target node.
        """
        self.name: str = name
        self.upstream_node:GraphNode = output_node
        self.downstream_node:GraphNode = input_node
        self.input_index:int = input_index

class ExecutionGraph:
    def __init__(self, env:BaseEnvironment, jobmanager_handle:Union['JobManager', 'ActorHandle']):
        self.env = env
        self.nodes:Dict[str, GraphNode] = {}
        self.edges:Dict[str, GraphEdge] = {}
        # 构建数据流之间的连接映射

        # self.log_base_dir = env.log_base_dir
        # self.env_base_dir = env.env_base_dir
        self.setup_logging_system()
        # 构建基础图结构
        self._build_graph_from_pipeline(env)
        self._calculate_source_dependencies()
        self.generate_runtime_contexts(jobmanager_handle)
        self.total_stop_signals = self.calculate_total_stop_signals()
        self.logger.info(f"Successfully converted and optimized pipeline '{env.name}' to compiler with {len(self.nodes)} nodes and {len(self.edges)} edges")


    def calculate_total_stop_signals(self):
        """计算所有源节点的停止信号总数"""
        total_signals = 0
        for node in self.nodes.values():
            if node.is_sink:
                total_signals += node.stop_signal_num
        return total_signals

    def setup_logging_system(self): 
        self.logger = CustomLogger([
                ("console", self.env.console_log_level),  # 使用环境设置的控制台日志等级
                (os.path.join(self.env.env_base_dir, "ExecutionGraph.log"), "DEBUG"),  # 详细日志
                (os.path.join(self.env.env_base_dir, "Error.log"), "ERROR")  # 错误日志
            ],
            name = f"ExecutionGraph_{self.env.name}",
        )


    def generate_runtime_contexts(self, jobmanager_handle):
        """
        为每个节点生成运行时上下文
        """
        self.logger.debug("Generating runtime contexts for all nodes")
        for node_name, node in self.nodes.items():
            try:
                node.ctx = RuntimeContext(node, node.transformation, self.env, jobmanager_handle)
                self.logger.debug(f"Generated runtime context for node: {node_name}")
            except Exception as e:
                self.logger.error(f"Failed to generate runtime context for node {node_name}: {e}", exc_info=True)



    def _build_graph_from_pipeline(self, env: BaseEnvironment):
        """
        根据transformation pipeline构建图, 支持并行度和多对多连接
        分为三步: 1) 生成并行节点 2) 生成物理边 3) 创建图结构
        """
        transformation_to_node:Dict[BaseTransformation, List[str]] = {}  # transformation -> list of node names
        
        # 第一步：为每个transformation生成并行节点名字表，同时创建节点
        self.logger.debug("Step 1: Generating parallel nodes for each transformation")
        for transformation in env.pipeline:
            # 安全检查：如果发现未填充的future transformation，报错
            from sage.core.transformation.future_transformation import FutureTransformation
            if isinstance(transformation, FutureTransformation):
                if not transformation.filled:
                    raise RuntimeError(
                        f"Unfilled future transformation '{transformation.future_name}' in pipeline. "
                    )
                continue
            
            node_names = []
            for i in range(transformation.parallelism):
                try:
                    node_name = get_name(f"{transformation.basename}_{i}")
                    node_names.append(node_name)
                    self.nodes[node_name] = GraphNode(node_name,   transformation, i, env)
                    self.logger.debug(f"Created node: {node_name} (parallel index: {i})")
                except Exception as e:
                    self.logger.error(f"Error creating node {node_name}: {e}")
                    raise
            transformation_to_node[transformation.basename] = node_names
            self.logger.debug(f"Generated {len(node_names)} parallel nodes for {transformation.operator_class.__name__}: {node_names}")
        
        # 第三步：为每条逻辑边创建物理边并连接节点
        self.logger.debug("Step 2: Creating compiler structure")

        for transformation in env.pipeline:
            downstream_nodes = transformation_to_node[transformation.basename]
            for upstream_trans in transformation.upstreams:
                downstream_input_index = upstream_trans.downstreams[transformation.basename]
                upstream_nodes = transformation_to_node[upstream_trans.basename]
                
                # 找到downstream_transformation在upstream_transformation.downstream中的位置
                # downstream_idx = upstream_trans.downstream.index(transformation)
                # 创建m*n条物理边
                for i, upstream_node_name in enumerate(upstream_nodes):
                    upstream_node = self.nodes[upstream_node_name]
                    output_group_edges:List[GraphEdge] = []
                    for j, downstream_node_name in enumerate(downstream_nodes):
                        # 创建边名
                        edge_name = f"({upstream_node_name})->({downstream_node_name})[{downstream_input_index}]"
                        
                        # 获取节点对象
                        downstream_node = self.nodes[downstream_node_name]
                        if downstream_node.input_channels.get(downstream_input_index) is None:
                            downstream_node.input_channels[downstream_input_index] = []
                        
                        # 创建边对象并连接
                        edge = GraphEdge(
                            name=edge_name,
                            output_node=upstream_node,
                            input_node=downstream_node,
                            input_index = downstream_input_index
                        )
                        self.logger.debug(f"Creating edge: {edge_name} ")
                        # 将边添加到节点的channels中
                        #upstream_node.output_channels[upstream_output_channel].append(edge)
                        output_group_edges.append(edge)
                        downstream_node.input_channels[downstream_input_index].append(edge)
                        
                        # 将边添加到图中
                        self.edges[edge_name] = edge
                    upstream_node.output_channels.append(output_group_edges)



                    self.logger.debug(f"Connected {len(upstream_nodes)}×{len(downstream_nodes)} physical edges "
                                    f"between {upstream_trans.operator_class.__name__} -> "
                                    f"{transformation.operator_class.__name__}")
        
        self.logger.info(f"Graph construction completed: {len(self.nodes)} nodes, {len(self.edges)} edges")


    def _calculate_source_dependencies(self):
        """计算每个节点的源依赖关系"""
        self.logger.debug("Calculating source dependencies for all nodes")
        
        # 使用广度优先搜索计算每个节点依赖的源节点
        for node_name, node in self.nodes.items():
            if node.is_sink:
                # 非源节点通过BFS收集所有上游源依赖
                visited = set()
                queue = [node_name]
                source_deps = set()

                while queue:
                    current_name = queue.pop(0)
                    if current_name in visited:
                        continue
                    visited.add(current_name)
                    
                    current_node = self.nodes[current_name]
                    
                    if current_node.is_spout:
                        source_deps.add(current_node.transformation.basename)
                        node.stop_signal_num += 1
                    else:
                        # 添加所有上游节点到队列
                        for input_channel in current_node.input_channels.values():
                            for edge in input_channel:
                                if edge.upstream_node.name not in visited:
                                    queue.append(edge.upstream_node.name)
            
            self.logger.debug(f"Node {node_name} expects {node.stop_signal_num} source instances")