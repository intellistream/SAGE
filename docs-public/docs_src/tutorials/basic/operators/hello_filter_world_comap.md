# Hello CoMap World !!!

`Hello CoMap World` 基于 SAGE 仓库示例
[`examples/tutorials/transformation-api/hello_comap_world.py`](https://github.com/intellistream/SAGE/blob/main/examples/tutorials/transformation-api/hello_comap_world.py)。在本例中，你将了解以下
function 与 transformation 的用法：

- DataStream.connect
- ConnectedStreams.comap（BaseCoMapFunction）
- 多源批流合并处理

## *A*. 场景概述

- [x] 两条批源流分别产生消息，通过 connect 合并为双输入流，使用 comap 对左右两路各自处理后，统一下发到下游 Sink 并打印。

______________________________________________________________________

## *B*. 代码示例

```python title="examples/tutorials/transformation-api/hello_comap_world.py" linenums="1"
# 此例意在说明如何将两个流通过comap合为一个流

from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function.sink_function import SinkFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.comap_function import BaseCoMapFunction


# 定义两个简单数据源：
class SourceOne(BatchFunction):
    def __init__(self):
        super().__init__()
        self.counter = 0

    def execute(self):
        self.counter += 1
        if self.counter > 5:
            return None
        return {"msg": f"No.{self.counter}: Hello"}


class SourceTwo(BatchFunction):
    def __init__(self):
        super().__init__()
        self.counter = 0

    def execute(self):
        self.counter += 1
        if self.counter > 10:
            return None
        return {"msg": f"World! #{self.counter}"}


class HelloCoMapProcessor(BaseCoMapFunction):
    def map0(self, data):
        return f"[Stream0] 👋 {data['msg']}"

    def map1(self, data):
        return f"[Stream1] 🌍 {data['msg']}"


class PrintSink(SinkFunction):
    def execute(self, data):
        print(data)


def main():
    env = LocalEnvironment("Hello_CoMap_World")

    # 两个数据源
    source1 = env.from_batch(SourceOne)
    source2 = env.from_batch(SourceTwo)

    # 将两个流 connect 在一起，并用 comap 分开处理
    source1.connect(source2).comap(HelloCoMapProcessor).sink(PrintSink)

    env.submit(autostop=True)
    print("Hello Comap World 示例结束")


if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    main()
```

______________________________________________________________________

## *C*. 关键类与接口

- BaseCoMapFunction：实现 `map0`/`map1`，分别处理左/右两路输入，属于一对一变换（不要返回可迭代对象，扁平化应使用 FlatMap）。
- .connect/.comap：将两路上游连接为 ConnectedStreams，并分别应用映射；两侧输入类型可不同，但输出类型需统一以供下游继续处理。

常见用法包括“主副数据源统一化”场景：两路数据分别清洗后输出统一 schema，便于后续统一处理。
