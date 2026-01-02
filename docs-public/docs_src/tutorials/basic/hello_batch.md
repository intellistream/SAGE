# 批处理示例：Hello World

> 通过一个简单的批处理任务，快速了解 SAGE 的基本用法

## 什么是批处理？

**批处理（Batch Processing）** 是指处理 **有界流（Bounded Stream）** 数据的任务。与持续运行的流处理不同，批处理任务：

- ✅ 数据量是有限的
- ✅ 任务可以自动结束
- ✅ 适合一次性数据处理场景

常见的批处理场景包括：

- 处理文件中的数据
- 执行一次性的数据转换
- 批量导入/导出数据

## Hello World 示例

让我们通过一个完整的示例来学习如何使用 SAGE 进行批处理。

### 完整代码

创建文件 `hello_batch.py`：

```python linenums="1" title="hello_batch.py"
from sage.kernel.api.local_environment import LocalEnvironment
from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.batch_function import BatchFunction
from sage.common.utils.logging.custom_logger import CustomLogger

# 1. 数据源：生成 10 条 "Hello, World!" 字符串
class HelloBatch(BatchFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.max_count = 10  # 生成 10 个数据包

    def execute(self):
        if self.counter >= self.max_count:
            return None  # 返回 None 表示批处理完成
        self.counter += 1
        return f"Hello, World! #{self.counter}"

# 2. 处理算子：将字符串转为大写
class UpperCaseMap(MapFunction):
    def execute(self, data):
        return data.upper()

# 3. 输出目标：打印结果
class PrintSink(SinkFunction):
    def execute(self, data):
        print(data)

def main():
    # 创建本地执行环境
    env = LocalEnvironment("Hello_World")

    # 构建数据流 Pipeline：批处理源 -> map -> sink
    env.from_batch(HelloBatch).map(UpperCaseMap).sink(PrintSink)

    # 提交执行（autostop=True 表示批处理完成后自动停止）
    env.submit(autostop=True)

    print("Hello World 批处理示例结束")

if __name__ == "__main__":
    # 关闭调试日志
    CustomLogger.disable_global_console_debug()
    main()
```

### 运行示例

```bash
python hello_batch.py
```

**预期输出**：

```
HELLO, WORLD! #1
HELLO, WORLD! #2
HELLO, WORLD! #3
HELLO, WORLD! #4
HELLO, WORLD! #5
HELLO, WORLD! #6
HELLO, WORLD! #7
HELLO, WORLD! #8
HELLO, WORLD! #9
HELLO, WORLD! #10
Hello World 批处理示例结束
```

## 代码详解

SAGE 批处理程序由以下几个核心部分组成：

### 1️⃣ 数据源（BatchFunction）

```python
class HelloBatch(BatchFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.max_count = 10

    def execute(self):
        if self.counter >= self.max_count:
            return None  # 通知框架数据已生成完毕
        self.counter += 1
        return f"Hello, World! #{self.counter}"
```

**关键点**：

- 继承自 `BatchFunction`
- 实现 `execute()` 方法，每次调用返回一条数据
- **返回 `None` 表示批处理结束**，框架会自动停止数据源

### 2️⃣ 处理算子（MapFunction）

```python
class UpperCaseMap(MapFunction):
    def execute(self, data):
        return data.upper()
```

**关键点**：

- 继承自 `MapFunction`
- 实现 `execute(data)` 方法，接收上游数据，返回处理后的结果
- 一对一转换：输入一条数据，输出一条数据

### 3️⃣ 输出目标（SinkFunction）

```python
class PrintSink(SinkFunction):
    def execute(self, data):
        print(data)
```

**关键点**：

- 继承自 `SinkFunction`
- 实现 `execute(data)` 方法，定义如何输出数据
- 不需要返回值

### 4️⃣ 构建 Pipeline

```python
env = LocalEnvironment("Hello_World")
env.from_batch(HelloBatch).map(UpperCaseMap).sink(PrintSink)
env.submit(autostop=True)
```

**关键点**：

- `LocalEnvironment` 创建本地执行环境
- `from_batch()` 指定批处理数据源
- `map()` 添加数据转换算子
- `sink()` 指定输出目标
- `submit(autostop=True)` 提交并执行，批处理完成后自动停止

## 数据流动过程

