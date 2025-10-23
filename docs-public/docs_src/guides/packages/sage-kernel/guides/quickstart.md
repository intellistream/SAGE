# 快速开始指南

这个指南将帮助你在5分钟内上手 SAGE Kernel，开始你的第一个流数据处理应用。

## 📦 安装

### 使用 pip 安装

```bash
# 安装核心包
pip install intsage-kernel

# 安装开发依赖（可选）
pip install intsage-kernel[dev]

# 安装企业版功能（需要许可证）
pip install intsage-kernel[enterprise]
```

### 从源码安装

```bash
git clone https://github.com/intellistream/SAGE.git
cd SAGE/packages/sage-kernel
pip install -e .
```

## 🚀 第一个例子

### 1. 简单的数据转换

```python
from sage.core.api.local_environment import LocalEnvironment

# 创建本地环境
env = LocalEnvironment("hello_sage")

# 创建数据流
numbers = env.from_batch([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

# 数据转换：平方并过滤偶数
result = (numbers
    .map(lambda x: x * x)           # 平方: [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]
    .filter(lambda x: x % 2 == 0)   # 过滤偶数: [4, 16, 36, 64, 100]
    .sink(print))                   # 输出结果

# 提交执行
env.submit()
```

### 2. 文本处理示例

```python
from sage.core.api.local_environment import LocalEnvironment

env = LocalEnvironment("text_processing")

# 模拟文本数据
sentences = env.from_batch([
    "Hello SAGE Kernel",
    "Stream processing made easy", 
    "Build powerful data pipelines",
    "Real-time analytics with Python"
])

# 文本处理管道
word_count = (sentences
    .flat_map(lambda s: s.lower().split())  # 分词
    .map(lambda word: (word, 1))            # 转换为(word, 1)
    .key_by(lambda pair: pair[0])           # 按单词分组
    .reduce(lambda a, b: (a[0], a[1] + b[1]))  # 统计词频
    .sink(print))                           # 输出结果

env.submit()
```

### 3. 实时数据处理

```python
from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function import SourceFunction, SourceContext
import time
import random

# 自定义数据源
class SensorDataSource(SourceFunction[dict]):
    def __init__(self, sensor_id: str):
        self.sensor_id = sensor_id
        self.running = True
    
    def run(self, ctx: SourceContext[dict]):
        while self.running:
            # 模拟传感器数据
            data = {
                "sensor_id": self.sensor_id,
                "temperature": random.uniform(20.0, 35.0),
                "humidity": random.uniform(30.0, 80.0),
                "timestamp": int(time.time())
            }
            ctx.emit(data)
            time.sleep(1)  # 每秒产生一条数据
    
    def cancel(self):
        self.running = False

# 创建环境
env = LocalEnvironment("sensor_monitoring")

# 添加数据源
sensor_stream = env.add_source(SensorDataSource("sensor_001"))

# 数据处理：检测异常温度
alerts = (sensor_stream
    .filter(lambda data: data["temperature"] > 30.0)  # 温度过高
    .map(lambda data: f"🚨 Alert: High temperature {data['temperature']:.1f}°C from {data['sensor_id']}")
    .sink(print))

# 启动处理（运行5秒后停止）
env.submit()
```

## 🔧 基本概念

### Environment (环境)
- 管理计算资源和执行上下文
- `LocalEnvironment`: 单机环境，适合开发测试
- `RemoteEnvironment`: 分布式环境，适合生产部署

### DataStream (数据流)
- 代表数据的流动序列
- 支持链式调用的转换操作
- 延迟执行，构建计算图

### Function (函数)
- 用户定义的数据处理逻辑
- 类型安全，支持泛型
- 内置常用函数类型

## 🛠️ 常用操作

### 数据源创建

```python
# 从集合创建
stream = env.from_batch([1, 2, 3, 4, 5])

# 从文件创建
stream = env.from_text_file("data.txt")

# 从多个文件创建  
stream = env.from_text_files("data/*.txt")

# 自定义数据源
stream = env.add_source(MySourceFunction())
```

### 数据转换

```python
# Map: 一对一转换
doubled = numbers.map(lambda x: x * 2)

# Filter: 过滤
evens = numbers.filter(lambda x: x % 2 == 0)

# FlatMap: 一对多转换
words = sentences.flat_map(lambda s: s.split())

# KeyBy: 分组
grouped = words.key_by(lambda word: word[0])  # 按首字母分组

# Reduce: 归约
sums = grouped.reduce(lambda a, b: a + b)
```

