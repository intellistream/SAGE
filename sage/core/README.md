# Sage Core 模块

Sage Core 是 Sage 框架的核心模块，负责数据流管道的定义、编译和执行管理。

## 模块架构

### API 层 (`sage.core/api/`)
提供用户友好的 API 接口，用于构建数据流管道。

- **`base_function.py`**: 定义用户函数的基础抽象类
  - `BaseFunction`: 所有用户函数的基类
  - 支持声明式输入/输出标签定义
  - 提供类型安全的数据处理接口

- **`datastream.py`**: 数据流抽象
  - `DataStream`: 表示数据流管道中的数据流
  - 支持链式操作：`map()`, `sink()`, `connect()`
  - 基于标签的多路输出：`side_output()`

- **`env.py`**: 执行环境管理
  - `BaseEnvironment`: 管道执行环境的基类
  - 收集和管理 Transformation 管道
  - 提供执行上下文和配置

- **`collector.py`**: 数据收集器
  - `Collector`: 函数内部数据输出接口
  - 支持基于标签的数据发送

- **`tuple.py`**: 数据容器
  - `Data`: 数据流中数据项的容器类

### 核心层 (`sage.core/core/`)
实现框架的核心逻辑和编译优化。

#### 算子系统 (`sage.core/core/operator/`)
- **`base_operator.py`**: 算子基类
  - `BaseOperator`: 所有算子的基础实现
  - 支持基于标签的数据路由
  - 管理上下游连接关系

- **`transformation.py`**: 数据变换定义
  - `Transformation`: 表示管道中的一个变换操作
  - 管理输入/输出连接关系
  - 支持并行度配置

#### 编译器系统 (`sage.core/core/compiler/`)
- **`compiler.py`**: 管道编译器
  - `ExecutionGraph`: 将逻辑管道编译为物理执行图
  - `GraphNode`: 表示执行图中的节点
  - `GraphEdge`: 表示节点间的数据连接
  - 支持并行度展开和连接优化

#### 执行引擎 (`sage.core/core/`)
- **`engine.py`**: 执行引擎
  - 协调编译器和运行时系统
  - 管理管道的完整执行生命周期
  - 提供执行状态监控和控制

## 使用示例

```python
from sage.core.api.env import LocalEnvironment
from sage_libs.io.source import FileSource
from sage_libs.io.sink import TerminalSink

# 创建执行环境
env = LocalEnvironment("example_pipeline")

# 构建数据流管道
source_stream = env.source(FileSource, path="data.txt")
processed_stream = source_stream.map(ProcessFunction)
processed_stream.sink(TerminalSink)

# 执行管道
env.execute()
```

## 设计原则

1. **声明式编程**: 用户通过链式调用声明数据流逻辑
2. **类型安全**: 基于标签的输入/输出声明提供编译时验证
3. **可扩展性**: 支持自定义函数和算子
4. **性能优化**: 编译器进行图优化和并行化
5. **平台无关**: 核心逻辑与具体运行时解耦