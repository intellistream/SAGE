# Memory Service Refactor - Architecture Overview

> **架构师**: AI Assistant\
> **日期**: 2025-12-25\
> **目标**: 重构 SAGE 记忆服务架构，实现清晰的职责分离和可扩展性

______________________________________________________________________

## 📋 执行摘要 (Executive Summary)

### 当前问题 (Current Issues)

1. **代码重复**: `memory_service/` 和 `services/` 两套实现，后者是最新的
1. **neuromem 设计过度复杂**: 创建了过多的 Collection 类型（VDB/Graph/Hybrid），在底层做多态
1. **职责不清**: Collection、Manager、Service 三者边界模糊
1. **命名不统一**: 13个配置文件使用旧命名（short_term_memory, hierarchical_memory 等）

### 新架构核心思想 (Core Concept)

```
┌──────────────────────────────────────────────────┐
│  L5: MemoryService (Business Logic)              │
│  - 13 种记忆策略服务                              │
│  - partitional.*, hierarchical.*, etc.           │
│  - 组合使用 Collection 的索引能力实现业务逻辑     │
└──────────────────────────────────────────────────┘
                     ↓ uses
┌──────────────────────────────────────────────────┐
│  L2: neuromem (Data & Index Layer)               │
│  ┌────────────────────────────────────────────┐  │
│  │ Manager: 管理 Collection 生命周期           │  │
│  │ - register, persist, remove                │  │
│  └────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────┐  │
│  │ Collection: 统一数据容器                    │  │
│  │ - 管理 raw_data (text + metadata)          │  │
│  │ - 管理多个 Index (动态添加/删除)            │  │
│  │ - 提供索引构建和查询接口                    │  │
│  └────────────────────────────────────────────┘  │
│  Index Types: FAISS, LSH, Graph, BM25, FIFO... │
└──────────────────────────────────────────────────┘
```

### 关键改进 (Key Improvements)

| 方面                    | 当前 (Before)                   | 新设计 (After)              |
| ----------------------- | ------------------------------- | --------------------------- |
| **neuromem Collection** | 多种类型继承 (VDB/Graph/Hybrid) | 单一通用 Collection         |
| **索引管理**            | Collection 类型决定索引能力     | Collection 动态添加任意索引 |
| **Service 实现**        | 混用 Collection 类型            | 组合使用 Collection 索引    |
| **命名系统**            | 旧命名 (6种)                    | 新命名 (13种, 语义化)       |
| **代码组织**            | 两套实现                        | 单一实现                    |

______________________________________________________________________

## 🎯 重构目标 (Refactor Goals)

### 目标 1: neuromem 层简化

- ✅ 统一为单一 `UnifiedCollection` 类
- ✅ 动态索引管理（add_index, remove_index, query_by_index）
- ✅ Manager 只负责生命周期管理

### 目标 2: MemoryService 层清晰化

- ✅ 13个明确命名的服务实现
- ✅ 基于 Registry 模式的统一注册
- ✅ 移除旧的 MemoryServiceFactory
- ✅ 服务通过组合 Collection 索引实现业务逻辑

### 目标 3: 配置和命名统一

- ✅ 13个配置文件更新为新命名
- ✅ 统一配置格式
- ✅ 向后兼容策略

______________________________________________________________________

## 📚 重构文档结构 (Refactor Documents)

```
mem_docs/refactor/
├── 00_REFACTOR_OVERVIEW.md           # 本文件 - 总览
├── 01_NEUROMEM_REFACTOR_PLAN.md      # neuromem 层重构
├── 02_SERVICE_IMPLEMENTATION_PLAN.md # MemoryService 实现
├── 03_CONFIGURATION_MIGRATION.md     # 配置迁移
├── 04_TESTING_STRATEGY.md            # 测试策略
└── 05_IMPLEMENTATION_CHECKLIST.md    # 实施清单
```

**阅读顺序**:

1. 先读本文档了解全局
1. 按顺序阅读 01-05 了解细节
1. 查看 05 获取具体任务清单

______________________________________________________________________

## 🏗️ 架构分层 (Architecture Layers)

### Layer 2: neuromem (Platform - Data & Index)

**职责**: 提供通用的数据存储和索引能力

```python
# UnifiedCollection: 统一数据容器
class UnifiedCollection:
    def __init__(self, name: str):
        self.raw_data = {}  # id -> {text, metadata}
        self.indexes = {}   # index_name -> Index对象

    def add_index(self, name, index_type, **config):
        """动态添加索引"""

    def query_by_index(self, index_name, query, **params):
        """通过指定索引查询"""

# MemoryManager: 生命周期管理
class MemoryManager:
    def register_collection(self, collection): ...
    def persist(self, collection_name): ...
    def remove(self, collection_name): ...
```

### Layer 5: MemoryService (Middleware - Business Logic)

**职责**: 实现具体的记忆策略

```python
# 示例: FIFO Queue Service
class FifoQueueMemoryService(BaseMemoryService):
    def __init__(self):
        self.collection = manager.create_collection("fifo_queue")
        self.collection.add_index("queue", "fifo", max_size=100)

    def insert(self, text):
        # 业务逻辑：如果队列满了，自动淘汰最旧的
        if self.collection.query_by_index("queue", method="count") >= 100:
            oldest = self.collection.query_by_index("queue", method="peek_oldest")
            self.collection.remove_from_index("queue", oldest)
        self.collection.insert(text, indexes=["queue"])
```

______________________________________________________________________

## 📊 实施时间线 (Implementation Timeline)

### Phase 1: neuromem 重构 (2-3天)

- Task 1.1: 实现 UnifiedCollection
- Task 1.2: 简化 MemoryManager
- Task 1.3: 索引工厂统一

### Phase 2: MemoryService 实现 (3-4天)

- Task 2.1: 实现 13个服务类
- Task 2.2: Registry 系统完善
- Task 2.3: 移除旧代码

### Phase 3: 配置迁移 (1-2天)

- Task 3.1: 更新 13个配置文件
- Task 3.2: 向后兼容层

### Phase 4: 测试和验证 (2-3天)

- Task 4.1: 单元测试
- Task 4.2: 集成测试
- Task 4.3: Benchmark 验证

**总计**: 约 8-12 个工作日

______________________________________________________________________

## 🔗 相关文档 (Related Documents)

- **命名讨论**: [MEMORY_SERVICE_NAMING_DISCUSSION.md](./MEMORY_SERVICE_NAMING_DISCUSSION.md)
- **当前实现**: `packages/sage-middleware/src/sage/middleware/components/sage_mem/`
- **配置文件**: `packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/config/`

______________________________________________________________________

## 📝 下一步 (Next Steps)

1. ✅ 阅读完本文档
1. → 阅读 `01_NEUROMEM_REFACTOR_PLAN.md` 了解 neuromem 重构细节
1. → 按顺序阅读其他文档
1. → 查看 `05_IMPLEMENTATION_CHECKLIST.md` 开始实施

______________________________________________________________________

**联系方式**: 如有疑问，请查阅各子文档或与架构师讨论
