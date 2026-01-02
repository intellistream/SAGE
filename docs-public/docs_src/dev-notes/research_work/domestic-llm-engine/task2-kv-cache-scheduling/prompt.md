# Prompt · 课题二 / PR2+PR3+PR4：prefix_reuse + kv_runtime + kv_policy

你是负责 **KV 运行时与策略栈** 的架构师。请设计并落地前缀复用、KV 池化/分层/迁移、策略/收益模型，全部基于新目录 `prefix_reuse/`, `kv_runtime/`,
`kv_policy/`，并与 LMDeploy Hook 对齐。

______________________________________________________________________

## 背景与目标

- 目标：32K/64K/128K 长上下文稳定运行，KV 池利用率 ≥90%，KV hit 提升显著，TTFT/TPOT 不回退（或改善）。
- 作用域：
  - PR2：`prefix_reuse`（索引/匹配/metrics/bench）
  - PR3：`kv_runtime`（KVPool/Hierarchy/Migrator/Quota/Defrag + lmdeploy_backend）
  - PR4：`kv_policy`（驱逐/迁移/收益/生命周期预测）
- Hook：对接 LMDeploy `kv_manager`（fetch/store/migrate/eviction callbacks）和 `scheduler_ir`（计划下发、PD 分离）。

______________________________________________________________________

## 研究内容（Scope）

1. **prefix_reuse**

- 组件：`PrefixReuseIndex`, `PrefixMatcher`, `PrefixReuseMetrics`。
- 能力：最长/多命中策略，校验/冲突处理，回填 KV block，支持并发安全实现。
- Bench：批量构造可复用/不可复用请求，输出命中率/匹配长度/延迟 (p50/p99)。

2. **kv_runtime**

- 组件：`KVPool`, `BlockManager`, `HierarchyManager`, `KVMigrator`, `QuotaManager`,
  `KVBackendProtocol`，默认实现 `lmdeploy_backend`（可选 `vllm_backend`）。
- 能力：池化/分层(HBM/DDR/NVMe)/迁移/碎片整理/配额；统计利用率、碎片率、迁移带宽；支持迁移计划与淘汰回调。
- 接口：`allocate/free/get_utilization/get_fragmentation`, `migrate(plan)`, `get_block_info`。

3. **kv_policy**

- 组件：`EvictionPolicy`(LRU/LFU/ARC/S3FIFO)、`MigrationPolicy`, `CostBenefitModel`,
  `LifetimePredictor`。
- 能力：选淘汰候选、迁移决策、收益-代价评估、生命周期预测；可热插拔策略比较。

4. **与 scheduler_ir / comm_backend / accel 协同**

- PD 分离：通过 `scheduler_ir` 接收 Prefill/Decode 阶段计划；kv_policy 提供预算/淘汰建议。
- 通信：迁移计划可委托 `comm_backend`；需要带宽/延迟反馈。
- 量化：kv_precision 由 `accel` 配置，kv_runtime 接受精度切换（prefill/decoding 可不同）。

______________________________________________________________________

## 目录结构（硬约束）

```
prefix_reuse/
    ├── __init__.py
    ├── index.py            # PrefixReuseIndex
    ├── matcher.py          # PrefixMatcher
    ├── metrics.py          # PrefixReuseMetrics
    └── benchmarks/

kv_runtime/
    ├── __init__.py
    ├── pool.py             # KVPool
    ├── block_manager.py    # BlockManager
    ├── hierarchy.py        # HierarchyManager
    ├── migrator.py         # KVMigrator
    ├── quota.py            # QuotaManager
    ├── backend_protocol.py # KVBackendProtocol
    ├── backends/
    │   ├── lmdeploy_backend.py
    │   └── vllm_backend.py (可选)
    └── benchmarks/

kv_policy/
    ├── __init__.py
    ├── eviction.py         # EvictionPolicy
    ├── migration.py        # MigrationPolicy
    ├── cost_benefit.py     # CostBenefitModel
    ├── lifetime.py         # LifetimePredictor
    └── benchmarks/
```

______________________________________________________________________

## Success Criteria

- 性能：池利用率 ≥90%；HBM→DDR 迁移带宽利用 ≥80%；TTFT/TPOT 无回退，长上下文吞吐稳定；KV hit 提升可量化。
- 工程化：
  - 单测覆盖 prefix/kv_runtime/kv_policy 核心逻辑与异常路径。
  - LMDeploy backend 集成可运行（补丁后）；与 scheduler_ir/comm_backend/accel 接口对齐。
  - Bench 输出 JSON/CSV；策略可热插拔对比。
- 兼容性：仅使用新目录和协议，禁止 legacy 路径。

______________________________________________________________________

## 交付物

1. 设计文档：前缀索引、KV 池化/分层/迁移、策略/收益模型、Hook 对接、bench 方案。
1. 核心代码：`prefix_reuse/`, `kv_runtime/`, `kv_policy/` 全量实现 + `lmdeploy_backend`。
1. 测试：单测（索引/池化/策略/迁移异常），集成测（LMDeploy patched + kv_runtime/kv_policy），前缀复用 E2E。
1. Benchmark：长上下文/混合负载/策略对比；输出 JSON/Markdown。
1. 配置/文档：README（各模块）；可选 `kv_runtime_presets.yaml`（配额/层级），`prefix_reuse`/`kv_policy` 调优指引。
