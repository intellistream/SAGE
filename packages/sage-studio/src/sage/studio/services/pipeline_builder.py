"""
Pipeline Builder - 将 Studio 可视化模型转换为 SAGE Pipeline

职责：
1. 解析 VisualPipeline 的节点和连接
2. 拓扑排序节点以确定执行顺序
3. 将每个节点映射到对应的 SAGE Operator
4. 使用 SAGE DataStream API 构建 Pipeline
5. 返回可执行的 Environment

不负责：
- 执行 Pipeline（由 SAGE Engine 完成）
- UI 交互逻辑
- 状态管理（由 SAGE Engine 完成）
"""

from typing import Any, Dict, List, Optional, Set
from collections import defaultdict, deque

# 从 SAGE 公共 API 导入（参考 PACKAGE_ARCHITECTURE.md）
from sage.kernel.api import LocalEnvironment
from sage.kernel.api.base_environment import BaseEnvironment
from sage.libs.io.source import (
    FileSource, JSONFileSource, CSVFileSource, TextFileSource,
    SocketSource, KafkaSource, DatabaseSource, APISource
)
from sage.libs.io.sink import (
    TerminalSink, PrintSink, FileSink, MemWriteSink, RetriveSink
)

from ..models import VisualPipeline, VisualNode, VisualConnection
from .node_registry import get_node_registry


