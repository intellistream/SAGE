# 批处理算子和函数设计文档

## 概述

本设计引入了新的批处理算子（`BatchOperator`）和批处理函数（`BatchFunction`），提供更友好的用户接口。用户可以声明一个批处理算子，该算子会预先计算要输出的记录数量，并在完成时自动发送停止信号。

## 设计目标

1. **用户友好性**: 用户只需要声明数据和数量，不需要手动管理停止逻辑
2. **进度可见性**: 提供清晰的进度跟踪和日志记录
3. **自动化管理**: 自动处理批处理生命周期和停止信号
4. **扩展性**: 支持多种数据源类型和自定义实现
5. **错误处理**: 优雅的错误处理和恢复机制

## 核心组件

### 1. BatchFunction 基类

```python
from sage_core.function.batch_function import BatchFunction

class MyBatchFunction(BatchFunction):
    def get_total_count(self) -> int:
        # 返回要处理的总记录数
        return 100
    
    def get_data_source(self) -> Iterator[Any]:
        # 返回数据源迭代器
        return iter(range(100))
```

#### 主要功能：
- **预定义记录数量**: 通过 `get_total_count()` 声明总记录数
- **数据源管理**: 通过 `get_data_source()` 提供数据迭代器
- **进度跟踪**: 自动跟踪处理进度和完成率
- **状态管理**: 管理批处理的完成状态

### 2. BatchOperator 算子

```python
from sage_core.operator.batch_operator import BatchOperator
```

#### 主要功能：
- **自动停止管理**: 在批处理完成后自动发送停止信号
- **进度日志**: 定期记录处理进度
- **错误处理**: 在出错时也会发送停止信号
- **状态监控**: 提供批处理状态信息

## 内置实现

### 1. SimpleBatchFunction - 简单列表批处理

```python
from sage_core.function.batch_function import SimpleBatchFunction

# 处理预定义的数据列表
data = ["apple", "banana", "cherry", "date"]
batch_function = SimpleBatchFunction(data, ctx)
```

### 2. FileBatchFunction - 文件批处理

```python
from sage_core.function.batch_function import FileBatchFunction

# 逐行处理文件内容
batch_function = FileBatchFunction("/path/to/file.txt", ctx)
```

### 3. 自定义批处理函数示例

```python
class NumberRangeBatchFunction(BatchFunction):
    def __init__(self, start: int, end: int, step: int = 1, ctx=None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.start = start
        self.end = end
        self.step = step
    
    def get_total_count(self) -> int:
        return max(0, (self.end - self.start + self.step - 1) // self.step)
    
    def get_data_source(self) -> Iterator[Any]:
        return iter(range(self.start, self.end, self.step))
```

## 使用场景

### 1. 基本批处理任务

```python
# 创建数据
data = [f"record_{i}" for i in range(1000)]

# 创建批处理函数
batch_func = SimpleBatchFunction(data, ctx)

# 在任务中使用BatchOperator
# 算子会自动处理数据并在完成后发送停止信号
```

### 2. 文件处理任务

```python
# 处理大文件
file_batch = FileBatchFunction("/path/to/large_file.txt", ctx)

# BatchOperator会：
# 1. 预先统计文件行数
# 2. 逐行处理文件内容  
# 3. 显示处理进度
# 4. 完成后自动发送停止信号
```

### 3. 数据生成任务

```python
# 生成斐波那契数列
def fibonacci_generator():
    a, b = 0, 1
    for _ in range(100):
        yield a
        a, b = b, a + b

custom_batch = CustomDataBatchFunction(fibonacci_generator, 100, ctx)
```

## 主要优势

### 与原始 SourceOperator 的对比

| 特性 | SourceOperator | BatchOperator |
|------|---------------|---------------|
| 停止信号管理 | 手动在function中发送 | 自动在operator中管理 |
| 进度跟踪 | 无内置支持 | 内置进度跟踪和日志 |
| 用户接口 | 需要处理停止逻辑 | 只需声明数据和数量 |
| 错误处理 | 手动处理 | 自动错误恢复 |
| 可见性 | 有限 | 丰富的状态信息 |

### 关键改进

1. **声明式接口**: 用户只需声明要处理什么数据，不需要关心何时停止
2. **自动化管理**: 算子自动管理整个批处理生命周期
3. **进度可见性**: 清晰的进度反馈和完成率计算
4. **错误容错**: 即使在出错情况下也能正确发送停止信号

## API 参考

### BatchFunction 方法

- `get_total_count() -> int`: 获取总记录数（抽象方法）
- `get_data_source() -> Iterator[Any]`: 获取数据源（抽象方法）
- `execute() -> Any`: 执行批处理逻辑
- `is_finished() -> bool`: 检查是否完成
- `get_progress() -> Tuple[int, int]`: 获取进度 (当前, 总数)
- `get_completion_rate() -> float`: 获取完成率 (0.0-1.0)
- `reset()`: 重置批处理状态

### BatchOperator 方法

- `process_packet(packet=None)`: 处理数据包（核心方法）
- `get_batch_info() -> Dict[str, Any]`: 获取批处理状态信息
- `reset_batch()`: 重置批处理
- `force_complete()`: 强制完成批处理

## 配置选项

```python
# 创建批处理算子时的配置选项
operator = BatchOperator(
    function_factory, 
    ctx, 
    progress_log_interval=100  # 每100条记录记录一次进度
)
```

## 测试和验证

运行测试套件来验证功能：

```bash
cd sage_tests
python test_batch_operator.py
```

运行使用示例：

```bash
cd sage_examples  
python batch_operator_examples.py
```

## 未来扩展

1. **并行批处理**: 支持并行处理多个批次
2. **检查点机制**: 支持批处理状态的持久化和恢复
3. **动态批次大小**: 根据系统负载动态调整批处理大小
4. **流式批处理**: 支持流式数据的批处理模式
5. **监控集成**: 与监控系统集成，提供详细的性能指标

## 总结

新的批处理设计提供了更友好的用户接口，将复杂的停止信号管理逻辑从用户代码中抽象出来，让用户可以专注于业务逻辑的实现。通过预定义记录数量和自动进度跟踪，大大提升了批处理任务的开发体验和运行时可见性。
