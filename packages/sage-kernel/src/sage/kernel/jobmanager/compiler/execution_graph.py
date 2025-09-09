"""
ExecutionGraph - 执行图类

ExecutionGraph管理整个图的构建和运行时上下文，包含：
- 图节点和服务节点的管理
- 队列描述符的创建和分发
- 运行时上下文的生成
- 图结构的构建
"""

from __future__ import annotations
import os
from typing import TYPE_CHECKING, Dict, List, Union

from sage.core.api.base_environment import BaseEnvironment
from sage.core.transformation.base_transformation import BaseTransformation
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.jobmanager.utils.name_server import get_name
from sage.kernel.runtime.context.task_context import TaskContext
from .graph_node import TaskNode
from .graph_edge import GraphEdge


class ExecutionGraph:
    """
    执行图类

    负责管理整个执行图的构建、队列描述符创建和运行时上下文生成
    """

    def __init__(self, env: BaseEnvironment):
        self.env = env
        self.nodes: Dict[str, TaskNode] = {}
        self.edges: Dict[str, GraphEdge] = {}

        # 首先设置日志系统
        self._setup_logging_system()

        # 构建基础图结构
        self._build_task_nodes(env)

        # 生成运行时上下文（队列描述符和连接关系都在Context构造函数中处理）
        self._generate_runtime_contexts()

        # 停止信号相关
        self._calculate_source_dependencies()
        self.total_stop_signals = self._calculate_total_stop_signals()

        self.logger.info(
            f"Successfully converted and optimized pipeline '{env.name}' to compiler with "
            f"{len(self.nodes)} transformation nodes,  "
            f"and {len(self.edges)} edges"
        )

    def _calculate_total_stop_signals(self):
        """计算所有源节点的停止信号总数"""
        total_signals = 0
        for node in self.nodes.values():
            if node.is_sink:
                total_signals += node.stop_signal_num
        return total_signals

    def _setup_logging_system(self):
        """设置日志系统，支持模拟环境"""
        try:
            # 获取控制台日志级别，如果不存在则使用默认值
            console_log_level = getattr(self.env, "console_log_level", "INFO")

            # 获取环境基础目录，如果不存在则使用临时目录
            env_base_dir = getattr(self.env, "env_base_dir", "/tmp")

            # 获取环境名称，如果不存在则使用默认名称
            env_name = getattr(self.env, "name", "unknown_env")

            self.logger = CustomLogger(
                [
                    ("console", console_log_level),  # 使用环境设置的控制台日志等级
                    (
                        os.path.join(env_base_dir, "ExecutionGraph.log"),
                        "DEBUG",
                    ),  # 详细日志
                    (os.path.join(env_base_dir, "Error.log"), "ERROR"),  # 错误日志
                ],
                name=f"ExecutionGraph_{env_name}",
            )
        except Exception as e:
            # 如果设置日志系统失败，创建一个基础的日志器
            self.logger = CustomLogger([("console", "INFO")], name="ExecutionGraph_fallback")

    def _generate_runtime_contexts(self):
        """
        为每个节点生成运行时上下文
        队列描述符和连接关系都在Context构造函数中处理，这里只需创建Context即可
        """
        self.logger.debug("Generating runtime contexts for all nodes")

        # 为流水线节点创建运行时上下文
        for node_name, node in self.nodes.items():
            try:
                # 创建TaskContext，所有队列描述符和连接关系都在构造函数中处理
                node.ctx = TaskContext(node, node.transformation, self.env, execution_graph=self)

                input_queues_info = "1 input queue" if node.input_qd else "no input queue (spout)"
                self.logger.debug(
                    f"Generated runtime context with {input_queues_info} for transformation node: {node_name}"
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to generate runtime context for node {node_name}: {e}",
                    exc_info=True,
                )

        self.logger.info(f"Runtime context generation completed: {len(self.nodes)} graph nodes,  ")

    def _build_task_nodes(self, env: BaseEnvironment):
        """
        根据transformation pipeline构建图, 支持并行度和多对多连接
        分为三步: 1) 生成并行节点 2) 生成物理边 3) 创建图结构
        """
        transformation_to_node: Dict[BaseTransformation, List[str]] = {}  # transformation -> list of node names

        # 第一步：为每个transformation生成并行节点名字表，同时创建节点
        self.logger.debug("Step 1: Generating parallel nodes for each transformation")
        for transformation in env.pipeline:
                
            node_names = []
            for i in range(transformation.parallelism):
                node_name = get_name(f"{transformation.basename}_{i}")
                node_names.append(node_name)
                self.nodes[node_name] = TaskNode(node_name, transformation, i, env)
                self.logger.debug(f"Created node: {node_name} (parallel index: {i})")

            transformation_to_node[transformation.basename] = node_names
            self.logger.debug(
                f"Generated {len(node_names)} parallel nodes for {transformation.operator_class.__name__}: {node_names}"
            )

        # 第二步：为每条逻辑边创建物理边并连接节点
        self.logger.debug("Step 2: Creating compiler structure")

        for transformation in env.pipeline:

            downstream_nodes = transformation_to_node[transformation.basename]
            for upstream_trans in transformation.upstreams:
                actual_upstream_trans = upstream_trans

                downstream_input_index = upstream_trans.downstreams[transformation.basename]
                upstream_nodes = transformation_to_node[actual_upstream_trans.basename]

                # 创建m*n条物理边
                for i, upstream_node_name in enumerate(upstream_nodes):
                    upstream_node = self.nodes[upstream_node_name]
                    output_group_edges: List[GraphEdge] = []
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
                            input_index=downstream_input_index,
                        )
                        self.logger.debug(f"Creating edge: {edge_name} ")

                        # 将边添加到节点的channels中
                        output_group_edges.append(edge)
                        downstream_node.input_channels[downstream_input_index].append(edge)

                        # 将边添加到图中
                        self.edges[edge_name] = edge
                    upstream_node.output_channels.append(output_group_edges)

                    self.logger.debug(
                        f"Connected {len(upstream_nodes)}×{len(downstream_nodes)} physical edges "
                        f"between {upstream_trans.operator_class.__name__} -> "
                        f"{transformation.operator_class.__name__}"
                    )

        self.logger.info(f"Graph construction completed: {len(self.nodes)} nodes, {len(self.edges)} edges")

    def _calculate_source_dependencies(self):
        """计算每个节点的源依赖关系"""
        self.logger.debug("Calculating source dependencies for all nodes")

        # 使用广度优先搜索计算每个节点依赖的源节点
        for node_name, node in self.nodes.items():
            if not node.is_spout:
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
            else:
                # 源节点不需要等待停止信号
                node.stop_signal_num = 0

            self.logger.debug(f"Node {node_name} expects {node.stop_signal_num} stop signals")
