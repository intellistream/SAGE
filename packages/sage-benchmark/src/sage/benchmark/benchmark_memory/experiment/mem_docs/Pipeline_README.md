# Locomo 长轮对话记忆实验 - Pipeline 架构文档

> **注意**: 修改代码时请同步更新此文档

## 架构说明

### 三条 Pipeline 架构

本实验采用三条独立的 Pipeline 实现记忆测试功能：

#### 1. 主 Pipeline (Controller Pipeline)
```
MemorySource → PipelineCaller → MemorySink
```
- **职责**: 逐轮喂入对话历史，调用两个服务 Pipeline
- **数据流**: 从数据源读取对话 → 调用服务处理 → 保存结果

#### 2. 记忆存储 Pipeline (Memory Insert Service)
```
PipelineServiceSource → PreInsert → MemoryInsert → PostInsert → PipelineServiceSink
```
- **职责**: 存储对话到短期记忆服务
- **流程**: 接收请求 → 预处理 → 插入记忆 → 后处理 → 返回响应

#### 3. 记忆测试 Pipeline (Memory Test Service)
```
PipelineServiceSource → PreRetrieval → MemoryRetrieval → PostRetrieval → MemoryTest → PipelineServiceSink
```
- **职责**: 检索历史对话、生成答案
- **流程**: 接收请求 → 预处理 → 检索记忆 → 后处理 → 测试生成 → 返回结果

### 服务层

实验使用以下服务：

1. **ShortTermMemoryService**: 管理对话历史窗口（默认 3 轮对话 = 6 条消息）
2. **Memory Insert Service**: Pipeline 即服务（记忆存储）
3. **Memory Test Service**: Pipeline 即服务（记忆测试）

### 通信机制

- **PipelineBridge**: 实现 Pipeline 之间的双向通信
- **背压机制**: `call_service()` 阻塞调用保证顺序执行
- **服务隔离**: 两个服务共享 ShortTermMemoryService，通过背压机制避免冲突

## 测试机制

### 两阶段处理

1. **阶段 1: 记忆存储** (总是执行)
   - 将当前对话存入短期记忆
   - 更新记忆窗口

2. **阶段 2: 记忆测试** (问题驱动)
   - **触发条件**: 每当可见问题增加 1/10 时
   - **测试范围**: 从第 1 题到当前可见的最后一题
   - **测试方法**: 检索相关对话历史，生成答案并评估

### 问题驱动测试策略

- 根据对话进度动态触发测试
- 测试所有可见问题，验证记忆检索效果
- 避免频繁测试，降低计算开销

### 输出格式

结果保存为 JSON 格式，包含：
- 数据集统计信息
- 测试结果（准确率、召回率等）
- 每个问题的详细测试记录

详细输出格式请参考 `OUTPUT_FORMAT.md`

## 运行方式

```bash
# 使用默认配置和第一个样本
python packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/memory_test_pipeline.py

# 指定配置文件和任务 ID
python packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/memory_test_pipeline.py \
  --config path/to/config.yaml \
  --task_id sample_001
```

## 关键特性

- **autostop=True**: 自动停止机制
  - 等待所有 Task 停止（不只是源节点）
  - 确保队列中的数据都被处理完
  - 自动调用 `env.close()` 清理资源

- **资源管理**: 实验结束后自动清理所有资源

- **可扩展性**: 易于添加新的处理节点或修改现有流程

## 注意事项

- 配置文件必须包含 `generator` 和 `promptor` 配置
- 任务 ID 必须在数据集中存在
- 修改代码时请同步更新本文档
