# Hello FlatMap World !!!

`Hello FlatMap World` 基于 SAGE 仓库示例
[`examples/tutorials/transformation-api/hello_flatmap_world.py`](https://github.com/intellistream/SAGE/blob/main/examples/tutorials/transformation-api/hello_flatmap_world.py)，在本例中，你将了解以下
`function` 与 `transformation` 的用法：

- DataStream.map
- DataStream.flatmap
- FlatMapFunction（返回语义）
- SinkFunction / BatchFunction

## *A*. 场景概述

- [x] 从一个批源生成 `1 ~ 10` 的字符串记录，经 Map 转大写，再用 FlatMap 将每条字符串切分为多个单词并逐条下发，最终打印输出。

______________________________________________________________________

## *B*. 代码示例

```python title="examples/tutorials/transformation-api/hello_flatmap_world.py" linenums="1"
# 此例意在说明FlatMap的使用
from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.map_function import MapFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.function.flatmap_function import FlatMapFunction


class HelloBatch(BatchFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.max_count = 10

    def execute(self):
        if self.counter >= self.max_count:
            return None
        self.counter += 1
        return f"Hello, World! #{self.counter}"


class UpperCaseMap(MapFunction):
    def execute(self, data):
        return data.upper()


class PrintSink(SinkFunction):
    def execute(self, data):
        print(data)


# 利用FlatMapFunction实现单词拆分
class SplitWords(FlatMapFunction):
    def execute(self, data):
        words = data.split()
        return words


def main():
    env = LocalEnvironment("Hello_Flatmap_World")

    env.from_batch(HelloBatch).map(UpperCaseMap).flatmap(SplitWords).sink(PrintSink)

    env.submit(autostop=True)
    print("Hello Flatmap World 示例结束")


if __name__ == "__main__":
    # 关闭日志输出
    CustomLogger.disable_global_console_debug()
    main()
```

______________________________________________________________________

## *C*. 关键类与接口

- SplitWords：继承基础 `FlatMapFunction` 并实现其 `execute`，返回一个可迭代对象，框架会逐条下发其中元素；也可使用 `collector.collect()`
  逐条输出。
- .flatmap 转换：`flatmap` 类型 `transformation`，告知 SAGE 用 `flatmap_operator` 包装该算子。

在此例中，flatmap 的作用是将一条输入拆解为多条输出，数据变换示意：M 个输入 -> N 个输出（通常 N ≥ M）。
