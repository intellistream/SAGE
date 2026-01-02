# 高级教程

深入学习 SAGE 的高级特性和最佳实践，构建生产级的流式 AI 应用。

## 📚 本章内容

本章节涵盖 SAGE 的高级主题，适合已经掌握基础知识的开发者。

> 快速定位源码与运行命令，可参考[《教程与示例映射一览》](../tutorial-example-map.md)。

### [分布式 Pipeline](distributed-pipeline.md)

构建可扩展的分布式流式处理应用：

- 🌐 **分布式环境配置** - Ray 集群配置和资源管理
- 📊 **并行处理** - 多节点并行数据处理
- ⚡ **性能优化** - 资源分配和调度优化
- 🔄 **跨节点通信** - 高效的数据交换机制

**适合场景**：大规模数据处理、高并发推理、多 GPU 训练

👉 [查看详情](distributed-pipeline.md)

### [自定义算子](custom-operators.md)

创建可复用的自定义算子和组件：

- 🛠️ **算子基类** - MapFunction、FilterFunction、SinkFunction
- 🔧 **状态管理** - 有状态算子的实现模式
- 🎯 **生命周期** - open、map/filter、close 方法详解
- 🔌 **最佳实践** - 异常处理、资源管理、日志记录

**适合场景**：业务定制化需求、特殊数据处理逻辑、算法封装

👉 [查看详情](custom-operators.md)

### [复杂工作流](complex-workflows.md)

构建复杂的多阶段流式工作流：

- 🌲 **多分支 Pipeline** - 数据流的分支和合并
- 🔗 **流连接（Join）** - 多数据流的关联处理
- 🔄 **迭代处理** - 循环处理直到满足条件
- 📊 **聚合与窗口** - 时间窗口和聚合操作

**适合场景**：复杂业务逻辑、多模态数据处理、实时分析

👉 [查看详情](complex-workflows.md)

### [高级 RAG 技术](advanced-rag.md)

构建企业级的检索增强生成系统：

- 🗂️ **多源检索** - 从多个知识库并行检索
- 🎯 **分层检索** - 粗粒度 + 细粒度两阶段检索
- 📈 **重排序（Re-ranking）** - 提升检索精度
- 🧠 **混合检索** - 向量检索 + 关键词检索

**适合场景**：知识问答系统、文档分析、智能客服

👉 [查看详情](advanced-rag.md)

### [性能调优](performance-tuning.md)

优化 SAGE 应用的性能和资源使用：

- 📊 **性能分析** - Profiling 和瓶颈定位
- 💾 **内存优化** - 内存使用监控和优化策略
- 🔢 **批处理优化** - 批量处理提升吞吐量
- ⚡ **GPU 加速** - GPU 资源管理和优化

**适合场景**：生产环境部署、高负载场景、成本优化

👉 [查看详情](performance-tuning.md)

### [容错与可靠性](fault-tolerance.md)

构建高可用的容错系统：

- 💾 **检查点（Checkpointing）** - 状态持久化和恢复
- 🔄 **重试机制** - 智能重试和指数退避
- 🛡️ **异常处理** - 优雅降级和错误隔离
- 📊 **监控告警** - 系统健康监控

**适合场景**：生产环境、长时间运行任务、关键业务系统

👉 [查看详情](fault-tolerance.md)

## 🎯 学习路径

=== "分布式系统开发者"

```
1. [分布式 Pipeline](distributed-pipeline.md) - 理解分布式架构
2. [性能调优](performance-tuning.md) - 优化系统性能
3. [容错与可靠性](fault-tolerance.md) - 构建高可用系统
```

=== "算法工程师"

```
1. [自定义算子](custom-operators.md) - 封装算法逻辑
2. [复杂工作流](complex-workflows.md) - 构建算法 Pipeline
3. [性能调优](performance-tuning.md) - 优化推理性能
```

=== "AI 应用开发者"

```
1. [高级 RAG 技术](advanced-rag.md) - 构建智能问答
2. [复杂工作流](complex-workflows.md) - 多模态处理
3. [容错与可靠性](fault-tolerance.md) - 保障服务质量
```

## 🔍 快速参考

### 常见高级场景

| 场景               | 推荐教程                                   | 关键技术             |
| ------------------ | ------------------------------------------ | -------------------- |
| **大规模数据处理** | [分布式 Pipeline](distributed-pipeline.md) | Ray 集群、并行度配置 |
| **实时推荐系统**   | [复杂工作流](complex-workflows.md)         | 流连接、窗口聚合     |
| **智能客服**       | [高级 RAG](advanced-rag.md)                | 多源检索、重排序     |
| **业务定制化**     | [自定义算子](custom-operators.md)          | 算子开发、状态管理   |
| **性能瓶颈**       | [性能调优](performance-tuning.md)          | Profiling、批处理    |
| **生产部署**       | [容错与可靠性](fault-tolerance.md)         | 检查点、监控告警     |

### 核心概念对照

| SAGE 概念      | Apache Flink 类比 | Spark Streaming 类比 |
| -------------- | ----------------- | -------------------- |
| MapFunction    | MapFunction       | map()                |
| FilterFunction | FilterFunction    | filter()             |
| Checkpoint     | Savepoint         | Checkpoint           |
| Parallelism    | Parallelism       | Partitions           |
| Window         | Window            | Window               |

## 📖 前置知识

在学习本章内容前，建议您已经掌握：

- ✅ [快速入门](../../getting-started/quickstart.md) - SAGE 基础使用
- ✅ [基础教程](../basic/streaming-101.md) - 流式处理概念
- ✅ [Kernel 用户指南](../../guides/packages/sage-kernel/README.md) - 执行引擎原理
- ✅ Python 异步编程基础

## 💡 最佳实践提示

### 开发阶段

- 🔍 **小数据测试** - 先用小数据集验证逻辑正确性
- 📊 **逐步扩展** - 逐步增加并行度和数据规模
- 🐛 **详细日志** - 添加充分的日志便于调试

### 生产部署

- 🛡️ **容错设计** - 添加检查点和重试机制
- 📈 **监控指标** - 监控吞吐量、延迟、资源使用
- 🔄 **灰度发布** - 逐步切换流量到新版本

### 性能优化

- ⚡ **批量处理** - 合并小请求减少网络开销
- 💾 **内存管理** - 及时释放大对象，避免 OOM
- 🎯 **资源配置** - 根据负载合理分配 CPU/GPU

## 🚀 下一步

完成高级教程后，您可以：

<div class="grid cards" markdown>

- :material-rocket-launch:{ .lg .middle } **部署应用**

  ______________________________________________________________________

  将 SAGE 应用部署到生产环境

  [:octicons-arrow-right-24: 部署指南](../../guides/deployment/index.md)

- :material-code-braces:{ .lg .middle } **深入源码**

  ______________________________________________________________________

  理解 SAGE 的内部实现

  [:octicons-arrow-right-24: 架构设计](../../concepts/architecture/overview.md)

- :material-account-group:{ .lg .middle } **参与贡献**

  ______________________________________________________________________

  为 SAGE 项目做出贡献

  [:octicons-arrow-right-24: 贡献指南](../../developers/commands.md)

- :material-forum:{ .lg .middle } **加入社区**

  ______________________________________________________________________

  与其他开发者交流经验

  [:octicons-arrow-right-24: 社区](../../community/community.md)

</div>

______________________________________________________________________

**注意**：本章内容持续更新中，部分教程页面正在完善。如有问题或建议，欢迎通过
[GitHub Issues](https://github.com/intellistream/SAGE/issues) 反馈。
