# 批处理算子和函数设计文档

## 概述

本设计引入了新的批处理算子（`BatchOperator`）和批处理函数（`BatchFunction`），以及相应的环境接口，提供更友好的用户接口。用户可以声明各种类型的批处理数据源，引擎会自动判断批次大小，并在完成时自动发送停止信号。

## 设计目标

1. **用户友好性**: 用户只需要声明数据和数量，不需要手动管理停止逻辑
2. **自动化判断**: 引擎自动计算批次大小，无需用户手动设置
3. **进度可见性**: 提供清晰的进度跟踪和日志记录
4. **自动化管理**: 自动处理批处理生命周期和停止信号
5. **扩展性**: 支持多种数据源类型和自定义实现
6. **错误处理**: 优雅的错误处理和恢复机制

## 核心组件

### 1. BatchFunction 基类

```python
from sage.core.function.batch_function import BatchFunction

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
from sage.core.operator.batch_operator import BatchOperator
```

#### 主要功能：
- **自动停止管理**: 在批处理完成后自动发送停止信号
- **进度日志**: 定期记录处理进度
- **错误处理**: 在出错时也会发送停止信号
- **状态监控**: 提供批处理状态信息

### 3. BatchTransformation 变换

```python
from sage.core.transformation.batch_transformation import BatchTransformation
```

#### 主要功能：
- **算子绑定**: 绑定到BatchOperator
- **参数传递**: 传递进度日志间隔等配置参数
- **管道集成**: 与现有数据处理管道无缝集成

## BaseEnvironment 批处理接口

### 新增的批处理方法：

1. **`from_batch_collection(data, **kwargs)`** - 从数据集合创建批处理
2. **`from_batch_file(file_path, encoding='utf-8', **kwargs)`** - 从文件创建批处理
3. **`from_batch_range(start, end, step=1, **kwargs)`** - 从数字范围创建批处理
4. **`from_batch_generator(generator_func, total_count, **kwargs)`** - 从生成器创建批处理
5. **`from_batch_custom(batch_function_class, *args, **kwargs)`** - 从自定义函数创建批处理

## 内置实现

### 1. SimpleBatchFunction - 简单列表批处理

```python
# 引擎自动判断批次大小
data = ["apple", "banana", "cherry", "date"]
batch_stream = env.from_batch_collection(data)
```

### 2. FileBatchFunction - 文件批处理

```python
# 引擎自动统计文件行数
batch_stream = env.from_batch_file("/path/to/file.txt")
```

### 3. NumberRangeBatchFunction - 数字范围批处理

```python
# 引擎自动计算范围大小
batch_stream = env.from_batch_range(1, 100001)  # 10万个数字
```

### 4. CustomDataBatchFunction - 自定义数据生成

```python
def data_generator():
    for i in range(1000):
        yield {"id": i, "value": i * 2}

# 引擎根据用户提供的total_count管理批处理
batch_stream = env.from_batch_generator(data_generator, 1000)
```

## 使用场景

### 1. 基本批处理任务

```python
# 处理简单数据 - 引擎自动判断批次大小
data = [f"record_{i}" for i in range(1000)]
batch_stream = env.from_batch_collection(data)
```

### 2. 文件处理任务

```python
# 处理大文件 - 引擎自动统计行数
file_batch = env.from_batch_file("/path/to/large_file.txt")
```

### 3. 数值计算任务

```python
# 大规模数值计算 - 引擎自动计算范围
numbers = env.from_batch_range(1, 1000001)  # 100万个数字
result = (numbers
          .map(lambda x: x * x)
          .reduce(lambda a, b: a + b))
```

### 4. 复杂数据生成

```python
# 自定义批处理函数
class DatabaseBatchFunction(BatchFunction):
    def get_total_count(self) -> int:
        # 引擎调用此方法获取总数
        return db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    
    def get_data_source(self) -> Iterator[Any]:
        return db.execute("SELECT * FROM users")

batch_stream = env.from_batch_custom(DatabaseBatchFunction)
```

## 主要优势

### 与原始 SourceOperator 的对比

