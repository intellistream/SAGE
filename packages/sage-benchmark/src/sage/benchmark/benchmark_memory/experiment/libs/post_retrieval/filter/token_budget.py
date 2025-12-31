"""Token Budget Filter - Token 预算过滤

使用场景: SCM

功能: 根据 token 预算限制截断检索结果
"""

from typing import Any, Optional

from ..base import BasePostRetrievalAction, PostRetrievalInput, PostRetrievalOutput


class TokenBudgetFilterAction(BasePostRetrievalAction):
    """Token 预算过滤策略

    根据 token 预算限制，从头开始累加直到达到预算上限。
    """

    def _init_action(self) -> None:
        """初始化配置"""
        self.max_tokens = self.config.get("max_tokens", 2000)
        self.encoding = self.config.get("encoding", "cl100k_base")  # OpenAI tokenizer
        self._init_tokenizer()

    def _init_tokenizer(self) -> None:
        """初始化 tokenizer"""
        try:
            import tiktoken

            self.tokenizer = tiktoken.get_encoding(self.encoding)
        except Exception:  # noqa: BLE001
            # 如果 tiktoken 不可用，使用简单估算（1 token ≈ 4 chars）
            self.tokenizer = None

    def execute(
        self,
        input_data: PostRetrievalInput,
        service: Any,
        llm: Optional[Any] = None,
    ) -> PostRetrievalOutput:
        """根据 token 预算过滤结果

        Args:
            input_data: 输入数据
            service: 记忆服务代理（未使用）
            llm: LLM 生成器（未使用）

        Returns:
            PostRetrievalOutput: 过滤后的结果
        """
        memory_data = input_data.data.get("memory_data", [])
        items = self._convert_to_items(memory_data)

        if not items:
            return PostRetrievalOutput(
                memory_items=items, metadata={"action": "filter.token_budget"}
            )

        # 按顺序累加 token 直到达到预算
        filtered_items = []
        total_tokens = 0

        for item in items:
            item_tokens = self._count_tokens(item.text)

            if total_tokens + item_tokens <= self.max_tokens:
                filtered_items.append(item)
                total_tokens += item_tokens
            else:
                # 达到预算上限，停止添加
                break

        return PostRetrievalOutput(
            memory_items=filtered_items,
            metadata={
                "action": "filter.token_budget",
                "max_tokens": self.max_tokens,
                "used_tokens": total_tokens,
                "original_count": len(items),
                "filtered_count": len(filtered_items),
            },
        )

    def _count_tokens(self, text: str) -> int:
        """计算文本的 token 数量

        Args:
            text: 输入文本

        Returns:
            token 数量
        """
        if self.tokenizer is not None:
            return len(self.tokenizer.encode(text))
        else:
            # 简单估算：1 token ≈ 4 chars
            return len(text) // 4
