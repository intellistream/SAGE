# sage-libs 外迁路线图 (Externalization Roadmap)

**目标**: 将 sage-libs 打造为轻量接口层，重型实现全部外迁到独立 PyPI 包

## 已完成 ✅

### Phase 1: ANNS & AMMS (2026-01-09)

- ✅ **isage-anns** - ANNS 算法

  - 移除: wrappers/ (376K)
  - 保留: interface/ (68K)
  - 节省: 308K

- ✅ **isage-amms** - AMM 算法

  - 移除: wrappers/ + 构建文件 (8K+)
  - 保留: interface/ (68K)
  - 节省: ~40K

### Phase 2: 模块重组 (2026-01-09)

- ✅ 整合 agent 相关模块到 `agentic/`
  - sias/, reasoning/, eval/ → agentic/
  - 从 13 个顶层模块 → 10 个

**总节省**: ~350K\
**状态**: 完成并测试通过

______________________________________________________________________

## 计划中 🚧

### Phase 3: Agentic (高优先级)

**目标包**: `isage-agentic`\
**当前大小**: 1.3M, 77 files\
**预计节省**: ~1.2M (保留 100K 接口)

#### 保留 (Interface Layer)

```
agentic/interface/
├── protocols/
│   ├── agent.py
│   ├── planner.py
│   ├── tool_selector.py
│   └── workflow.py
├── registries/
│   ├── planner_registry.py
│   ├── selector_registry.py
│   └── workflow_registry.py
└── schemas/
    ├── plan_types.py
    └── constraint_types.py
```

#### 外迁 (Implementations)

- agents/planning/\* (planners)
- agents/action/tool_selection/\* (selectors)
- agents/bots/\* (bot implementations)
- agents/runtime/\* (orchestrator)
- workflow/generators/\* (generators)
- workflow/optimizers/\* (optimizers)
- sias/\* (tool selection reasoning)
- reasoning/\* (search algorithms)
- eval/\* (evaluation metrics)

**时间估计**: 2 周

### Phase 4: RAG Toolkit (中优先级)

**目标包**: `isage-rag`\
**当前大小**: 76K, 4 files\
**预计外迁**: 轻量模块，可能合并到 isage-agentic 或独立

#### 当前组件

- chunk.py - 文本分块
- document_loaders.py - 文档加载器
- types.py - 类型定义

#### 扩展计划 (外迁后)

- retrievers/ - 检索器实现
- rerankers/ - 重排算法
- context_builders/ - 上下文构建
- post_processing/ - 后处理工具

**时间估计**: 1 周

### Phase 5: Privacy & Unlearning (中优先级)

**目标包**: `isage-privacy`\
**当前大小**: 196K, 13 files\
**预计节省**: ~180K

#### 保留 (Interface)

- privacy/interface/
  - protocols.py
  - registry.py

#### 外迁 (Implementations)

- unlearning/\* - 机器遗忘算法

**时间估计**: 1 周

______________________________________________________________________

## 保留模块 (不外迁)

这些模块保持在 sage-libs 中，因为它们是轻量工具或核心接口：

### Foundation (340K, 19 files)

**原因**: 基础工具库，纯 Python，无重依赖

- tools/, io/, context/, filters/
- 被其他模块广泛依赖

### Dataops (76K, 5 files)

**原因**: 轻量数据变换工具

- json_ops, table, text, sampling
- 通用性高，依赖少

### Safety (60K, 4 files)

**原因**: 轻量安全工具

- content_filter, pii_scrubber, policy_check
- 无重依赖

### Integrations (148K, 5 files)

**原因**: 第三方适配器，薄封装

- 保持灵活性和快速迭代

### Finetune (460K, 20 files)

**待定**: 可能部分外迁

- 核心训练工具保留
- 特定算法可外迁

______________________________________________________________________

## 外迁优先级排序

| 模块     | 大小 | 优先级 | 原因                       |
| -------- | ---- | ------ | -------------------------- |
| agentic  | 1.3M | 🔴 高  | 最大模块，独立生态价值高   |
| privacy  | 196K | 🟡 中  | 专业领域，独立版本管理更好 |
| rag      | 76K  | 🟡 中  | 快速扩展，避免污染核心     |
| finetune | 460K | 🟢 低  | 与核心耦合较紧             |

______________________________________________________________________

## 时间线

### Q1 2026 (Jan-Mar)

- ✅ Week 1-2: Phase 1 & 2 (ANNS/AMMS + 重组)
- 🚧 Week 3-4: Phase 3 开始 (agentic 接口准备)
- Week 5-6: Phase 3 完成 (agentic 外迁)

### Q2 2026 (Apr-Jun)

- Week 7-8: Phase 4 (RAG 外迁)
- Week 9-10: Phase 5 (Privacy 外迁)
- Week 11-12: 文档完善和测试

______________________________________________________________________

## 依赖关系图

```
sage-libs (核心接口层)
├── isage-anns (ANNS 实现)
├── isage-amms (AMM 实现)
├── isage-agentic (Agent 实现)
│   └── depends on: sage-libs, transformers, torch
├── isage-rag (RAG 实现)
│   └── depends on: sage-libs, isage-anns
└── isage-privacy (Privacy 实现)
    └── depends on: sage-libs, torch
```

______________________________________________________________________

## 成功指标

1. **大小**: sage-libs 从 2.5M → \<500K
1. **模块数**: 从 10 个顶层 → 6 个核心 + 接口
1. **测试时间**: CI 从 45min → \<15min
1. **独立性**: 每个外部包可独立发布
1. **兼容性**: 工厂模式保持向后兼容

______________________________________________________________________

## 下一步行动

1. [ ] Review agentic externalization plan with team
1. [ ] Create `agentic/interface/` structure
1. [ ] Set up `intellistream/sage-agentic` repo
1. [ ] Start Phase 3 implementation
