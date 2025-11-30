"""预检索处理模块 - 在记忆检索前的预处理（可选）

对于短期记忆（STM），通常不需要预处理，直接检索即可。
此模块保留用于未来扩展（如查询优化、权限验证等）。
"""

from sage.benchmark.benchmark_memory.experiment.utils.embedding_generator import (
    EmbeddingGenerator,
)
from sage.common.core import MapFunction


class PreRetrieval(MapFunction):
    """记忆检索前的预处理算子

    职责：
    - 查询优化
    - 权限验证
    - 参数调整
    - 查询 Embedding（用于向量检索）

    注：短期记忆通常不需要此步骤
    """

    def __init__(self, config):
        """初始化 PreRetrieval

        Args:
            config: RuntimeConfig 对象，从中获取 operators.pre_retrieval.action
        """
        super().__init__()
        self.action = config.get("operators.pre_retrieval.action", "none")
        self.config = config

        # 如果 action 是 embedding，初始化 Embedding 生成器
        if self.action == "embedding":
            self.embedding_generator = EmbeddingGenerator.from_config(config)

    def execute(self, data):
        """执行预处理

        Args:
            data: PipelineRequest 对象或原始检索请求，包含：
                - "question": 查询问题（字符串）
                - 其他检索参数

        Returns:
            处理后的数据：
            - action="none": 原样返回
            - action="embedding": 添加 "query_embedding" 字段
            - 其他: 原样返回
        """
        # 根据 action 模式执行不同操作
        if self.action == "none":
            # 不执行任何操作，直接透传
            return data
        elif self.action == "embedding":
            # 对 question 进行 Embedding
            return self._embed_question(data)
        elif self.action == "optimize":
            # TODO: 实现查询优化逻辑
            return data
        elif self.action == "validate":
            # TODO: 实现权限验证逻辑
            return data
        else:
            # 未知操作模式，透传
            return data

    def _embed_question(self, data):
        """对查询问题进行 Embedding

        Args:
            data: 检索请求数据，包含 "question" 字段

        Returns:
            添加了 "query_embedding" 字段的数据
        """

        question = data.get("question")

        # 生成 Embedding
        embedding = self.embedding_generator.embed(question)

        # 将 Embedding 添加到数据中
        data["query_embedding"] = embedding

        return data
