# Operator 模块

该模块实现了 Sage Core 的算子系统，负责在运行时执行具体的数据处理操作。算子是函数（Function）在运行时的执行载体。

## 核心组件

### 基础框架

- **`base_operator.py`**: 算子抽象基类
  - 定义算子生命周期管理
  - 提供运行时上下文和路由器集成
  - 管理函数实例的创建和执行

### 数据源算子

- **`source_operator.py`**: 数据源算子实现
  - 管理数据输入流
  - 处理数据源的启动和停止
  - 支持多种数据源类型

### 数据转换算子

- **`map_operator.py`**: 映射算子，执行一对一数据转换
- **`filter_operator.py`**: 过滤算子，根据条件过滤数据
- **`flatmap_operator.py`**: 扁平化映射算子，执行一对多转换
- **`keyby_operator.py`**: 键分组算子，按键分组数据流
- **`join_operator.py`**: 连接算子，执行流连接操作
- **`comap_operator.py`**: 协同映射算子，处理多流协同操作

### 数据输出算子

- **`sink_operator.py`**: 数据输出算子
  - 管理数据输出流
  - 支持多种输出目标
  - 处理输出缓冲和刷新

### 特殊算子

- **`batch_operator.py`**: 批处理算子
  - 支持批量数据处理
  - 管理批次边界和触发条件
- **`future_operator.py`**: 异步算子，支持异步操作执行

## 算子与函数的关系

```
Operator (运行时执行) ←→ Function (逻辑定义)
     ↑                      ↑
包含并执行                  用户定义
     ↓                      ↓
实际数据处理              处理逻辑描述
```

## 算子生命周期

1. **初始化阶段**: 创建函数实例，设置运行时上下文
1. **启动阶段**: 建立输入输出连接，准备数据处理
1. **执行阶段**: 持续处理输入数据，产生输出结果
1. **停止阶段**: 清理资源，关闭连接

## 算子类型体系

```
BaseOperator (抽象基类)
├── SourceOperator (数据源)
├── MapOperator (映射转换)
├── FilterOperator (过滤)
├── FlatMapOperator (扁平化映射)
├── KeyByOperator (键分组)
├── JoinOperator (连接)
├── CoMapOperator (协同映射)
├── SinkOperator (数据输出)
├── BatchOperator (批处理)
└── FutureOperator (异步操作)
```

## 使用特点

- **运行时执行**: 算子在运行时被实例化和执行
- **状态管理**: 支持有状态算子的状态维护
- **容错处理**: 内置错误处理和恢复机制
- **性能监控**: 集成执行指标收集和监控
- **资源管理**: 自动管理内存和网络资源

## 类型安全说明

### `type: ignore` 使用原则

本模块中某些位置使用了 `# type: ignore[attr-defined]`，这些是**有意为之**的设计选择：

1. **动态属性访问** (source_operator.py)
   - `self.task` 属性在运行时由 `BaseTask` 动态注入
   - 已添加类型声明 `task: BaseTask | None` 和运行时检查 `hasattr` + `self.task`
   
2. **子类特定方法** (flatmap_operator.py, join_operator.py, sink_operator.py)
   - `BaseFunction` 是抽象基类，特定方法在子类中定义：
     - `FlatMapFunction.insert_collector()` 
     - `JoinFunction.is_join`
     - `SinkFunction.close()`
   - 所有访问都有 `hasattr()` 运行时检查保护
   - `type: ignore` 仅用于告诉类型检查器这是预期的多态行为

3. **已知的设计问题** (Packet 类型冲突)
   - 两个不同的 `Packet` 类 (communication.packet vs router.packet)
   - 这是架构层面的问题，需要单独的重构任务解决
   - 使用 `# type: ignore[arg-type]` 标记

**原则**: 只在有充分理由且有运行时安全保障的情况下使用 `type: ignore`，并添加清晰的注释说明原因。