class PipelineBuilder:
    """
    将 Studio 的可视化 Pipeline 转换为 SAGE 可执行 Pipeline

    Usage:
        builder = PipelineBuilder()
        env = builder.build(visual_pipeline)
        job = env.execute()
    """

    def __init__(self):
        # 使用全局节点注册表
        self.registry = get_node_registry()

    def build(self, pipeline: VisualPipeline) -> BaseEnvironment:
        """
        从 VisualPipeline 构建 SAGE Pipeline

        Args:
            pipeline: Studio 的可视化 Pipeline 模型

        Returns:
            配置好的 SAGE 执行环境

        Raises:
            ValueError: 如果 Pipeline 结构无效
        """
        # 1. 验证 Pipeline
        self._validate_pipeline(pipeline)

        # 2. 拓扑排序节点
        sorted_nodes = self._topological_sort(pipeline)

        # 3. 创建执行环境
        env = LocalEnvironment()

        # 4. 构建 DataStream Pipeline
        stream = None
        node_outputs = {}  # 记录每个节点的输出 stream

        for node in sorted_nodes:
            operator_class = self._get_operator_class(node.type)

            if stream is None:
                # 第一个节点 - 创建 source
                source_class, source_args, source_kwargs = self._create_source(node, pipeline)
                stream = env.from_source(source_class, *source_args, name=node.label, **source_kwargs)
            else:
                # 后续节点 - 添加 transformation
                stream = stream.map(
                    operator_class,
                    config=node.config,
                    name=node.label
                )

            node_outputs[node.id] = stream

        # 5. 添加 sink
        if stream:
            stream.sink(self._create_sink(pipeline))

        return env

    def _validate_pipeline(self, pipeline: VisualPipeline):
        """验证 Pipeline 结构的有效性"""
        if not pipeline.nodes:
            raise ValueError("Pipeline must contain at least one node")

        # 检查所有节点类型是否已注册
        for node in pipeline.nodes:
            if self.registry.get_operator(node.type) is None:
                raise ValueError(
                    f"Unknown node type: {node.type}. "
                    f"Available types: {self.registry.list_types()}"
                )

        # 检查连接是否有效
        node_ids = {node.id for node in pipeline.nodes}
        for conn in pipeline.connections:
            if conn.source_node_id not in node_ids:
                raise ValueError(f"Connection source not found: {conn.source_node_id}")
            if conn.target_node_id not in node_ids:
                raise ValueError(f"Connection target not found: {conn.target_node_id}")

    def _topological_sort(self, pipeline: VisualPipeline) -> List[VisualNode]:
        """
        对节点进行拓扑排序

        Returns:
            排序后的节点列表

        Raises:
            ValueError: 如果存在循环依赖
        """
        # 构建依赖图
        in_degree = defaultdict(int)
        adjacency = defaultdict(list)
        node_map = {node.id: node for node in pipeline.nodes}

        # 初始化入度
        for node in pipeline.nodes:
            in_degree[node.id] = 0

        # 构建图
        for conn in pipeline.connections:
            adjacency[conn.source_node_id].append(conn.target_node_id)
            in_degree[conn.target_node_id] += 1

        # Kahn 算法
        queue = deque([node_id for node_id in in_degree if in_degree[node_id] == 0])
        sorted_nodes = []

        while queue:
            node_id = queue.popleft()
            sorted_nodes.append(node_map[node_id])

            for neighbor in adjacency[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # 检查是否存在循环
        if len(sorted_nodes) != len(pipeline.nodes):
            remaining = [n.label for n in pipeline.nodes if n not in sorted_nodes]
            raise ValueError(
                f"Circular dependency detected in pipeline. "
                f"Nodes in cycle: {remaining}"
            )

        return sorted_nodes

    def _get_operator_class(self, node_type: str):
        """获取节点类型对应的 Operator 类"""
        operator_class = self.registry.get_operator(node_type)
        if not operator_class:
            raise ValueError(f"Unknown node type: {node_type}. "
                           f"Available types: {self.registry.list_types()}")
        return operator_class

    def _create_source(self, node: VisualNode, pipeline: VisualPipeline):
        """
        根据节点类型和配置创建合适的数据源

        Returns:
            tuple: (source_class, args, kwargs)

        支持的源类型：
        - file: FileSource (文件路径)
        - json_file: JSONFileSource (JSON 文件)
        - csv_file: CSVFileSource (CSV 文件)
        - text_file: TextFileSource (文本文件)
        - socket: SocketSource (网络 socket)
        - kafka: KafkaSource (Kafka topic)
        - database: DatabaseSource (数据库查询)
        - api: APISource (HTTP API)
        - memory/data: 内存数据源（用于测试）
        """
        from sage.kernel.api.function.source_function import SourceFunction

        source_type = node.config.get("source_type", "memory")

        # 文件源
        if source_type == "file":
            file_path = node.config.get("file_path", node.config.get("path"))
            return FileSource, (file_path,), {}

        elif source_type == "json_file":
            file_path = node.config.get("file_path", node.config.get("path"))
            return JSONFileSource, (file_path,), {}

        elif source_type == "csv_file":
            file_path = node.config.get("file_path", node.config.get("path"))
            delimiter = node.config.get("delimiter", ",")
            return CSVFileSource, (file_path, delimiter), {}

        elif source_type == "text_file":
            file_path = node.config.get("file_path", node.config.get("path"))
            return TextFileSource, (file_path,), {}

        # 网络源
        elif source_type == "socket":
            host = node.config.get("host", "localhost")
            port = node.config.get("port", 9999)
            return SocketSource, (host, port), {}

        elif source_type == "kafka":
            topic = node.config.get("topic")
            bootstrap_servers = node.config.get("bootstrap_servers", "localhost:9092")
            return KafkaSource, (topic, bootstrap_servers), {}

        # 数据库源
        elif source_type == "database":
            query = node.config.get("query")
            connection_string = node.config.get("connection_string")
            return DatabaseSource, (query, connection_string), {}

        # API 源
        elif source_type == "api":
            url = node.config.get("url")
            method = node.config.get("method", "GET")
            return APISource, (url, method), {}

        # 内存数据源（默认，用于测试）
        else:
            class SimpleListSource(SourceFunction):
                """Simple in-memory list source for testing and development"""
                def __init__(self, data):
                    super().__init__()
                    self.data = data if isinstance(data, list) else [data]

                def execute(self, data=None):
                    """Execute the source function"""
                    return self.data

            initial_data = node.config.get("data", [{"input": "test data"}])
            return SimpleListSource, (initial_data,), {}

    def _create_sink(self, pipeline: VisualPipeline):
        """
        根据 Pipeline 配置创建合适的数据接收器

        Returns:
            Type: Sink class (not instance)

        支持的接收器类型：
        - terminal: TerminalSink (终端输出，带颜色)
        - print: PrintSink (简单打印)
        - file: FileSink (文件输出)
        - memory: MemWriteSink (内存写入，用于测试)
        - retrieve: RetriveSink (收集结果)
        """

        # 从 pipeline 的 execution_mode 或其他配置中获取 sink 类型
        # 注意：VisualPipeline 可能没有直接的 sink 配置，这里使用默认值
        sink_type = getattr(pipeline, "sink_type", "print")

        if sink_type == "terminal":
            return TerminalSink
        elif sink_type == "file":
            return FileSink
        elif sink_type == "memory":
            return MemWriteSink
        elif sink_type == "retrieve":
            return RetriveSink
        else:
            # 默认使用 PrintSink
            return PrintSink


# 全局 Builder 实例
_default_builder = None


def get_pipeline_builder() -> PipelineBuilder:
    """获取全局 PipelineBuilder 实例"""
    global _default_builder
    if _default_builder is None:
        _default_builder = PipelineBuilder()
    return _default_builder
