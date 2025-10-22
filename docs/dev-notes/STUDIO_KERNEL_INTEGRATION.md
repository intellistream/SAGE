# SAGE Studio 与 Kernel 集成架构

## 背景

SAGE 架构中存在两个执行引擎：

1. **sage-kernel**: 核心数据流引擎
   - 基于 Transformation 和 Operator
   - 支持分布式执行、容错、状态管理
   - DataStream API: `env.add_source().map().filter().sink()`

2. **sage-studio**: Web UI 流程引擎
   - 基于 Node 的可视化流程编排
   - 轻量级异步执行
   - 面向用户交互和可视化

## 当前状态（Phase 1）

### 架构
```
┌─────────────────────────────────────────┐
│         SAGE Studio (Frontend)          │
│   React Flow + Node-based UI            │
└─────────────┬───────────────────────────┘
              │ REST API
┌─────────────▼───────────────────────────┐
│    SAGE Studio Backend (FastAPI)        │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  FlowEngine (Lightweight)          │ │
│  │  - Node execution                  │ │
│  │  - Dependency resolution           │ │
│  │  - Async execution                 │ │
│  └────────────────────────────────────┘ │
└──────────────────────────────────────────┘

        ❌ 未集成 SAGE Kernel ❌
```

### 问题
1. **重复实现**：Studio 重新实现了执行引擎
2. **功能受限**：缺少 Kernel 的高级特性（容错、分布式、状态管理）
3. **维护成本**：两套执行引擎需要分别维护
4. **不一致**：Studio 执行结果可能与直接使用 Kernel 不同

## 目标架构（Phase 2）

### 集成方案
```
┌─────────────────────────────────────────┐
│         SAGE Studio (Frontend)          │
│   React Flow + Node-based UI            │
└─────────────┬───────────────────────────┘
              │ REST API
┌─────────────▼───────────────────────────┐
│    SAGE Studio Backend (FastAPI)        │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  KernelPipelineAdapter             │ │
│  │  - Flow → Pipeline 转换            │ │
│  │  - Node → Operator 映射            │ │
│  └────────────┬───────────────────────┘ │
└───────────────┼─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│         SAGE Kernel Engine              │
│  ┌────────────────────────────────────┐ │
│  │  DataStream API                    │ │
│  │  Transformation Pipeline           │ │
│  │  Execution Environment             │ │
│  └────────────────────────────────────┘ │
│                                          │
│  - 分布式执行                            │
│  - 容错恢复                              │
│  - 状态管理                              │
│  - 性能监控                              │
└──────────────────────────────────────────┘
```

### 实现步骤

#### Step 1: 创建适配器（已完成）
- [x] 创建 `adapters/kernel_adapter.py`
- [x] 定义 Flow → Pipeline 转换接口
- [x] 定义 Node → Operator 映射机制

#### Step 2: 实现核心转换逻辑
- [ ] 实现 FlowDefinition 到 DataStream Pipeline 的转换
- [ ] 处理节点依赖关系和拓扑排序
- [ ] 映射 Studio 节点类型到 SAGE 算子
- [ ] 处理数据流转换（Node inputs/outputs → Stream data）

#### Step 3: 集成执行
- [ ] 替换 FlowEngine.execute_flow() 使用 Kernel
- [ ] 保持现有 API 兼容性
- [ ] 添加执行模式选择（Lightweight vs Kernel）
- [ ] 实现执行状态同步

#### Step 4: 功能增强
- [ ] 支持 Kernel 的容错机制
- [ ] 支持分布式执行
- [ ] 集成状态管理和检查点
- [ ] 性能监控和可视化

## 代码映射

### Studio Node → Kernel Operator

| Studio Node Type | Kernel Operator | 包 |
|------------------|-----------------|-----|
| `rag.generator` | `OpenAIGenerator` | sage-middleware |
| `rag.retriever` | `ChromaRetriever` | sage-middleware |
| `rag.reranker` | `BGEReranker` | sage-middleware |
| `llm.vllm` | `VLLMGenerator` | sage-middleware |
| `data.filter` | `FilterOperator` | sage-kernel |
| `data.map` | `MapOperator` | sage-kernel |

### Flow Execution → Pipeline Execution

**Before (Current):**
```python
# Studio 自己的执行
flow = FlowDefinition(...)
execution = await flow_engine.execute_flow(flow, inputs)
```

**After (Integrated):**
```python
# 使用 Kernel 执行
from sage.studio.adapters.kernel_adapter import kernel_adapter

adapter = kernel_adapter
adapter.register_node_operator("rag.generator", OpenAIGenerator)
env = adapter.build_pipeline(flow)
result = env.execute()
```

## 迁移策略

### 渐进式迁移
1. **保持现有功能**：FlowEngine 继续工作
2. **添加适配器层**：逐步实现 KernelPipelineAdapter
3. **可选集成**：通过配置选择使用哪个引擎
4. **完全迁移**：验证后替换默认引擎

### 配置示例
```python
# studio/config/settings.py
class StudioSettings:
    # Phase 1: 使用轻量级引擎
    execution_engine = "lightweight"  # or "kernel"
    
    # Phase 2: 启用 Kernel 集成
    # execution_engine = "kernel"
    # kernel_execution_mode = ExecutionMode.LOCAL  # or DISTRIBUTED
```

## 收益

1. **统一执行**：所有 SAGE pipeline 使用相同引擎
2. **功能完整**：Studio 获得 Kernel 的所有高级特性
3. **维护简化**：只需维护一个执行引擎
4. **性能提升**：利用 Kernel 的优化和分布式能力
5. **用户体验**：Studio UI 保持不变，底层更强大

## 相关文件

- `packages/sage-studio/src/sage/studio/core/flow_engine.py` - 当前的 Flow 执行引擎
- `packages/sage-studio/src/sage/studio/adapters/kernel_adapter.py` - Kernel 集成适配器
- `packages/sage-kernel/src/sage/kernel/api/datastream.py` - Kernel DataStream API
- `packages/sage-kernel/src/sage/kernel/operators/` - 基础算子
- `packages/sage-middleware/src/sage/middleware/operators/` - 领域算子

## 下一步

1. 完善 `KernelPipelineAdapter` 的实现
2. 创建单元测试验证转换正确性
3. 在 Studio 中添加引擎选择配置
4. 逐步迁移现有 Flow 使用 Kernel 执行
5. 文档化最佳实践和使用指南
