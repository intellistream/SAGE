"""
Pipeline F: SAGE Operators Demo (算子库演示)
============================================

演示 SAGE 算子库中的所有主要算子类型。

算子类型:
- SourceFunction: 数据源
- MapFunction: 一对一映射
- FilterFunction: 过滤 (返回 bool)
- FlatMapFunction: 一对多映射
- SinkFunction: 数据汇
- KeyByFunction: 分区键提取
- BatchFunction: 批处理数据源
- BaseJoinFunction: 多流 Join
- BaseCoMapFunction: 多输入 CoMap

本模块提供了每种算子类型的示例实现，供参考和测试。
"""

from __future__ import annotations

import time
from collections.abc import Hashable, Iterable
from dataclasses import dataclass
from typing import Any, Optional

from sage.common.core import (
    BaseCoMapFunction,
    BaseJoinFunction,
    BatchFunction,
    FilterFunction,
    FlatMapFunction,
    KeyByFunction,
    MapFunction,
    SinkFunction,
    SourceFunction,
)
from sage.kernel.api import LocalEnvironment


# ============================================================================
# 数据模型
# ============================================================================


@dataclass
class UserEvent:
    """用户事件"""

    user_id: str
    event_type: str
    timestamp: float
    data: dict


@dataclass
class OrderEvent:
    """订单事件"""

    order_id: str
    user_id: str
    amount: float
    timestamp: float


# ============================================================================
# SourceFunction 示例
# ============================================================================


class UserEventSourceFunction(SourceFunction):
    """用户事件源: 生成用户事件流

    SourceFunction 的 execute() 方法在每次调用时返回一个数据项。
    返回 None 表示数据流结束。
    """

    def __init__(self, num_events: int = 10, **kwargs):
        super().__init__(**kwargs)
        self.num_events = num_events
        self._index = 0

    def execute(self, data: Any = None) -> Optional[UserEvent]:
        """生成下一个用户事件"""
        if self._index >= self.num_events:
            return None

        event = UserEvent(
            user_id=f"user_{self._index % 3}",
            event_type=["click", "view", "purchase"][self._index % 3],
            timestamp=time.time(),
            data={"index": self._index},
        )
        self._index += 1
        return event


# ============================================================================
# BatchFunction 示例
# ============================================================================


class OrderBatchFunction(BatchFunction):
    """订单批处理源: 批量生成订单数据

    BatchFunction 的 execute() 方法无参数，每次调用返回一个数据项。
    返回 None 表示批处理结束。
    """

    def __init__(self, num_orders: int = 10, **kwargs):
        super().__init__(**kwargs)
        self.num_orders = num_orders
        self._index = 0

    def execute(self) -> Optional[OrderEvent]:
        """生成下一个订单"""
        if self._index >= self.num_orders:
            return None

        order = OrderEvent(
            order_id=f"order_{self._index}",
            user_id=f"user_{self._index % 3}",
            amount=100.0 * (self._index + 1),
            timestamp=time.time(),
        )
        self._index += 1
        return order


# ============================================================================
# MapFunction 示例
# ============================================================================


class EnrichUserEventMapFunction(MapFunction):
    """丰富用户事件: 添加额外信息

    MapFunction 的 execute() 方法接收一个输入，返回一个输出。
    适用于一对一的数据转换。
    """

    def execute(self, event: UserEvent) -> UserEvent:
        """丰富事件数据"""
        event.data["enriched"] = True
        event.data["processed_at"] = time.time()
        return event


# ============================================================================
# FilterFunction 示例
# ============================================================================


class PurchaseEventFilterFunction(FilterFunction):
    """过滤购买事件

    FilterFunction 的 execute() 方法必须返回 bool:
    - True: 数据通过过滤，继续传递给下游
    - False: 数据被过滤掉

    注意: FilterFunction 不应该修改数据，只做判断。
    如果需要同时过滤和转换，应该使用 MapFunction + FilterFunction 组合。
    """

    def execute(self, event: UserEvent) -> bool:
        """只保留购买事件"""
        return event.event_type == "purchase"


class HighValueOrderFilterFunction(FilterFunction):
    """过滤高价值订单"""

    def __init__(self, min_amount: float = 200.0, **kwargs):
        super().__init__(**kwargs)
        self.min_amount = min_amount

    def execute(self, order: OrderEvent) -> bool:
        """只保留高价值订单"""
        return order.amount >= self.min_amount


