"""NoneAction - 透传查询，不做任何处理

使用记忆体：
- Mem0: hybrid_memory，直接使用原始查询进行CRUD决策
- Mem0ᵍ: graph_memory，直接使用原始查询进行图检索

特点：
- 无需查询优化
- 保持原始查询文本
- 不生成embedding（由外部统一处理）
"""

from .base import BasePreRetrievalAction, PreRetrievalInput, PreRetrievalOutput


class NoneAction(BasePreRetrievalAction):
    """透传Action - 不做任何处理

    适用于不需要查询预处理的记忆体系统。
    """

    def _init_action(self) -> None:
        """无需初始化配置"""
        pass

    def execute(self, input_data: PreRetrievalInput) -> PreRetrievalOutput:
        """直接返回原始查询

        Args:
            input_data: 输入数据

        Returns:
            包含原始查询的输出数据
        """
        question = input_data.question

        return PreRetrievalOutput(
            query=question,
            query_embedding=None,  # 不生成embedding
            metadata={"original_query": question},
            retrieve_mode="passive",
        )
