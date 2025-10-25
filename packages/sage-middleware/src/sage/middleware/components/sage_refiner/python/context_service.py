"""
全局Context Service
==================

提供自动管理全流程上下文的服务，用户只需一个flag即可开关。
"""

import logging
from typing import Any

from sage.middleware.components.sage_refiner.python.service import RefinerService


class ContextService:
    """
    全局上下文服务

    自动管理应用全流程的上下文，包括：
    - 历史对话压缩
    - 检索文档压缩
    - 上下文窗口管理
    - 自动压缩策略
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        初始化Context Service

        Args:
            config: 配置字典，包含:
                - refiner: RefinerService配置
                - max_context_length: 最大上下文长度
                - auto_compress: 是否自动压缩
                - compress_threshold: 压缩阈值
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # 创建Refiner服务
        refiner_config = self.config.get("refiner", {})
        self.refiner = RefinerService(refiner_config)

        # 上下文管理配置
        self.max_context_length = self.config.get("max_context_length", 8192)
        self.auto_compress = self.config.get("auto_compress", True)
        self.compress_threshold = self.config.get("compress_threshold", 0.8)

        # 上下文缓存
        self.context_history: list[dict[str, Any]] = []

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "ContextService":
        """从配置字典创建服务"""
        return cls(config)

    def manage_context(
        self,
        query: str,
        history: list[dict[str, str]] | None = None,
        retrieved_docs: list[str | dict[str, Any]] | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        管理上下文

        自动处理历史对话、检索文档的压缩和组合。

        Args:
            query: 当前查询
            history: 历史对话 [{"role": "user/assistant", "content": "..."}]
            retrieved_docs: 检索到的文档
            system_prompt: 系统提示词
            **kwargs: 其他参数

        Returns:
            Dict包含:
                - compressed_context: 压缩后的上下文
                - context_length: 上下文长度
                - compression_applied: 是否应用了压缩
                - metrics: 压缩指标
        """
        self.logger.debug("Managing context...")

        context_parts = []
        total_length = 0
        compression_applied = False
        metrics = {}

        # 1. 系统提示词
        if system_prompt:
            context_parts.append({"type": "system", "content": system_prompt})
            total_length += len(system_prompt.split())

        # 2. 处理历史对话
        if history:
            history_text = self._format_history(history)
            history_length = len(history_text.split())

            # 检查是否需要压缩历史
            if (
                self.auto_compress
                and history_length > self.max_context_length * self.compress_threshold
            ):
                # 压缩历史
                compressed_history = self._compress_history(history)
                context_parts.append({"type": "history", "content": compressed_history["content"]})
                total_length += compressed_history["length"]
                compression_applied = True
                metrics["history_compression"] = compressed_history["metrics"]
            else:
                context_parts.append({"type": "history", "content": history_text})
                total_length += history_length

        # 3. 处理检索文档
        if retrieved_docs:
            docs_budget = max(self.max_context_length - total_length, self.max_context_length // 2)

            if docs_budget > 0:
                refine_result = self.refiner.refine(
                    query=query, documents=retrieved_docs, budget=docs_budget
                )

                # 格式化精炼后的文档
                if isinstance(refine_result.refined_content, list):
                    docs_text = "\n\n".join(refine_result.refined_content)
                else:
                    docs_text = refine_result.refined_content

                context_parts.append({"type": "documents", "content": docs_text})
                total_length += refine_result.metrics.refined_tokens
                compression_applied = True
                metrics["docs_compression"] = refine_result.metrics.to_dict()

        # 4. 添加当前查询
        context_parts.append({"type": "query", "content": query})
        total_length += len(query.split())

        return {
            "compressed_context": context_parts,
            "context_length": total_length,
            "compression_applied": compression_applied,
            "metrics": metrics,
        }

    def _format_history(self, history: list[dict[str, str]]) -> str:
        """格式化历史对话"""
        formatted = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)

    def _compress_history(self, history: list[dict[str, str]]) -> dict[str, Any]:
        """压缩历史对话"""
        # 简单策略：只保留最近的N轮对话
        # 未来可以使用更智能的压缩方法
        max_turns = 5
        recent_history = history[-max_turns * 2 :]  # 每轮2条（user+assistant）

        formatted = self._format_history(recent_history)
        return {
            "content": formatted,
            "length": len(formatted.split()),
            "metrics": {
                "original_turns": len(history),
                "kept_turns": len(recent_history) // 2,
            },
        }

    def add_to_history(self, role: str, content: str) -> None:
        """添加到历史记录"""
        self.context_history.append({"role": role, "content": content})

    def clear_history(self) -> None:
        """清空历史"""
        self.context_history.clear()

    def get_stats(self) -> dict[str, Any]:
        """获取服务统计"""
        return {
            "refiner_stats": self.refiner.get_stats(),
            "context_history_size": len(self.context_history),
            "max_context_length": self.max_context_length,
            "auto_compress": self.auto_compress,
        }

    def shutdown(self) -> None:
        """关闭服务"""
        self.refiner.shutdown()
        self.context_history.clear()

    def __enter__(self):
        """上下文管理器"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器"""
        self.shutdown()