```
HelloBatch (数据源)
    │
    ├─ "Hello, World! #1"
    ├─ "Hello, World! #2"
    ├─ ...
    └─ None (结束信号)
         ↓
    UpperCaseMap (转换)
         │
         ├─ "HELLO, WORLD! #1"
         ├─ "HELLO, WORLD! #2"
         └─ ...
              ↓
         PrintSink (输出)
              │
              └─ 打印到控制台
```

## 常见批处理场景

### 场景 1：处理文件数据

```python
from sage.common.core.functions.batch_function import BatchFunction

class FileBatch(BatchFunction):
    def __init__(self, file_path, **kwargs):
        super().__init__(**kwargs)
        self.file = open(file_path, 'r')
        self.lines = self.file.readlines()
        self.index = 0

    def execute(self):
        if self.index >= len(self.lines):
            self.file.close()
            return None
        line = self.lines[self.index].strip()
        self.index += 1
        return line
```

### 场景 2：批量处理列表数据

```python
class ListBatch(BatchFunction):
    def __init__(self, data_list, **kwargs):
        super().__init__(**kwargs)
        self.data = data_list
        self.index = 0

    def execute(self):
        if self.index >= len(self.data):
            return None
        item = self.data[self.index]
        self.index += 1
        return item

# 使用示例
data = ["apple", "banana", "cherry", "date"]
env.from_batch(ListBatch, data_list=data).map(processor).sink(output)
```

### 场景 3：分批处理大数据集

```python
class ChunkedBatch(BatchFunction):
    def __init__(self, total_records, chunk_size=100, **kwargs):
        super().__init__(**kwargs)
        self.total = total_records
        self.chunk_size = chunk_size
        self.processed = 0

    def execute(self):
        if self.processed >= self.total:
            return None

        # 返回一批数据
        chunk = []
        for i in range(self.chunk_size):
            if self.processed >= self.total:
                break
            chunk.append(self.fetch_data(self.processed))
            self.processed += 1

        return chunk

    def fetch_data(self, index):
        # 从数据库或其他源获取数据
        return {"id": index, "data": f"record_{index}"}
```

## 批处理 vs 流处理

| 特性     | 批处理（Batch）      | 流处理（Stream）   |
| -------- | -------------------- | ------------------ |
| 数据量   | 有限（有界流）       | 无限（无界流）     |
| 执行时间 | 自动结束             | 持续运行           |
| 数据源   | `from_batch()`       | `from_stream()`    |
| 结束标志 | 返回 `None`          | 不主动结束         |
| 适用场景 | 文件处理、一次性任务 | 实时数据、持续监控 |

## 最佳实践

### ✅ DO（推荐做法）

1. **使用 `autostop=True`** - 批处理完成后自动停止

   ```python
   env.submit(autostop=True)
   ```

1. **明确返回 `None`** - 清晰地表示批处理结束

   ```python
   if self.counter >= self.max_count:
       return None
   ```

1. **资源清理** - 在返回 `None` 前关闭文件/连接

   ```python
   if self.index >= len(self.data):
       self.file.close()
       return None
   ```

1. **关闭调试日志** - 生产环境减少日志噪音

   ```python
   CustomLogger.disable_global_console_debug()
   ```

### ❌ DON'T（避免做法）

1. **忘记返回 `None`** - 会导致程序无法自动结束

   ```python
   # ❌ 错误：没有结束标志
   def execute(self):
       if self.counter >= self.max_count:
           return  # 应该是 return None
       # ...
   ```

1. **未使用 `autostop`** - 批处理结束后仍保持运行

   ```python
   # ❌ 错误：批处理完成后不会自动停止
   env.submit()
   ```

1. **忘记调用 `super().__init__()`**

   ```python
   # ❌ 错误：未初始化父类
   def __init__(self):
       self.counter = 0  # 应该先调用 super().__init__(**kwargs)
   ```

## 下一步

- 📖 学习 [流式处理 101](./streaming-101.md) 了解无界流处理
- 🔧 探索 [Filter 算子](./operators/hello_filter_world.md) 学习数据过滤
- 🚀 查看 [MapFunction](./operators/hello_flatmap_world.md) 了解更多数据转换方式
- 📚 阅读 [高级教程](../advanced/index.md) 学习复杂场景处理

## 总结

本教程介绍了：

- ✅ 批处理的概念和适用场景
- ✅ 如何创建 BatchFunction 数据源
- ✅ 如何构建批处理 Pipeline
- ✅ 批处理的生命周期管理
- ✅ 常见批处理模式和最佳实践

现在您已经掌握了 SAGE 批处理的基础！试着修改示例代码，创建您自己的批处理应用吧！🚀
