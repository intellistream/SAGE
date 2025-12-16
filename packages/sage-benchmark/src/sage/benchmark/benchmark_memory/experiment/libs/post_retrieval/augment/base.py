"""Augment Action - 结果增强

使用场景: MemoryBank, MemoryOS

功能: 在检索结果中添加额外的上下文信息（如 persona, traits, summary 等）
"""

from typing import Any, Optional

from ..base import BasePostRetrievalAction, PostRetrievalInput, PostRetrievalOutput


class AugmentAction(BasePostRetrievalAction):
    """结果增强策略

    在检索结果前后添加额外的上下文信息，如：
    - persona: 用户个性化信息
    - traits: 用户特征
    - summary: 记忆摘要
    - metadata: 元数据信息
    """

    def _init_action(self) -> None:
        """初始化配置"""
        self.augment_type = self.config.get("augment_type", "persona")
        self.position = self.config.get("position", "before")  # before, after, both
        self.separator = self.config.get("separator", "\n\n---\n\n")

    def execute(
        self,
        input_data: PostRetrievalInput,
        service: Optional[Any] = None,
        llm: Optional[Any] = None,
        embedding: Optional[Any] = None,
    ) -> PostRetrievalOutput:
        """增强检索结果

        Args:
            input_data: 输入数据
            service: 记忆服务（用于获取 persona 等信息）

        Returns:
            PostRetrievalOutput: 增强后的结果
        """
        memory_data = input_data.data.get("memory_data", [])
        items = self._convert_to_items(memory_data)

        if not items:
            return PostRetrievalOutput(memory_items=items, metadata={"action": "augment"})

        # 获取增强内容
        augment_content = self._get_augment_content(input_data, service)

        if not augment_content:
            # 如果没有增强内容，返回原始结果
            return PostRetrievalOutput(
                memory_items=items,
                metadata={"action": "augment", "warning": "No augment content available"},
            )

        # 根据位置添加增强内容
        if self.position == "before":
            # 在第一个条目前添加
            if items:
                items[0].text = augment_content + self.separator + items[0].text
        elif self.position == "after":
            # 在最后一个条目后添加
            if items:
                items[-1].text = items[-1].text + self.separator + augment_content
        elif self.position == "both":
            # 前后都添加
            if items:
                items[0].text = augment_content + self.separator + items[0].text
                items[-1].text = items[-1].text + self.separator + augment_content

        return PostRetrievalOutput(
            memory_items=items,
            metadata={
                "action": "augment",
                "augment_type": self.augment_type,
                "position": self.position,
            },
        )

    def _get_augment_content(self, input_data: PostRetrievalInput, service: Optional[Any]) -> str:
        """获取增强内容

        Args:
            input_data: 输入数据
            service: 记忆服务

        Returns:
            增强内容文本
        """
        if self.augment_type == "persona":
            return self._get_persona(input_data, service)
        elif self.augment_type == "traits":
            return self._get_traits(input_data, service)
        elif self.augment_type == "summary":
            return self._get_summary(input_data, service)
        elif self.augment_type == "metadata":
            return self._get_metadata(input_data)
        else:
            return ""

    def _get_persona(self, input_data: PostRetrievalInput, service: Optional[Any]) -> str:
        """获取 persona 信息

        Args:
            input_data: 输入数据
            service: 记忆服务

        Returns:
            Persona 文本
        """
        if service is None:
            return ""

        try:
            # 调用服务获取 persona
            # TODO: 需要服务提供 get_persona 方法
            # persona = service.call_service(input_data.service_name, method="get_persona")
            # return persona
            return ""
        except Exception:  # noqa: BLE001
            return ""

    def _get_traits(self, input_data: PostRetrievalInput, service: Optional[Any]) -> str:
        """获取 traits 信息

        Args:
            input_data: 输入数据
            service: 记忆服务

        Returns:
            Traits 文本
        """
        if service is None:
            return ""

        try:
            # 调用服务获取 traits
            # TODO: 需要服务提供 get_traits 方法
            return ""
        except Exception:  # noqa: BLE001
            return ""

    def _get_summary(self, input_data: PostRetrievalInput, service: Optional[Any]) -> str:
        """获取记忆摘要

        Args:
            input_data: 输入数据
            service: 记忆服务

        Returns:
            摘要文本
        """
        if service is None:
            return ""

        try:
            # 调用服务获取摘要
            # TODO: 需要服务提供 get_summary 方法
            return ""
        except Exception:  # noqa: BLE001
            return ""

    def _get_metadata(self, input_data: PostRetrievalInput) -> str:
        """从 data 获取元数据信息

        Args:
            input_data: 输入数据

        Returns:
            元数据文本
        """
        metadata = input_data.data.get("metadata", {})
        if not metadata:
            return ""

        # 格式化元数据
        lines = ["=== Metadata ==="]
        for key, value in metadata.items():
            lines.append(f"{key}: {value}")

        return "\n".join(lines)
