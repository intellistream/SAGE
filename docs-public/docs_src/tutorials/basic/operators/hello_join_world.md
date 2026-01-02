# Hello Join World !!!

`Hello Join World` 基于 SAGE 仓库示例
[`examples/tutorials/L3-kernel/operators/hello_join_world.py`](https://github.com/intellistream/SAGE/blob/main/examples/tutorials/L3-kernel/operators/hello_join_world.py)，演示按键分区与双流
Join：

- DataStream.keyby
- DataStream.connect
- ConnectedStreams.join（BaseJoinFunction）

## *A*. 场景概述

- [x] 两条批源流分别产生带 id 的记录，经 keyby 提取相同 key 后，通过 connect + join 进行关联，输出配对后的合并结果并打印。

______________________________________________________________________

## *B*. 代码示例

```python title="examples/tutorials/L3-kernel/operators/hello_join_world.py" linenums="1"
# 此例用到了keyby和join操作符，展示如何将两个数据流按key进行关联。
from sage.kernel.api.local_environment import LocalEnvironment
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.batch_function import BatchFunction
from sage.common.core.functions.keyby_function import KeyByFunction
from sage.common.core.functions.join_function import BaseJoinFunction
from sage.common.utils.logging.custom_logger import CustomLogger


class SourceOne(BatchFunction):
    def __init__(self):
        super().__init__()
        self.counter = 0

    def execute(self):
        self.counter += 1
        if self.counter > 5:
            return None
        return {"id": self.counter, "msg": f"Hello-{self.counter}", "type": "hello"}


class SourceTwo(BatchFunction):
    def __init__(self):
        super().__init__()
        self.counter = 0

    def execute(self):
        self.counter += 1
        if self.counter > 5:
            return None
        return {"id": self.counter, "msg": f"World-{self.counter}", "type": "world"}


class IdKeyBy(KeyByFunction):
    def execute(self, data):
        return data.get("id")


class PrintSink(SinkFunction):
    def execute(self, data):
        print(f"🔗 Joined Streaming: {data}")


class HelloWorldJoin(BaseJoinFunction):
    """
    Join 算子示例：
    execute(payload, key, tag) 参数说明：
      - payload: 流里传过来的原始数据 (dict)
      - key: 由 keyby 算子提取出来的分区键 (比如这里的 id)
      - tag: 数据来源标识 (0=左流 / 第一个流, 1=右流 / 第二个流)
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hello_cache = {}  # {key: [payloads]}
        self.world_cache = {}  # {key: [payloads]}

    def execute(self, payload, key, tag):
        results = []
        data_type = payload.get("type", "")

        if tag == 0:  # 第一个流 (Hello)
            if data_type == "hello":
                # 缓存 Hello 数据
                self.hello_cache.setdefault(key, []).append(payload)

                # 检查是否有匹配的 World 数据
                if key in self.world_cache:
                    for world_data in self.world_cache[key]:
                        results.append(self._merge(payload, world_data, key))

        elif tag == 1:  # 第二个流 (World)
            if data_type == "world":
                # 缓存 World 数据
                self.world_cache.setdefault(key, []).append(payload)

                # 检查是否有匹配的 Hello 数据
                if key in self.hello_cache:
                    for hello_data in self.hello_cache[key]:
                        results.append(self._merge(hello_data, payload, key))

        return results

    def _merge(self, hello_data, world_data, key):
        return {"id": key, "msg": f"{hello_data['msg']} + {world_data['msg']}"}


def main():
    env = LocalEnvironment("Hello_Join_World")

    source1 = env.from_batch(SourceOne).keyby(IdKeyBy)
    source2 = env.from_batch(SourceTwo).keyby(IdKeyBy)

    # connect + join
    source1.connect(source2).join(HelloWorldJoin).sink(PrintSink)

    # 提交但不使用 autostop，而是手动控制
    env.submit()

    # 等待一段时间让批处理完成
    import time

    time.sleep(2)  # 给足够时间让所有数据处理完成

    print("Hello Join World 示例结束")


if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    main()
```

______________________________________________________________________

## *C*. 关键类与接口

- KeyByFunction：提取 key 用于分区，确保 join 覆盖需要关联的记录。
- BaseJoinFunction：双流 Join 算子，框架传入 (payload, key, tag)。需考虑乱序、重复与缓存清理策略（示例为最简实现）。
- join 是双向触发：左或右任一到达都会尝试与对方缓存匹配。

扩展：订单与支付对账（按 order_id join）、实时监控（指标流与阈值流按指标名 join 并生成告警）等。
