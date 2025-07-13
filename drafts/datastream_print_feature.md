# DataStream Print 功能说明

## 概述

我们为 SAGE 数据流框架添加了便捷的 `datastream.print()` 方法，让开发者能够轻松地调试和查看数据流的内容。

## 功能特性

### 1. 便捷的 print() 方法

`DataStream` 和 `ConnectedStreams` 现在都支持 `.print()` 方法：

```python
# 基本用法
stream.print()

# 带前缀
stream.print("调试输出")

# 自定义分隔符
stream.print("结果", separator=" -> ")

# 禁用彩色输出
stream.print(colored=False)
```

### 2. 智能数据格式化

`PrintSink` 能够自动识别并格式化多种数据类型：

#### 问答对 (Question-Answer pairs)
```python
# 输入: ("什么是Python?", "Python是一种编程语言")
# 输出: 
# [Q] 什么是Python?
# [A] Python是一种编程语言
```

#### 检索结果 (Retrieval results)  
```python
# 输入: ("查询内容", ["结果1", "结果2", "结果3"])
# 输出:
# [Q] 查询内容
# [Chunks]
#   - 结果1
#   - 结果2
#   - 结果3
```

#### 字符串列表
```python
# 输入: ["项目1", "项目2", "项目3"]
# 输出:
#   - 项目1
#   - 项目2
#   - 项目3
```

#### 字典对象
```python
# 输入: {"name": "张三", "age": 25}
# 输出:
# name: 张三
# age: 25
```

### 3. 彩色输出支持

默认启用 ANSI 彩色输出，让输出更加清晰易读：
- 🔵 问题 (Question) - 青色
- 🟢 答案 (Answer) - 绿色  
- 🟡 检索块 (Chunks) - 黄色
- 🔵 字典键 (Keys) - 蓝色

## 使用示例

### 基本使用

```python
from sage_core.api.env import LocalEnvironment
from sage_common_funs.io.source import ListSource

# 创建环境
env = LocalEnvironment("demo")

# 创建数据流并打印
stream = env.from_source(ListSource, data=["数据1", "数据2", "数据3"])
stream.print("原始数据")  # 立即打印数据
```

### 链式调用中的调试

```python
result = (env.from_source(ListSource, data=["输入"])
          .print("原始输入")           # 调试点1
          .map(ProcessFunction)
          .print("处理后")           # 调试点2  
          .filter(FilterFunction)
          .print("过滤后")           # 调试点3
          .sink(FileSink, config))
```

### 与现有 Sink 的对比

```python
# 传统方式 - 使用 TerminalSink
stream.sink(TerminalSink, config)

# 新方式 - 使用 print() 方法 (更简洁)
stream.print()

# 传统方式 - 使用 FileSink 进行调试
stream.sink(FileSink, {"file_path": "debug.txt"})

# 新方式 - 使用 print() 进行调试 (更快捷)
stream.print("调试信息")
```

## API 参考

### DataStream.print()

```python
def print(self, prefix: str = "", separator: str = " | ", colored: bool = True) -> "DataStream":
    """
    便捷的打印方法 - 将数据流输出到控制台
    
    Args:
        prefix: 输出前缀，默认为空
        separator: 前缀与内容之间的分隔符，默认为 " | " 
        colored: 是否启用彩色输出，默认为True
        
    Returns:
        DataStream: 返回新的数据流用于链式调用
    """
```

### PrintSink 类

```python
class PrintSink(SinkFunction):
    """
    简洁的打印汇聚函数 - 提供便捷的datastream.print()支持
    
    支持多种数据格式的智能打印，自动检测数据类型并格式化输出
    """
    
    def __init__(self, prefix: str = "", separator: str = " | ", colored: bool = True, **kwargs):
        """
        初始化 PrintSink
        
        Args:
            prefix: 输出前缀
            separator: 前缀与内容的分隔符
            colored: 是否启用彩色输出
        """
```

## 实现细节

### 文件结构

- `sage_common_funs/io/sink.py` - 添加了 `PrintSink` 类
- `sage_core/api/datastream.py` - 添加了 `print()` 方法
- `sage_core/api/connected_streams.py` - 添加了 `print()` 方法

### 设计原则

1. **简洁性**: `.print()` 方法提供最简单的调试方式
2. **一致性**: 与现有的 `.sink()`, `.map()` 等方法保持一致的接口
3. **灵活性**: 支持自定义前缀、分隔符和颜色控制
4. **智能性**: 自动识别数据格式并进行适当的格式化
5. **链式调用**: 返回新的 DataStream 以支持方法链

### 类型支持

目前 `PrintSink` 智能识别以下数据类型：
- 问答对元组: `(question: str, answer: str)`
- 检索结果元组: `(query: str, chunks: List[str])`
- 字符串列表: `List[str]`
- 字典对象: `Dict[str, Any]` 
- 其他类型: 自动转换为字符串

## 测试

运行测试以确保功能正常：

```bash
# 运行单元测试
python tests/test_print_functionality.py

# 运行演示示例
python examples/print_demo.py
```

## 注意事项

1. `print()` 方法内部使用 `PrintSink`，因此具有相同的执行语义
2. 彩色输出在不支持 ANSI 的终端中可能显示异常，可通过 `colored=False` 禁用
3. 该方法主要用于开发和调试，生产环境建议使用专门的 Sink 函数
4. 大量数据打印可能影响性能，建议在开发阶段使用

## 未来改进

- [ ] 支持更多数据类型的智能格式化
- [ ] 添加数据截断选项（限制输出长度）
- [ ] 支持输出到日志文件的选项
- [ ] 添加数据统计信息（如数据量、类型分布等）
