# SAGE 架构层级分析与 L2 层讨论

## 问题发现

当前 PACKAGE_ARCHITECTURE.md 中的层级定义跳过了 L2 层：
- L1: sage-common (基础设施)
- **L2: 缺失**
- L3: sage-kernel, sage-libs (核心)
- L4: sage-middleware (领域)
- L5: sage-apps, sage-benchmark, sage-tools (应用)
- L6: sage-studio (界面)

## L2 层的典型职责

在经典的分层架构中，L2 层通常负责：

### 1. **数据访问层 (Data Access Layer)**
- 数据库连接和会话管理
- ORM 映射
- 数据持久化
- 缓存管理

### 2. **基础设施服务层 (Infrastructure Services)**
- 消息队列 (MQ) 客户端
- 分布式存储客户端
- 网络通信协议
- 配置中心客户端

### 3. **平台服务层 (Platform Services)**
- 认证和授权
- 日志聚合
- 监控和追踪
- 服务发现

## SAGE 当前架构中的 L2 候选代码

### 在 sage-common 中：
```
sage-common/
├── components/
│   ├── sage_vllm/service.py          # VLLMService (服务基类)
│   ├── sage_embedding/service.py     # EmbeddingService
│   └── vectordb/                      # 向量数据库客户端
├── utils/
│   └── network/                       # 网络工具
└── config/                            # 配置管理
```

### 在 sage-kernel 中：
```
sage-kernel/
└── runtime/
    ├── communication/                 # 通信层 (Queue, gRPC)
    ├── job_manager.py                 # 任务管理
    ├── job_manager_server.py          # 任务管理服务器
    ├── jobmanager_client.py           # 任务管理客户端
    ├── heartbeat_monitor.py           # 心跳监控
    ├── service/                       # 服务基础设施
    ├── context/                       # 执行上下文
    └── monitoring/                    # 监控
```

## 三种可能的架构方案

### 方案 1: 保持现状（推荐）

**理由**：
1. SAGE 的架构特点是**流式处理为核心**，不是传统的 CRUD 应用
2. 数据访问和基础设施服务已经合理分布：
   - **sage-common**: 基础组件（VectorDB客户端、配置）
   - **sage-kernel**: 运行时基础设施（通信、任务管理）
3. 没有必要强行创建 L2 层

**行动**：
- 更新文档说明为什么跳过 L2
- 明确 sage-common 和 sage-kernel 的边界

### 方案 2: 创建 sage-platform (L2)

**新包职责**：
```
sage-platform (L2):
├── data/              # 数据访问抽象
│   ├── vectordb/     # 向量数据库统一接口
│   └── cache/        # 缓存管理
├── messaging/         # 消息队列抽象
├── storage/           # 存储抽象
└── network/           # 网络通信抽象
```

**迁移内容**：
- 从 sage-common 迁移：VectorDB 客户端、网络工具
- 从 sage-kernel 迁移：通信层、任务管理客户端

**缺点**：
- 增加复杂度
- 需要大量重构
- 对于 SAGE 的用例可能是过度设计

### 方案 3: 合并为 sage-infrastructure (L1+L2)

**将 sage-common 重命名并扩展**：
```
sage-infrastructure (L1+L2):
├── core/              # L1: 核心类型和异常
├── components/        # L1: 基础组件
├── platform/          # L2: 平台服务
│   ├── data/
│   ├── messaging/
│   └── network/
└── config/            # L1: 配置
```

**缺点**：
- 混合了两个职责层
- 违反单一职责原则

## 推荐方案：方案 1（保持现状）

### 理由详解

#### 1. SAGE 不是传统 Web 应用
- **传统 Web**: Controller → Service → Repository(L2) → Database
- **SAGE**: Source → Operator Pipeline → Sink（流式处理）

#### 2. 现有分层已经合理
```
L1 (sage-common):
  - 提供基础组件和工具
  - 无业务逻辑
  - 可被所有层使用
  
L3 (sage-kernel):
  - 流式执行引擎
  - 包含运行时基础设施（通信、任务管理）
  - 这些是"执行引擎的一部分"，不是独立的平台服务
```

#### 3. sage-kernel 的 runtime 属于执行引擎
- `communication/`: 算子间通信（执行引擎功能）
- `job_manager`: 任务调度（执行引擎功能）
- `service/`: 服务基类（执行引擎抽象）

这些不是通用的"平台服务"，而是**执行引擎的组成部分**。

### 需要的文档改进

#### 1. 更新 PACKAGE_ARCHITECTURE.md

在"层级说明"部分添加：

```markdown
### 关于 L2 层

SAGE 架构中没有传统的 L2 (Infrastructure/Platform) 层，原因是：

1. **架构特点**：SAGE 是流式数据处理系统，不是传统的 CRUD 应用
2. **职责分布**：
   - **sage-common (L1)**: 包含基础组件（VectorDB客户端、配置管理）
   - **sage-kernel (L3)**: 执行引擎本身包含运行时基础设施
3. **设计原则**：遵循"足够用即可"原则，避免过度设计

如果未来需要独立的平台服务层（如统一的存储抽象、消息队列等），
可以引入 sage-platform (L2) 包。
```

#### 2. 明确 sage-common 和 sage-kernel 的边界

**sage-common (L1)** - 基础设施：
- ✅ 核心数据类型 (`Record`, `Parameter`)
- ✅ 基础组件（Embedding、VectorDB 客户端）
- ✅ 配置管理
- ✅ 通用工具函数
- ❌ 执行引擎功能
- ❌ 算子实现

**sage-kernel (L3)** - 执行引擎：
- ✅ 流式执行引擎
- ✅ 基础算子 (`map`, `filter`, `join`)
- ✅ 运行时基础设施（通信、调度）
- ✅ 任务管理
- ❌ 领域算子（RAG、LLM）
- ❌ 应用逻辑

## 检查清单

### ✅ sage-common 职责清晰
- [x] 只包含基础组件
- [x] 无执行引擎代码
- [x] 无领域逻辑

### ✅ sage-kernel 职责清晰
- [x] 执行引擎核心
- [x] 运行时基础设施属于执行引擎
- [x] 无领域算子

### ✅ 依赖关系正确
- [x] sage-common 无依赖
- [x] sage-kernel 只依赖 sage-common
- [x] 无循环依赖

## 结论

**建议采用方案 1：保持现状，更新文档说明。**

SAGE 的两层基础架构（L1: common + L3: kernel）是合理的：
- sage-common 提供共享基础设施
- sage-kernel 提供执行引擎（包含运行时基础设施）

这种设计符合 SAGE 作为流式处理系统的特点，无需强行引入 L2 层。

---

**日期**: 2025-10-22  
**作者**: SAGE Architecture Review