| 特性 | SourceOperator | BatchOperator |
|------|---------------|---------------|
| 停止信号管理 | 手动在function中发送 | 自动在operator中管理 |
| 批次大小判断 | 用户手动计算 | 引擎自动判断 |
| 进度跟踪 | 无内置支持 | 内置进度跟踪和日志 |
| 用户接口 | 需要处理停止逻辑 | 只需声明数据源 |
| 错误处理 | 手动处理 | 自动错误恢复 |
| 可见性 | 有限 | 丰富的状态信息 |

### 关键改进

1. **声明式接口**: 用户只需声明要处理什么数据，引擎自动处理其余逻辑
2. **智能批次判断**: 引擎自动计算批次大小，无需用户手动设置
3. **自动化管理**: 算子自动管理整个批处理生命周期
4. **进度可见性**: 清晰的进度反馈和完成率计算
5. **错误容错**: 即使在出错情况下也能正确发送停止信号

## 环境接口使用示例

```python
# 1. 简单数据集合
batch_stream = env.from_batch_collection([1, 2, 3, 4, 5])

# 2. 文件处理
batch_stream = env.from_batch_file("/path/to/data.txt", 
                                   progress_log_interval=1000)

# 3. 数字范围
batch_stream = env.from_batch_range(1, 100001, step=2)

# 4. 生成器
def my_generator():
    for i in range(1000):
        yield f"item_{i}"

batch_stream = env.from_batch_generator(my_generator, 1000)

# 5. 自定义批处理
class MyBatchFunction(BatchFunction):
    def get_total_count(self) -> int:
        return 100
    
    def get_data_source(self) -> Iterator[Any]:
        return iter(range(100))

batch_stream = env.from_batch_custom(MyBatchFunction)

# 所有批处理都可以直接用于处理管道
result = (batch_stream
          .map(ProcessFunction)
          .filter(FilterFunction)
          .sink(OutputSink))
```

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

### BaseEnvironment 批处理方法

- `from_batch_collection(data, **kwargs)`: 从集合创建批处理
- `from_batch_file(file_path, encoding='utf-8', **kwargs)`: 从文件创建批处理
- `from_batch_range(start, end, step=1, **kwargs)`: 从范围创建批处理
- `from_batch_generator(generator_func, total_count, **kwargs)`: 从生成器创建批处理
- `from_batch_custom(batch_function_class, *args, **kwargs)`: 从自定义函数创建批处理

## 配置选项

```python
# 所有批处理方法都支持的通用配置
batch_stream = env.from_batch_collection(
    data,
    progress_log_interval=100,  # 每100条记录记录一次进度
    delay=0.1                   # 处理延迟(秒)
)
```

## 测试和验证

运行测试套件来验证功能：

```bash
# 测试批处理算子和函数
python sage_tests/test_batch_operator.py

# 测试环境接口
python sage_tests/test_batch_environment_interfaces.py

# 运行使用示例
python sage_examples/batch_comprehensive_demo.py
```

## 未来扩展

1. **并行批处理**: 支持并行处理多个批次
2. **检查点机制**: 支持批处理状态的持久化和恢复
3. **动态批次调整**: 根据系统负载动态调整处理策略
4. **流式批处理**: 支持流式数据的批处理模式
5. **监控集成**: 与监控系统集成，提供详细的性能指标
6. **智能重试**: 支持失败任务的自动重试机制

## 总结

新的批处理设计通过以下方式大大提升了用户体验：

1. **简化接口**: 提供了5种不同的批处理接口，覆盖常见使用场景
2. **自动化管理**: 引擎自动判断批次大小，用户无需手动计算
3. **进度可见**: 内置进度跟踪，提供清晰的执行状态反馈
4. **错误处理**: 统一的错误处理机制，提升系统稳定性
5. **无缝集成**: 与现有数据处理管道完全兼容

通过将复杂的停止信号管理和批次大小计算逻辑从用户代码中抽象出来，让用户可以专注于业务逻辑的实现，大大提升了批处理任务的开发效率和运行时可见性。
