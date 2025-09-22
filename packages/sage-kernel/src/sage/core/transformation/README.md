# Transformation 模块

该模块定义了 Sage Core 的转换（Transformation）系统，负责将用户定义的数据处理逻辑转换为可执行的算子图。

## 核心组件

### 基础框架
- **`base_transformation.py`**: 转换抽象基类
  - 定义转换的基本接口和生命周期
  - 管理算子工厂和函数工厂
  - 提供任务创建和执行图构建功能

### 数据源转换
- **`source_transformation.py`**: 数据源转换
  - 将数据源函数转换为源算子
  - 管理数据输入的并行度和分区
  - 支持多种数据源类型

### 数据转换操作
- **`map_transformation.py`**: 映射转换，实现一对一数据映射
- **`filter_transformation.py`**: 过滤转换，实现条件过滤
- **`flatmap_transformation.py`**: 扁平化映射转换，实现一对多映射
- **`keyby_transformation.py`**: 键分组转换，实现数据分组
- **`join_transformation.py`**: 连接转换，实现流连接操作
- **`comap_transformation.py`**: 协同映射转换，实现多流协同处理

### 数据输出转换
- **`sink_transformation.py`**: 数据输出转换
  - 将输出函数转换为输出算子
  - 管理数据输出的格式和目标
  - 支持多种输出方式

### 特殊转换
- **`batch_transformation.py`**: 批处理转换
  - 支持批量数据处理转换
  - 管理批次大小和触发条件
- **`future_transformation.py`**: 异步转换，支持异步操作

## 转换过程

```
用户API调用 → Transformation → 算子图构建 → 任务创建 → 运行时执行
    ↓              ↓              ↓           ↓           ↓
DataStream     BaseTransformation  ExecutionGraph   Task    Operator
```

## 转换类型体系

```
BaseTransformation (抽象基类)
├── SourceTransformation (数据源)
├── MapTransformation (映射)
├── FilterTransformation (过滤)
├── FlatMapTransformation (扁平化映射)
├── KeyByTransformation (键分组)
├── JoinTransformation (连接)
├── CoMapTransformation (协同映射)
├── SinkTransformation (数据输出)
├── BatchTransformation (批处理)
└── FutureTransformation (异步操作)
```

## 核心功能

### 编译时优化
- **图优化**: 消除冗余操作，合并相邻转换
- **并行度推导**: 自动计算最优并行度
- **资源分配**: 预估内存和CPU需求

### 运行时支持
- **任务调度**: 将转换编译为可调度的任务
- **故障恢复**: 支持转换级别的故障恢复
- **状态管理**: 有状态转换的状态维护

### 平台适配
- **本地执行**: 适配本地环境的转换实现
- **远程执行**: 适配分布式环境的转换实现
- **混合执行**: 支持本地和远程混合部署

## 使用特点

- **声明式定义**: 用户通过API声明转换逻辑
- **延迟执行**: 构建阶段创建转换图，执行阶段才运行
- **类型安全**: 编译时类型检查和推导
- **可组合性**: 支持转换的链式组合和嵌套
