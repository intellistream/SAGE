"""EmbeddingAction - 查询向量化

使用记忆体：
- TiM: vector_hash_memory，使用embedding进行相似度检索
- MemoryBank: hierarchical_memory，使用embedding检索各层记忆
- A-Mem: graph_memory，使用embedding进行图检索
- MemoryOS: hierarchical_memory，使用embedding检索层级记忆
- HippoRAG2: graph_memory，使用embedding进行图检索
- SeCom: neuromem_vdb，使用embedding检索语义记忆

特点：
- 将查询文本转换为向量表示
- 支持外部embedding服务（通过EmbeddingGenerator）
- 不修改原始查询文本
"""

from typing import Optional

from ..base import BasePreRetrievalAction, PreRetrievalInput, PreRetrievalOutput


class EmbeddingAction(BasePreRetrievalAction):
    """查询向量化Action

    使用EmbeddingGenerator生成查询的向量表示。
    """

    def _init_action(self) -> None:
        """初始化embedding生成器

        从config中获取runtime配置，创建EmbeddingGenerator。
        注意：这里不直接创建generator，而是在execute时使用外部传入的。
        """
        # EmbeddingGenerator将由PreRetrieval主类统一管理
        # 这里只存储配置
        self.embedding_dim: Optional[int] = self.config.get("embedding_dim")

    def execute(self, input_data: PreRetrievalInput) -> PreRetrievalOutput:
        """生成查询向量

        Args:
            input_data: 输入数据

        Returns:
            包含查询向量的输出数据

        Note:
            实际的embedding生成由PreRetrieval主类完成，
            这里主要是标记需要生成embedding。
        """
        question = input_data.question

        # 返回查询，embedding将由外部统一生成
        return PreRetrievalOutput(
            query=question,
            query_embedding=None,  # 由PreRetrieval主类统一生成
            metadata={
                "original_query": question,
                "needs_embedding": True,  # 标记需要生成embedding
            },
            retrieve_mode="passive",
        )
