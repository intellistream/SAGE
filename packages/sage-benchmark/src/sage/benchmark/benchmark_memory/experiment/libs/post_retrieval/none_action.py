"""None Action - 透传策略

使用场景: HippoRAG, HippoRAG2, Mem0, SeCom

功能: 不做任何处理，直接透传检索结果
"""

from typing import Any, Optional

from .base import BasePostRetrievalAction, PostRetrievalInput, PostRetrievalOutput


class NoneAction(BasePostRetrievalAction):
    """透传策略 - 不做任何处理"""

    def _init_action(self) -> None:
        """无需初始化"""
        pass

    def execute(
        self,
        input_data: PostRetrievalInput,
        service: Optional[Any] = None,
        llm: Optional[Any] = None,
        embedding: Optional[Any] = None,
    ) -> PostRetrievalOutput:
        """直接返回原始检索结果

        Args:
            input_data: 输入数据

        Returns:
            PostRetrievalOutput: 未修改的检索结果
        """
        memory_data = input_data.data.get("memory_data", [])
        items = self._convert_to_items(memory_data)

        return PostRetrievalOutput(memory_items=items, metadata={"action": "none"})