# ============================================================================
# FlatMapFunction 示例
# ============================================================================


class SplitEventDataFlatMapFunction(FlatMapFunction):
    """拆分事件数据: 将一个事件拆分为多个子事件

    FlatMapFunction 的 execute() 方法可以:
    1. 返回一个 Iterable (如 list), 框架会自动展开
    2. 使用 self.collect() 逐个发射数据

    适用于一对多的数据转换。
    """

    def execute(self, event: UserEvent) -> Iterable[dict]:
        """拆分事件数据为多个键值对"""
        result = []
        for key, value in event.data.items():
            result.append(
                {
                    "user_id": event.user_id,
                    "event_type": event.event_type,
                    "key": key,
                    "value": value,
                }
            )
        return result


class TokenizeFlatMapFunction(FlatMapFunction):
    """分词: 使用 collect() 方式发射数据"""

    def execute(self, text: str) -> Iterable[str]:
        """分词并使用 collect() 发射"""
        words = text.split()
        # 方式 1: 使用 collect()
        for word in words:
            self.collect(word)
        # 返回 None 表示已经通过 collect() 发射了数据
        return []


# ============================================================================
# KeyByFunction 示例
# ============================================================================


class UserIdKeyByFunction(KeyByFunction):
    """按用户 ID 分区

    KeyByFunction 的 execute() 方法从数据中提取分区键。
    返回值必须是可哈希的 (Hashable)。

    常用于:
    - 数据分区
    - 有状态操作的键提取
    - Join 操作的键匹配
    """

    def execute(self, event: UserEvent | OrderEvent) -> Hashable:
        """提取用户 ID 作为分区键"""
        return event.user_id


class CompositeKeyByFunction(KeyByFunction):
    """复合键: 使用多个字段组成分区键"""

    def execute(self, event: UserEvent) -> Hashable:
        """使用 (user_id, event_type) 作为复合键"""
        return (event.user_id, event.event_type)


# ============================================================================
# BaseJoinFunction 示例
# ============================================================================


class UserOrderJoinFunction(BaseJoinFunction):
    """用户-订单 Join: 关联用户事件和订单

    BaseJoinFunction 用于多流 Join 操作。
    execute() 方法接收:
    - payload: 数据
    - key: 分区键
    - tag: 流标识 (0=第一个流, 1=第二个流, ...)

    返回一个 list，包含所有匹配的结果。
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_cache: dict[str, UserEvent] = {}
        self.order_cache: dict[str, list[OrderEvent]] = {}

    def execute(self, payload: Any, key: Any, tag: int) -> list[dict]:
        """执行 Join 逻辑"""
        results = []

        if tag == 0:  # 用户事件流
            event: UserEvent = payload
            self.user_cache[key] = event

            # 检查是否有待匹配的订单
            if key in self.order_cache:
                for order in self.order_cache[key]:
                    results.append(self._create_joined_result(event, order))
                del self.order_cache[key]

        elif tag == 1:  # 订单流
            order: OrderEvent = payload

            # 检查是否有对应的用户
            if key in self.user_cache:
                event = self.user_cache[key]
                results.append(self._create_joined_result(event, order))
            else:
                # 缓存订单等待用户数据
                if key not in self.order_cache:
                    self.order_cache[key] = []
                self.order_cache[key].append(order)

        return results

    def _create_joined_result(self, event: UserEvent, order: OrderEvent) -> dict:
        """创建 Join 结果"""
        return {
            "user_id": event.user_id,
            "event_type": event.event_type,
            "order_id": order.order_id,
            "amount": order.amount,
            "join_timestamp": time.time(),
        }


# ============================================================================
# BaseCoMapFunction 示例
# ============================================================================


class EventOrderCoMapFunction(BaseCoMapFunction):
    """多输入 CoMap: 分别处理不同流的数据

    BaseCoMapFunction 用于处理多个输入流，每个流有独立的处理方法:
    - map0(): 处理第一个输入流
    - map1(): 处理第二个输入流
    - map2(), map3(), map4(): 处理更多输入流 (可选)

    与 JoinFunction 不同，CoMap 不需要按键匹配，
    每个流的数据独立处理，可以有不同的输出类型。
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_count = 0
        self.order_count = 0

    def map0(self, event: UserEvent) -> dict:
        """处理用户事件流"""
        self.event_count += 1
        return {
            "type": "event",
            "user_id": event.user_id,
            "event_type": event.event_type,
            "count": self.event_count,
        }

    def map1(self, order: OrderEvent) -> dict:
        """处理订单流"""
        self.order_count += 1
        return {
            "type": "order",
            "order_id": order.order_id,
            "amount": order.amount,
            "count": self.order_count,
        }