### 数据输出

```python
# 打印输出
stream.sink(print)

# 文件输出
stream.sink_to_file("output.txt")

# 自定义输出
stream.sink(MySinkFunction())
```

## 📊 完整示例：网站访问日志分析

```python
from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function import MapFunction, FilterFunction
import json
from datetime import datetime

class LogParser(MapFunction[str, dict]):
    """解析日志行"""
    def map(self, log_line: str) -> dict:
        try:
            # 假设是JSON格式的日志
            return json.loads(log_line)
        except:
            return {"error": True, "raw": log_line}

class ValidLogFilter(FilterFunction[dict]):
    """过滤有效日志"""
    def filter(self, log: dict) -> bool:
        return not log.get("error", False) and "url" in log

class PageViewExtractor(MapFunction[dict, tuple]):
    """提取页面访问信息"""
    def map(self, log: dict) -> tuple:
        return (log["url"], 1)

def main():
    env = LocalEnvironment("log_analysis")
    
    # 模拟日志数据
    log_lines = env.from_batch([
        '{"timestamp": "2025-01-01T10:00:00", "url": "/home", "status": 200, "user_id": "user1"}',
        '{"timestamp": "2025-01-01T10:01:00", "url": "/about", "status": 200, "user_id": "user2"}',
        '{"timestamp": "2025-01-01T10:02:00", "url": "/home", "status": 200, "user_id": "user3"}',
        '{"timestamp": "2025-01-01T10:03:00", "url": "/contact", "status": 404, "user_id": "user1"}',
        'invalid log line',
        '{"timestamp": "2025-01-01T10:04:00", "url": "/home", "status": 200, "user_id": "user2"}'
    ])
    
    # 日志处理管道
    page_views = (log_lines
        .map(LogParser())                    # 解析日志
        .filter(ValidLogFilter())           # 过滤有效日志
        .filter(lambda log: log["status"] == 200)  # 只统计成功访问
        .map(PageViewExtractor())           # 提取页面信息
        .key_by(lambda pair: pair[0])       # 按URL分组
        .reduce(lambda a, b: (a[0], a[1] + b[1]))  # 统计访问次数
        .map(lambda pair: f"Page {pair[0]}: {pair[1]} views")
        .sink(print))
    
    env.submit()

if __name__ == "__main__":
    main()
```

## 🎯 最佳实践

### 1. 错误处理

```python
class RobustMapFunction(MapFunction[str, dict]):
    def map(self, input_str: str) -> dict:
        try:
            return json.loads(input_str)
        except Exception as e:
            # 返回错误信息而不是抛出异常
            return {
                "error": True,
                "message": str(e),
                "input": input_str
            }
```

### 2. 配置管理

```python
# config.py
CONFIG = {
    "parallelism": 4,
    "buffer_size": 10000,
    "checkpoint_interval": "30s"
}

# main.py
env = LocalEnvironment("my_app", config=CONFIG)
```

### 3. 日志记录

```python
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LoggedMapFunction(MapFunction[str, str]):
    def map(self, value: str) -> str:
        logger.info(f"Processing: {value}")
        result = process(value)
        logger.info(f"Result: {result}")
        return result
```

### 4. 性能监控

```python
import time

class TimedMapFunction(MapFunction[str, str]):
    def __init__(self):
        self.total_time = 0
        self.count = 0
    
    def map(self, value: str) -> str:
        start = time.time()
        result = expensive_operation(value)
        self.total_time += time.time() - start
        self.count += 1
        
        if self.count % 1000 == 0:
            avg_time = self.total_time / self.count
            print(f"Processed {self.count} items, avg time: {avg_time:.3f}s")
        
        return result
```

## 🚀 下一步

恭喜！你已经掌握了 SAGE Kernel 的基础用法。现在可以：

1. 📖 阅读 [API 详细文档](../api/README.md)
2. 🌐 学习 [核心概念](../concepts.md)
3. ⚡ 了解 <!-- [数据流开发](./dataflow_development.md) -->
数据流开发指南
4. 🔍 查看 [更多示例](../examples/basic_tutorials.md)

## 📞 获取帮助

- [GitHub Issues](https://github.com/intellistream/SAGE/issues) - 报告问题
- [文档中心](../README.md) - 完整文档
- [示例代码](../examples/README.md) - 更多示例
