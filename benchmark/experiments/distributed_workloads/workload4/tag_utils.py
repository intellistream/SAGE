"""
Tag-based Stream Splitting Utilities for Workload 4
====================================================

用于给流打 tag 并根据 tag 过滤的工具算子。

使用场景：
- 需要将一个流复制成多份，分别处理不同的逻辑
- 避免使用 join 等待配对，直接用 filter 分流
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.flatmap_function import FlatMapFunction
from sage.common.core.functions.filter_function import FilterFunction
from sage.kernel.runtime.communication.packet import StopSignal

if TYPE_CHECKING:
    try:
        from .models import JoinedEvent
    except ImportError:
        from models import JoinedEvent


class TaggedEvent:
    """
    带 tag 的事件包装器。
    
    包装原始事件，添加一个 tag 标识，用于后续的 filter 分流。
    """
    
    def __init__(self, event: Any, tag: str):
        """
        初始化带 tag 的事件。
        
        Args:
            event: 原始事件（如 JoinedEvent）
            tag: 标识符（如 "vdb1", "vdb2", "graph"）
        """
        self.event = event
        self.tag = tag
    
    def __repr__(self) -> str:
        return f"TaggedEvent(tag={self.tag}, event={self.event})"


class TagMapper(FlatMapFunction):
    """
    给事件打 tag 的 FlatMapper（复制数据流）。
    
    将输入事件复制多份，每份包装成 TaggedEvent，添加不同的 tag 标识。
    这样可以将一个流"复制"成多个带不同 tag 的流。
    
    Example:
        # 每条数据复制两份，分别打上 vdb1 和 vdb2 标签
        tagged_stream = graph_stream.flat_map(TagMapper, tags=["vdb1", "vdb2"])
    """
    
    is_flat_map = True
    
    def __init__(self, tags: list[str]):
        """
        初始化 TagMapper。
        
        Args:
            tags: 要打上的标签列表（如 ["vdb1", "vdb2"]）
        """
        super().__init__()
        self.tags = tags
    
    def execute(self, payload: Any) -> list[TaggedEvent]:
        """
        给事件打多个 tag，复制多份。
        
        Args:
            payload: 输入事件（任意类型）
        
        Returns:
            list[TaggedEvent]: 包装后的带 tag 事件列表
        """
        # StopSignal 直接透传，不复制
        if isinstance(payload, StopSignal):
            return [payload]
        
        # 为每个 tag 创建一个 TaggedEvent
        self.logger.info(f"[TAGGER] Tagging payload with tags: {self.tags} ; payload: {payload}")
        return [TaggedEvent(event=payload, tag=tag) for tag in self.tags]


class TagFilter(FilterFunction):
    """
    根据 tag 过滤事件的 Filter。
    
    只允许指定 tag 的事件通过，过滤掉其他 tag 的事件。
    配合 TagMapper 使用，实现流的分流。
    
    Example:
        vdb1_stream = tagged_stream.filter(TagFilter, target_tag="vdb1")
        vdb2_stream = tagged_stream.filter(TagFilter, target_tag="vdb2")
    """
    
    is_filter = True
    
    def __init__(self, target_tag: str):
        """
        初始化 TagFilter。
        
        Args:
            target_tag: 目标标签，只有这个 tag 的事件才能通过
        """
        super().__init__()
        self.target_tag = target_tag
    
    def execute(self, payload: TaggedEvent) -> bool:
        """
        检查事件的 tag 是否匹配。
        
        Args:
            payload: 输入的 TaggedEvent
        
        Returns:
            bool: 如果 tag 匹配返回 True（允许通过），否则返回 False（过滤掉）
        """
        # StopSignal 始终通过
        if isinstance(payload, StopSignal):
            return True
        self.logger.info(f"[FILTER] Received payload with tag={getattr(payload, 'tag', None)}; target_tag={self.target_tag}")
        # 检查 tag 是否匹配
        if isinstance(payload, TaggedEvent):
            return payload.tag == self.target_tag
        
        # 非 TaggedEvent 的数据，默认不通过
        return False


class UntagMapper(MapFunction):
    """
    移除 tag 的 Mapper。
    
    将 TaggedEvent 解包，提取原始事件。
    用于在 filter 分流后，恢复原始的事件类型。
    
    Example:
        original_stream = tagged_stream.filter(...).map(UntagMapper)
    """
    
    is_map = True
    
    def execute(self, payload: TaggedEvent) -> Any:
        """
        解包 TaggedEvent，返回原始事件。
        
        Args:
            payload: 输入的 TaggedEvent
        
        Returns:
            原始事件
        """
        # StopSignal 直接透传
        if isinstance(payload, StopSignal):
            return payload
        
        if isinstance(payload, TaggedEvent):
            return payload.event
        
        # 如果不是 TaggedEvent，直接返回原始数据
        return payload
