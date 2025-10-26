# SAGE 架构总览

> **最后更新**: 2025-10-23

SAGE (Streaming AI aGent Engine) 采用分层单体架构（Modular Monolith），由 9 个独立包组成，支持构建高性能的流式 AI Agent 应用。

## 🏗️ 架构全景

```
┌─────────────────────────────────────────────────────────┐
│  L6: Interface Layer (接口层)                           │
│  ┌──────────────┐         ┌──────────────┐              │
│  │ sage-studio  │         │ sage-tools   │              │
│  │  Web UI      │         │  CLI         │              │
│  └──────────────┘         └──────────────┘              │
└─────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│  L5: Application Layer (应用层)                         │
│  ┌──────────────┐         ┌──────────────┐              │
│  │  sage-apps   │         │sage-benchmark│              │
│  │  应用实现     │         │  性能测试     │              │
│  └──────────────┘         └──────────────┘              │
└─────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│  L4: Middleware Layer (中间件层)                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │         sage-middleware                           │  │
│  │  RAG/LLM Operators + Components (Memory, DB)     │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│  L3: Core Layer (核心层)                                │
│  ┌──────────────┐         ┌──────────────┐              │
│  │ sage-kernel  │         │  sage-libs   │              │
│  │ 流式引擎      │         │ 算法库+Agents │              │
│  └──────────────┘         └──────────────┘              │
└─────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│  L2: Platform Layer (平台层)                            │
│  ┌───────────────────────────────────────────────────┐  │
│  │         sage-platform                             │  │
│  │  Queue, Storage, Service 抽象                     │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│  L1: Foundation Layer (基础设施层)                      │
│  ┌───────────────────────────────────────────────────┐  │
│  │         sage-common                               │  │
│  │  Core Types, Config, Utils, Components           │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 📦 核心组件

### L1: sage-common (基础设施)

- **职责**: 提供通用工具、配置、核心类型
- **关键模块**: core, config, utils, components
- **依赖**: 无
- **文档**: [Common →](../core/common/overview.md)

### L2: sage-platform (平台服务)

- **职责**: 消息队列、存储、服务抽象
- **关键模块**: queue, storage, service
- **依赖**: common
- **文档**: [Platform →](../core/platform/overview.md)

### L3: sage-kernel (流式引擎)

- **职责**: 流式数据处理、任务调度、分布式执行
- **关键模块**: api, operators, runtime
- **依赖**: common, platform
- **文档**: [Kernel →](../core/kernel/overview.md)

### L3: sage-libs (算法库)

- **职责**: Agents 框架、RAG 工具、I/O 工具、工作流优化
- **关键模块**: agents, rag, io, workflow, integrations
- **依赖**: common, kernel (可选)
- **文档**: [Libs →](../core/libs/overview.md)

### L4: sage-middleware (中间件)

- **职责**: 领域特定算子（RAG, LLM）和组件（Memory, VectorDB）
- **关键模块**: operators, components
- **依赖**: common, platform, kernel, libs
- **文档**: [Middleware →](../middleware/overview.md)

### L5-L6: 应用与接口

- **sage-apps**: 具体应用（医疗诊断、视频分析）
- **sage-benchmark**: 性能基准测试
- **sage-studio**: Web 可视化界面
- **sage-tools**: CLI 命令行工具
- **文档**: [Applications →](../applications/apps/overview.md)

## 🎯 设计原则

### 1. 分层架构 (Layered Architecture)

- **单向依赖**: 高层可以依赖低层，反之不可
- **清晰边界**: 每层职责明确，互不越界
- **可替换性**: 同层组件可独立替换

### 2. 接口优先 (Interface-First)

- 通过 `__init__.py` 明确公共 API
- 低层提供稳定接口
- 高层通过接口使用低层

### 3. 最小依赖 (Minimal Dependencies)

- 只依赖必需的包
- 减少耦合，提高独立性
- 支持增量部署

## 🔗 依赖规则

### ✅ 允许

```
L6 → L5, L4, L3, L2, L1
L5 → L4, L3, L2, L1
L4 → L3, L2, L1
L3 → L2, L1
L2 → L1
```

### ❌ 禁止

```
L1 → 任何其他层
L2 → L3+
L3 → L4+
同层互相依赖
```

## 📊 架构指标

| 指标          | 数值   | 状态 |
| ------------- | ------ | ---- |
| 总包数        | 9      | ✅   |
| 总模块数      | 138+   | ✅   |
| 测试数        | 1,200+ | ✅   |
| 架构违规      | 0      | ✅   |
| Layer标记覆盖 | 100%   | ✅   |
| 测试通过率    | 99.7%  | ✅   |

## 📚 深入阅读

- [包结构与依赖](./package-structure.md) - 详细的包依赖图
- [分层设计详解](./layer-design.md) - 各层设计理念
- [重构历史](./restructuring-history.md) - 架构演进过程
- [设计决策记录](./design-decisions/) - 重要架构决策

## 🚀 快速开始

从这里开始使用 SAGE:

- [安装指南](../getting-started/installation.md)
- [5分钟快速开始](../getting-started/quickstart.md)
- [第一个 Pipeline](../getting-started/first-pipeline.md)
