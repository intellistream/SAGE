"""Link Expand Merge - 链接扩展合并

使用场景: A-Mem, Mem0ᵍ

功能: 通过图的链接关系扩展检索结果（邻居节点）
"""

from typing import Any, Optional

from ..base import BasePostRetrievalAction, MemoryItem, PostRetrievalInput, PostRetrievalOutput


class LinkExpandMergeAction(BasePostRetrievalAction):
    """链接扩展合并策略

    通过记忆服务的图结构，扩展检索到的记忆的邻居节点。
    """

    def _init_action(self) -> None:
        """初始化配置"""
        self.expand_depth = self.config.get("expand_depth", 1)
        self.max_neighbors = self.config.get("max_neighbors", 5)
        self.edge_types = self.config.get("edge_types", ["semantic", "temporal"])

    def execute(
        self,
        input_data: PostRetrievalInput,
        service: Optional[Any] = None,
        llm: Optional[Any] = None,
        embedding: Optional[Any] = None,
    ) -> PostRetrievalOutput:
        """通过链接扩展合并结果

        Args:
            input_data: 输入数据
            service: 记忆服务（需要提供 expand_neighbors 方法）

        Returns:
            PostRetrievalOutput: 扩展后的结果
        """
        memory_data = input_data.data.get("memory_data", [])
        items = self._convert_to_items(memory_data)

        if not items or service is None:
            return PostRetrievalOutput(
                memory_items=items,
                metadata={
                    "action": "merge.link_expand",
                    "warning": "No service available or empty items",
                },
            )

        # 提取节点 ID
        node_ids = []
        for item in items:
            node_id = item.metadata.get("node_id") or item.metadata.get("id")
            if node_id:
                node_ids.append(node_id)

        if not node_ids:
            # 如果没有节点 ID，无法扩展
            return PostRetrievalOutput(
                memory_items=items,
                metadata={"action": "merge.link_expand", "warning": "No node IDs found"},
            )

        # 调用服务扩展邻居
        try:
            expanded_results = self._call_service_expand(service, input_data.service_name, node_ids)

            # 合并原始结果和扩展结果
            merged_items = self._merge_results(items, expanded_results)

            return PostRetrievalOutput(
                memory_items=merged_items,
                metadata={
                    "action": "merge.link_expand",
                    "original_count": len(items),
                    "expanded_count": len(expanded_results),
                    "total_count": len(merged_items),
                },
            )
        except Exception as e:  # noqa: BLE001
            # 如果扩展失败，返回原始结果
            return PostRetrievalOutput(
                memory_items=items,
                metadata={"action": "merge.link_expand", "error": str(e)},
            )

    def _call_service_expand(
        self, service: Any, service_name: str, node_ids: list[str]
    ) -> list[dict[str, Any]]:
        """调用服务扩展邻居节点

        Args:
            service: 服务实例
            service_name: 服务名称
            node_ids: 节点 ID 列表

        Returns:
            扩展的记忆列表
        """
        # TODO: 需要服务提供 expand_neighbors 方法
        # 示例: service.call_service(service_name, method="expand_neighbors", ...)
        #
        # 当前简化为返回空列表（需要服务端支持）
        return []

    def _merge_results(
        self, original: list[MemoryItem], expanded: list[dict[str, Any]]
    ) -> list[MemoryItem]:
        """合并原始结果和扩展结果

        Args:
            original: 原始 MemoryItem 列表
            expanded: 扩展的字典列表

        Returns:
            合并后的 MemoryItem 列表
        """
        # 去重（基于 node_id）
        seen_ids = set()
        merged = []

        # 先添加原始结果
        for item in original:
            node_id = item.metadata.get("node_id") or item.metadata.get("id")
            if node_id:
                seen_ids.add(node_id)
            merged.append(item)

        # 再添加扩展结果（避免重复）
        for idx, exp in enumerate(expanded):
            node_id = exp.get("metadata", {}).get("node_id") or exp.get("metadata", {}).get("id")
            if node_id and node_id in seen_ids:
                continue

            # 转换为 MemoryItem
            item = MemoryItem(
                text=exp.get("text", ""),
                score=exp.get("score"),
                metadata=exp.get("metadata", {}),
                original_index=len(original) + idx,
            )
            merged.append(item)

            if node_id:
                seen_ids.add(node_id)

        return merged