# ============================================================================
# SinkFunction 示例
# ============================================================================


class PrintSinkFunction(SinkFunction):
    """打印 Sink: 输出数据到控制台

    SinkFunction 的 execute() 方法接收数据，不返回任何值。
    适用于数据输出、存储等终端操作。
    """

    def __init__(self, prefix: str = "", **kwargs):
        super().__init__(**kwargs)
        self.prefix = prefix
        self.count = 0

    def execute(self, data: Any) -> None:
        """打印数据"""
        self.count += 1
        print(f"{self.prefix}[{self.count}] {data}")


class CollectorSinkFunction(SinkFunction):
    """收集 Sink: 将数据收集到列表中"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.results: list[Any] = []

    def execute(self, data: Any) -> None:
        """收集数据"""
        self.results.append(data)


# ============================================================================
# Pipeline 示例
# ============================================================================


def demo_basic_pipeline():
    """演示基础 Pipeline: Source → Map → Filter → Sink"""
    env = LocalEnvironment("basic_demo")

    (
        env.from_source(UserEventSourceFunction, num_events=10)
        .map(EnrichUserEventMapFunction)
        .filter(PurchaseEventFilterFunction)
        .sink(PrintSinkFunction, prefix="Purchase: ")
    )

    env.execute()


def demo_flatmap_pipeline():
    """演示 FlatMap Pipeline: Source → FlatMap → Sink"""
    env = LocalEnvironment("flatmap_demo")

    (
        env.from_source(UserEventSourceFunction, num_events=5)
        .flatmap(SplitEventDataFlatMapFunction)
        .sink(PrintSinkFunction, prefix="Split: ")
    )

    env.execute()


def demo_keyby_pipeline():
    """演示 KeyBy Pipeline: Source → KeyBy → Map → Sink"""
    env = LocalEnvironment("keyby_demo")

    (
        env.from_source(UserEventSourceFunction, num_events=10)
        .keyby(UserIdKeyByFunction)
        .map(EnrichUserEventMapFunction)
        .sink(PrintSinkFunction, prefix="Keyed: ")
    )

    env.execute()


# ============================================================================
# 算子总览
# ============================================================================

OPERATOR_SUMMARY = """
SAGE 算子类型总览
================

1. SourceFunction
   - 用途: 数据源，生成数据流
   - 签名: execute(data=None) -> Optional[T]
   - 返回 None 表示数据结束

2. BatchFunction
   - 用途: 批处理数据源
   - 签名: execute() -> Optional[T]
   - 返回 None 表示批处理结束

3. MapFunction
   - 用途: 一对一数据转换
   - 签名: execute(data: T) -> R

4. FilterFunction
   - 用途: 数据过滤
   - 签名: execute(data: T) -> bool
   - 返回 True 保留数据, False 过滤掉

5. FlatMapFunction
   - 用途: 一对多数据转换
   - 签名: execute(data: T) -> Iterable[R]
   - 也可以使用 self.collect(item) 发射数据

6. KeyByFunction
   - 用途: 提取分区键
   - 签名: execute(data: T) -> Hashable

7. BaseJoinFunction
   - 用途: 多流 Join
   - 签名: execute(payload: Any, key: Any, tag: int) -> list[R]

8. BaseCoMapFunction
   - 用途: 多输入独立处理
   - 签名: map0(data) -> R, map1(data) -> R, ...

9. SinkFunction
   - 用途: 数据输出
   - 签名: execute(data: T) -> None
"""


if __name__ == "__main__":
    print(OPERATOR_SUMMARY)
    print("\n" + "=" * 60)
    print("Demo: Basic Pipeline")
    print("=" * 60)
    demo_basic_pipeline()
