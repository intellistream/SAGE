# 自定义算子

> **目标**：学习如何创建可复用的自定义算子和组件

## 概述

SAGE 提供了灵活的算子开发框架，您可以通过继承基类来实现自定义的数据处理逻辑。

## 算子基类

### MapFunction - 转换算子

```python
from sage.common.core.functions import MapFunction
from sage.kernel.runtime.context import RuntimeContext

class CustomMapOperator(MapFunction):
    """自定义 Map 算子模板"""

    def __init__(self, config: dict):
        """初始化配置"""
        self.config = config
        self.state = None

    def open(self, context: RuntimeContext):
        """
        初始化资源
        在算子启动时调用一次
        """
        self.context = context
        self.logger = context.get_logger()
        self.state = self._initialize_state()

    def map(self, record):
        """
        处理单条记录
        对每条输入记录调用
        """
        return self._process(record)

    def close(self):
        """
        清理资源
        在算子结束时调用一次
        """
        if self.state:
            self.state.cleanup()

    def _initialize_state(self):
        """子类重写：初始化状态"""
        return {}

    def _process(self, record):
        """子类重写：实现处理逻辑"""
        return record
```

### FilterFunction - 过滤算子

```python
from sage.common.core.functions import FilterFunction

class CustomFilterOperator(FilterFunction):
    """自定义 Filter 算子"""

    def __init__(self, threshold=0.5):
        self.threshold = threshold

    def filter(self, record) -> bool:
        """
        判断记录是否保留
        返回 True 保留，False 过滤
        """
        score = record.get("score", 0.0)
        return score >= self.threshold
```

### SinkFunction - 输出算子

```python
from sage.common.core.functions import SinkFunction

class CustomSinkOperator(SinkFunction):
    """自定义 Sink 算子"""

    def __init__(self, output_path: str):
        self.output_path = output_path
        self.file = None

    def open(self, context):
        """打开输出文件"""
        self.file = open(self.output_path, 'w')

    def invoke(self, record):
        """写入单条记录"""
        self.file.write(json.dumps(record) + '\n')
        self.file.flush()

    def close(self):
        """关闭文件"""
        if self.file:
            self.file.close()
```

## 实用示例

### LLM 调用算子（含重试）

```python
from openai import OpenAI
import time

class LLMOperator(MapFunction):
    """带重试机制的 LLM 调用算子"""

    def __init__(self, model="gpt-4", max_retries=3):
        self.model = model
        self.max_retries = max_retries
        self.cache = {}

    def open(self, context):
        self.client = OpenAI()
        self.logger = context.get_logger()

    def map(self, record):
        prompt = record.get("prompt")

        # 缓存检查
        if prompt in self.cache:
            self.logger.info("Cache hit")
            return self.cache[prompt]

        # 带指数退避的重试
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                result = response.choices[0].message.content

                self.cache[prompt] = result
                return {"prompt": prompt, "response": result}

            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # 1s, 2s, 4s...

# 使用示例
stream = (
    env.from_source(QuerySource())
    .map(LLMOperator(model="gpt-4", max_retries=3))
    .sink(ResponseSink())
)
```

### 批处理算子

```python
class BatchOperator(MapFunction):
    """批量处理算子，提升吞吐量"""

    def __init__(self, batch_size=10, timeout=1.0):
        self.batch_size = batch_size
        self.timeout = timeout
        self.buffer = []
        self.last_batch_time = None

    def open(self, context):
        self.last_batch_time = time.time()

    def map(self, record):
        self.buffer.append(record)

        # 检查是否需要处理批次
        should_process = (
            len(self.buffer) >= self.batch_size or
            time.time() - self.last_batch_time > self.timeout
        )

        if should_process:
            results = self.process_batch(self.buffer)
            self.buffer = []
            self.last_batch_time = time.time()
            return results

        return None  # 批次未满，暂不输出

    def process_batch(self, batch):
        """批量处理逻辑"""
        # 实现批量 API 调用等
        return batch
```

### 有状态算子（窗口聚合）

```python
class WindowAggregateOperator(MapFunction):
    """滑动窗口聚合"""

    def __init__(self, window_size=100):
        self.window_size = window_size
        self.window = []

    def map(self, record):
        self.window.append(record)

        # 保持窗口大小
        if len(self.window) > self.window_size:
            self.window.pop(0)

        # 计算聚合结果
        return {
            "count": len(self.window),
            "sum": sum(r["value"] for r in self.window),
            "avg": sum(r["value"] for r in self.window) / len(self.window)
        }
```

## 算子生命周期

```
┌─────────────────────────────────────────┐
│  1. __init__(): 构造函数                │
│     - 保存配置参数                       │
│     - 不要初始化资源                     │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  2. open(context): 初始化               │
│     - 打开文件、数据库连接               │
│     - 加载模型                           │
│     - 初始化状态                         │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  3. map/filter/invoke(): 处理数据       │
│     - 多次调用                           │
│     - 处理每条记录                       │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  4. close(): 清理资源                   │
│     - 关闭文件、连接                     │
│     - 释放内存                           │
│     - 保存状态                           │
└─────────────────────────────────────────┘
```

## 最佳实践

### ✅ 推荐做法

1. **在 `open()` 中初始化资源** - 不要在 `__init__()` 中初始化重资源
1. **在 `close()` 中清理** - 确保资源正确释放
1. **异常处理** - 捕获并记录异常，避免整个 Pipeline 崩溃
1. **日志记录** - 使用 `context.get_logger()` 记录关键信息
1. **配置可调** - 通过参数控制行为，提高复用性

### ❌ 避免的错误

- 在 `__init__()` 中打开文件或数据库连接（无法序列化）
- 忘记在 `close()` 中释放资源导致内存泄漏
- 在 `map()` 中做重复的初始化操作
- 不处理异常导致任务失败

## 测试自定义算子

```python
import unittest
from sage.kernel.api.runtime import RuntimeContext

class TestCustomOperator(unittest.TestCase):
    def test_map_logic(self):
        # 创建算子
        operator = CustomMapOperator(config={})

        # 模拟 context
        context = RuntimeContext()
        operator.open(context)

        # 测试处理逻辑
        input_record = {"value": 10}
        output_record = operator.map(input_record)

        self.assertEqual(output_record["value"], 20)

        # 清理
        operator.close()
```

## 相关阅读

- [Kernel API 文档](../../guides/packages/sage-kernel/api/functions.md)
- [复杂工作流](complex-workflows.md) - 组合多个算子
- [性能调优](performance-tuning.md) - 优化算子性能

______________________________________________________________________

**下一步**：学习 [复杂工作流](complex-workflows.md) 构建多阶段处理
