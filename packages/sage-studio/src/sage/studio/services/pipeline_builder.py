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

from collections import defaultdict, deque

# 从 SAGE 公共 API 导入（参考 PACKAGE_ARCHITECTURE.md）
from sage.kernel.api import LocalEnvironment
from sage.kernel.api.base_environment import BaseEnvironment
from sage.libs.io.sink import (
    FileSink,
    MemWriteSink,
    RetriveSink,
    TerminalSink,
)
from sage.libs.io.source import (
    APISource,
    CSVFileSource,
    DatabaseSource,
    FileSource,
    JSONFileSource,
    KafkaSource,
    SocketSource,
    TextFileSource,
)

from ..models import VisualNode, VisualPipeline
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
        self._user_input = None  # Playground/Chat 模式的用户输入
        self._env_config = {}  # 缓存环境配置

    def build(self, pipeline: VisualPipeline, user_input: str = None) -> BaseEnvironment:
        """
        从 VisualPipeline 构建 SAGE Pipeline

        Args:
            pipeline: Studio 的可视化 Pipeline 模型
            user_input: Playground/Chat 模式的用户输入 (可选)

        Returns:
            配置好的 SAGE 执行环境

        Raises:
            ValueError: 如果 Pipeline 结构无效
        """
        # 🆕 加载环境变量
        self._load_environment_variables()

        # 🆕 保存用户输入
        self._user_input = user_input

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
                stream = env.from_source(
                    source_class, *source_args, name=node.label, **source_kwargs
                )
            else:
                # 🆕 增强配置
                enhanced_config = self._enhance_operator_config(operator_class, node.config)

                # 后续节点 - 添加 transformation
                stream = stream.map(operator_class, config=enhanced_config, name=node.label)

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
            # Source 和 Sink 节点在 Registry 中有注册，但类型不同于 MapOperator
            # 它们会在 build() 中被特殊处理，所以这里只检查是否存在
            if self.registry.get_operator(node.type) is None:
                # 提供更友好的错误信息
                available_types = self.registry.list_types()
                error_msg = (
                    f"Unknown node type: '{node.type}'. \n"
                    f"Available types ({len(available_types)}): {available_types[:10]}... \n"
                    f"Hint: Node type should be in snake_case (e.g., 'terminal_sink', not 'TerminalSink')"
                )
                raise ValueError(error_msg)

        # 检查连接是否有效
        node_ids = {node.id for node in pipeline.nodes}
        for conn in pipeline.connections:
            if conn.source_node_id not in node_ids:
                raise ValueError(f"Connection source not found: {conn.source_node_id}")
            if conn.target_node_id not in node_ids:
                raise ValueError(f"Connection target not found: {conn.target_node_id}")

    def _topological_sort(self, pipeline: VisualPipeline) -> list[VisualNode]:
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
                f"Circular dependency detected in pipeline. Nodes in cycle: {remaining}"
            )

        return sorted_nodes

    def _load_environment_variables(self) -> None:
        """
        从 ~/.sage/.env.json 加载环境变量

        支持的变量:
        - DASHSCOPE_API_KEY: 阿里云 DashScope API
        - OPENAI_API_KEY: OpenAI API
        - 其他自定义环境变量
        """
        import json
        import os
        from pathlib import Path

        env_file = Path.home() / ".sage" / ".env.json"
        if env_file.exists():
            try:
                with open(env_file) as f:
                    env_vars = json.load(f)
                    self._env_config = env_vars  # 缓存配置
                    for key, value in env_vars.items():
                        os.environ[key] = value
                print(f"✅ 已加载环境变量: {', '.join(env_vars.keys())}")
            except Exception as e:
                print(f"⚠️ 加载环境变量失败: {e}")
        else:
            print(f"ℹ️ 环境变量文件不存在: {env_file}")

    def _load_env_from_config(self) -> dict:
        """从缓存的配置中读取环境变量"""
        return self._env_config

    def _enhance_operator_config(self, operator_class, config: dict) -> dict:
        """
        增强 operator 配置

        功能:
        1. OpenAIGenerator: 智能 Qwen/GPT API key 选择
        2. ChromaRetriever: 默认 ChromaDB 路径和参数
        3. 其他: 保持原配置
        """
        import os
        from pathlib import Path

        enhanced = config.copy()
        operator_name = operator_class.__name__

        # OpenAIGenerator: 智能 API key 配置
        if operator_name == "OpenAIGenerator":
            model = config.get("model", config.get("model_name", ""))

            # 确保 model_name 字段存在
            if "model_name" not in enhanced and model:
                enhanced["model_name"] = model

            # 确保总是有 api_key 字段（即使为 None）
            if "api_key" not in enhanced:
                # Qwen 模型 → DashScope
                if "qwen" in model.lower():
                    api_key = os.environ.get(
                        "DASHSCOPE_API_KEY"
                    ) or self._load_env_from_config().get("DASHSCOPE_API_KEY")
                    if api_key:
                        enhanced["api_key"] = api_key
                        if "base_url" not in enhanced:
                            enhanced["base_url"] = (
                                "https://dashscope.aliyuncs.com/compatible-mode/v1"
                            )
                        print(f"  ✓ Qwen 模型 '{model}' → DashScope API")
                    else:
                        enhanced["api_key"] = None
                        print("  ⚠️ 缺少 DASHSCOPE_API_KEY")

                # GPT 模型 → OpenAI
                elif "gpt" in model.lower():
                    api_key = os.environ.get("OPENAI_API_KEY")
                    if api_key:
                        enhanced["api_key"] = api_key
                        if "base_url" not in enhanced:
                            enhanced["base_url"] = "https://api.openai.com/v1"
                        print(f"  ✓ GPT 模型 '{model}' → OpenAI API")
                    else:
                        enhanced["api_key"] = None
                        print("  ⚠️ 缺少 OPENAI_API_KEY")

                # 其他模型：尝试从环境变量或配置文件获取
                else:
                    enhanced["api_key"] = (
                        os.environ.get("OPENAI_API_KEY")
                        or os.environ.get("DASHSCOPE_API_KEY")
                        or self._load_env_from_config().get("DASHSCOPE_API_KEY")
                        or None
                    )

            # 确保 base_url 字段存在（如果还没有）
            if "base_url" not in enhanced:
                # 根据模型推断 base_url
                if "qwen" in model.lower():
                    enhanced["base_url"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
                else:
                    enhanced["base_url"] = "https://api.openai.com/v1"

        # ChromaRetriever: 默认 ChromaDB 配置
        elif operator_name == "ChromaRetriever":
            if "persist_directory" not in enhanced:
                chroma_path = Path.home() / ".sage" / "vector_db"
                enhanced["persist_directory"] = str(chroma_path)

            if "collection_name" not in enhanced:
                enhanced["collection_name"] = "sage_docs"

            if "top_k" not in enhanced:
                enhanced["top_k"] = 5

            print(f"  ✓ ChromaRetriever: {enhanced['collection_name']} (top_k={enhanced['top_k']})")

        return enhanced

    def _get_operator_class(self, node_type: str):
        """获取节点类型对应的 Operator 类"""
        operator_class = self.registry.get_operator(node_type)
        if not operator_class:
            raise ValueError(
                f"Unknown node type: {node_type}. Available types: {self.registry.list_types()}"
            )
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
        from sage.common.core import SourceFunction

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

            # 🆕 优先使用外部输入
            if hasattr(self, "_user_input") and self._user_input:
                initial_data = [{"input": self._user_input}]
                print(f"  ✓ 使用输入: {self._user_input[:50]}...")
            else:
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
        # 🆕 Playground/Chat 模式默认使用 retrieve 收集结果
        sink_type = getattr(pipeline, "sink_type", "retrieve")

        if sink_type == "terminal":
            return TerminalSink
        elif sink_type == "file":
            return FileSink
        elif sink_type == "memory":
            return MemWriteSink
        elif sink_type == "retrieve":
            return RetriveSink
        else:
            # 默认使用 RetriveSink (Playground/Chat 模式)
            return RetriveSink


# 全局 Builder 实例
_default_builder = None


def get_pipeline_builder() -> PipelineBuilder:
    """获取全局 PipelineBuilder 实例"""
    global _default_builder
    if _default_builder is None:
        _default_builder = PipelineBuilder()
    return _default_builder
