# Hello Filter World !!!

`Hello Filter World`基于 SAGE Repo 里的示例
[`examples/tutorials/L3-kernel/operators/hello_filter_world.py`](https://github.com/intellistream/SAGE/blob/main/examples/tutorials/L3-kernel/operators/hello_filter_world.py)，在本例中，你将了解有关以下`function`和`transformation`的用法：

- DataStream.filter
- FilterFunction

## *A*. 场景概述

- [x] 依次从一个生成 `1 ~ 10` 的字符串记录，经 Map 转大写，再用 Filter 仅保留结尾为奇数的记录，最终打印输出。

______________________________________________________________________

## *B*. 代码示例

```python title="examples/tutorials/L3-kernel/operators/hello_filter_world.py" linenums="1"
from sage.kernel.api.local_environment import LocalEnvironment
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.batch_function import BatchFunction
from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.filter_function import FilterFunction
from sage.common.utils.logging.custom_logger import CustomLogger


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


# 过滤器示例，过滤所有偶数结尾的数据
class Oddpicker(FilterFunction):
    def execute(self, data):
        if int(data[-1]) % 2 != 0:
            return data
        else:
            return None


def main():
    env = LocalEnvironment("Hello_Filter_World")

    env.from_batch(HelloBatch).map(UpperCaseMap).filter(Oddpicker).sink(PrintSink)

    env.submit(autostop=True)
    print("Hello Filter World 示例结束")


if __name__ == "__main__":
    # 关闭日志输出
    CustomLogger.disable_global_console_debug()
    main()
```

______________________________________________________________________

## *C*. 关键类与接口

- Oddpicker ： 继承基础 `FilterFunction` 类并实现其 `execute` 方法。
- .filter转换 ： `filter` 类型 `transformation`，告知 SAGE 用 `filter_operator` 包装该算子。

在此例中，filter的作用主要是筛除不符合要求的数据，数据变换格式为： M 个输入 -> N 个输出 （M ≥ N）。
