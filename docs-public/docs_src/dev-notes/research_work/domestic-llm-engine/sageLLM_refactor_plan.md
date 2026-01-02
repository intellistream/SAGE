# sageLLM 模块化重构计划（含 LMDeploy 深度集成）

> 目标：让不同同学可独立在 6 个研究方向上开展工作，同时把国产推理引擎（LMDeploy/TurboMind）工程化接入，去掉 legacy 兼容层。

## 目录（建议存放位置）

```
packages/sage-common/src/sage/common/components/sage_llm/sageLLM/
├── core/               # 协调层：ControlPlaneManager 精简版、核心 types/config
├── prefix_reuse/       # ① 前缀复用检索与命中
├── kv_runtime/         # ② KV 运行时：池化/分层/迁移/碎片/配额 + backend 扩展
├── kv_policy/          # ③ KV 策略：生命周期预测、置换、迁移、收益-代价
├── scheduler_ir/       # ④ Prefill/Decode 解耦执行图 IR + 调度策略/API
├── comm_backend/       # ⑤ 通信后端：拓扑、融合、重叠、跨节点 KV/状态通路
├── accel/              # ⑥ 加速：量化/稀疏/投机解码/CoT 加速控制器
├── engines/            # 引擎深度集成（默认 LMDeploy，选配 vLLM）
├── third_party/        # vendor 引擎源码 + patches
└── benchmarks/         # 统一 benchmark 与 CI perf gate
```

## 模块边界与接口（概要）

- **prefix_reuse**: `PrefixReuseIndex`, `PrefixMatcher`，命中统计 `PrefixReuseMetrics`。
- **kv_runtime**: `KVPool`, `BlockManager`, `HierarchyManager`, `KVMigrator`, `QuotaManager`，backend
  协议：`KVBackendProtocol`；实现：`lmdeploy_backend`, 可选 `vllm_backend`。
- **kv_policy**: `EvictionPolicy` (LRU/LFU/ARC/S3FIFO), `MigrationPolicy`, `CostBenefitModel`,
  `LifetimePredictor`。
- **scheduler_ir**: IR
  定义(`IRNode/IRGraph`)、构建(`IRBuilder`)、优化(`IROptimizer`)、执行计划(`ExecutionPlan`)、执行器
  API(`ExecutorAPI`)、PD 解耦(`PDSeparator`)、策略迁移（fifo/priority/slo_aware/adaptive/aegaeon/hybrid）。
- **comm_backend**: `CommBackendProtocol` (NCCL/Gloo/RDMA
  占位)、`TopologyManager`、`CommFusion`、`OverlapWindow`、`KVTransferChannel`、可选
  `mooncake_integration`（PD 分离通信路径）。
- **accel**: `AccelController`，量化(AWQ/GPTQ/FP8)、稀疏(Sparse
  Attention)、投机解码(Draft/Verifier/CoTAccelController)。
- **engines**: `BaseEngine`；`engines/lmdeploy/` 深度扩展 TurboMind：
  - `engine.py`：封装入口，注入 prefix_reuse/kv_policy/scheduler_ir/comm/accel
  - `kv_manager.py`：扩展 SequenceManager API（前缀 hook、淘汰/迁移 hook）
  - `scheduler.py`：允许外部调度决策/IR 注入
  - `kernels/prefix_aware_attention.py`：可选自定义 kernel

## 引擎集成方案（LMDeploy）

- **Vendor**：`third_party/lmdeploy` 作为 submodule（锁定 v0.11.0，Apache-2.0）。
- **Patches**（存于 `third_party/patches/lmdeploy/` 并用 `apply_patches.sh` 应用）：
  - `0001-extend-kv-manager-api.patch`：SequenceManager 增加
    `get_block_info()`、`register_eviction_callback()`、`migrate_blocks()`
  - `0002-add-prefix-reuse-hooks.patch`：在 `fetch()`/`store()` 前后加入前缀查找与更新钩子
  - `0003-scheduler-ir-integration.patch`：Scheduler 支持外部 IR/决策注入
  - `0004-comm-backend-hooks.patch`：NCCL 调用前后拦截，支持通信融合/统计

## 调度与数据流（文字架构图）

```
用户请求 → scheduler_ir (策略/IR构建) → engines/lmdeploy (Scheduler 注入) →
    prefix_reuse (命中前缀→复用 KV block) → kv_runtime (池化/分层/迁移) →
    kv_policy (选淘汰/迁移) → comm_backend (TP/PP/跨节点 KV 传输/融合) →
    accel (量化/稀疏/投机解码/CoT) → TurboMind kernel → 返回
```

## PR 切分与优先级

1. **PR1 基础架构与类型** (P0, 2d)
   - 建目录骨架；定义 Protocol/types；添加 `third_party/lmdeploy` submodule。
1. **PR2 prefix_reuse** (P1, 3d)
   - Trie/Radix 索引、匹配校验、metrics、benchmark、tests。
1. **PR3 kv_runtime + lmdeploy_backend** (P1, 5d)
   - KVPool/BlockManager/Hierarchy/Migrator/Quota/Defrag；LMDeploy backend；bench+tests。
1. **PR4 kv_policy** (P1, 4d)
   - 淘汰/迁移策略、收益-代价模型、生命周期预测；bench+tests。
1. **PR5 scheduler_ir** (P0, 5d)
   - IR/Builder/Optimizer/ExecutorAPI/PD 分离；迁移现有策略；bench+tests。
1. **PR6 comm_backend** (P1, 4d)
   - NCCL/Gloo 协议、拓扑、融合、重叠、KV transfer、Mooncake 集成占位；bench+tests。
1. **PR7 accel** (P2, 5d)
   - AccelController，量化/稀疏/投机解码/CoT；bench+tests。
1. **PR8 engines/lmdeploy + patches** (P0, 5d)
   - `engine.py`/`kv_manager.py`/`scheduler.py`/kernels；补丁落地；最小可运行 demo；tests。
1. **PR9 benchmarks + CI perf gate** (P1, 3d)
   - 统一 benchmark runner + `ci_gate.py`；workflow：perf regression gate（MFU/TTFT/TPOT/KV hit/通信占比/单位
     token 成本）。

## README 模板（各模块）

- 说明要解决的问题与局限
- 快速开始（依赖安装 + 最小 Demo）
- 如何运行测试/benchmark
- 关键指标表（目标值）
- 接口文档引用 `__init__.py` + docstring

## 关键交互点（对引擎需要的 Hook）

- prefix_reuse: `SequenceManager.fetch/store` 前后钩子，token hash → KV block 映射
- kv_runtime: 块分配/释放/迁移 API；碎片/利用率查询
- kv_policy: 淘汰候选选择、迁移触发回调
- scheduler_ir: 请求队列、调度决策下发（持久化/即时）
- comm_backend: TP/PP 通信拦截、KV 传输带宽/拓扑感知
- accel: Kernel 调用路径、量化权重加载、投机解码入口

## 删除与迁移

- 删除 legacy/ 及 compat 层；不做向后兼容。
- 迁移/拆分旧文件：
  - `control_plane/strategies/*` → `scheduler_ir/strategies/`
  - `pd_routing.py` → `scheduler_ir/pd_separation.py`
  - `parallelism.py` → `scheduler_ir/`
  - `topology.py` → `comm_backend/`
  - `router.py` → 融入 scheduler_ir（路由决策）
  - `engine_lifecycle.py` → `engines/`
  - `executors/http_client.py` → 引擎层替代；`embedding_executor` 可留在 core/ 或拆分

## 验收指标（Perf Gate 建议）

- MFU ≥ 基线 -1%
- TTFT p50/p95 不回退 >5%
- TPOT p50/p95 不回退 >5%
- KV hit rate 提升可观（场景自定义）
- 通信占比（step time 中通信）下降或持平
- 单位 token 成本（GPU·s/token 或 ￥/token）不劣于基线

## 后续优先起步建议

- 先落地 **PR1 + PR8**：骨架 + LMDeploy 深度集成/补丁，跑通最小 demo
- 再补 **PR5**：scheduler_ir，使策略/IR 真正可插拔
- 然后并行推进 prefix_reuse / kv_runtime / kv_policy / comm_backend / accel
- 最后上 perf gate（PR9）

## 详细模块说明（目标 / 接口 / 数据结构 / 指标 / 测试）

### core

- 目标：最小协调层（配置、事件循环、实例注册、健康检查入口），不再承载策略/路由/执行器复杂逻辑。
- 接口：`ControlPlaneManager`（精简）、`BaseService` 适配；config 结构化（pydantic/dataclass）。
- 数据结构：EngineInfo、RequestMetadata（去除与 KV 绑定的字段，转交 kv_runtime）。
- 指标：manager 启动/停止耗时、实例注册耗时、健康检查成功率。
- 测试：unit（配置加载、事件循环生命周期）、integration（带 engines/lmdeploy 最小 demo）。

### prefix_reuse

- 目标：可插拔前缀索引 + 校验，支持最长匹配/多命中策略，命中回填 KV block。
- 接口：`PrefixReuseIndex.insert/lookup/invalidate/evict_lru`，`PrefixMatcher.verify`。
- 数据结构：`PrefixEntry{entry_id, token_hash, token_length, kv_block_ids, metadata}`，`PrefixHit{matched_length, confidence, remaining_tokens}`。
- 指标：命中率、平均匹配长度、lookup p50/p99、冲突率。
- 测试：
  - unit：插入/查找/淘汰/校验；哈希冲突覆盖；空/短/超长输入；并发安全（锁或无锁实现）。
  - integration：与 `kv_runtime`/`engines.lmdeploy` 联动的前缀复用路径。
- Benchmark：批量构造可复用/不可复用请求，测 lookup/命中收益；输出 CSV/JSON。

### kv_runtime

- 目标：统一 KV 池化/分层/迁移/碎片控制/配额；后端抽象可换 LMDeploy/vLLM/Mock。
- 接口：`KVPool.allocate/free/get_utilization/get_fragmentation`; `HierarchyManager`（tier:
  gpu/cpu/nvme）；`KVMigrator.migrate(plan)`；`QuotaManager`。
- 数据结构：`KVBlockInfo{block_id, tier, size_bytes, tenant_id, last_access}`，`MigrationPlan{src_tier, dst_tier, block_ids}`，`AllocationResult{block_ids, tier}`。
- 指标：池利用率、碎片率、分配/释放/迁移延迟、迁移带宽、配额违例数。
- 测试：
  - unit：分配/释放/碎片整理/配额限制/分层迁移（mock 后端）。
  - integration：LMDeploy backend 实际分配；与 kv_policy 结合的淘汰路径。
- Benchmark：可配置请求分布、长短混合、跨层迁移；输出吞吐/延迟/带宽。

### kv_policy

- 目标：策略与运行时解耦，可热插拔；支持多策略对比与收益-代价模型。
- 接口：`EvictionPolicy.select_victims`，`MigrationPolicy.plan`，`CostBenefitModel.evaluate_migration`，`LifetimePredictor.predict_ttl`。
- 数据结构：`PolicyContext{pool_stats, tenant_stats, access_history}`，`EvictionDecision{victims, reason}`，`MigrationDecision{plan, net_benefit}`。
- 指标：命中率变化、淘汰误杀率、决策延迟、收益-代价准确度。
- 测试：策略单测（LRU/LFU/ARC/S3FIFO），成本模型打桩，生命周期预测基准。
- Benchmark：回放 trace，对比策略结果与基线；输出命中率/延迟/成本。

### scheduler_ir

- 目标：把策略输出转成可执行 IR，支持 Prefill/Decode 解耦、算子融合、并行策略选择。
- 接口：`IRBuilder.build(requests)`，`IRGraph.optimize()`，`ExecutorAPI.submit_plan/ cancel /status`，`PDSeparator.split`。
- 数据结构：`IRNode{node_type, inputs, outputs, config, device}`，`ExecutionPlan{plan_id, ir_graph, request_ids, target_instance_id}`。
- 指标：IR 构建时间、优化时间、计划执行成功率、策略决策命中率（与期望资源匹配度）。
- 测试：
  - unit：IR 拓扑排序、循环检测、算子融合规则、PD 分离边界条件。
  - integration：与 engines.lmdeploy 联动，验证计划执行路径。
- Benchmark：多策略对比（fifo/priority/slo_aware/adaptive/aegaeon/hybrid），测队列延迟/吞吐。

### comm_backend

- 目标：通信后端抽象，支持拓扑感知、通信融合、计算通信重叠、KV 传输。
- 接口：`CommBackendProtocol.{all_reduce, all_gather, send, recv}`，`TopologyManager.detect_nvlink/numa`，`KVTransferChannel.transfer`。
- 数据结构：`CommConfig{world_size, rank, backend}`，`TopologyInfo{nvlink, numa}`，`TransferPlan{source, target, block_ids, total_bytes}`。
- 指标：带宽利用率、重叠效率、传输 p50/p99、拓扑探测耗时。
- 测试：mock/nccl 双路径；拓扑解析；KV 传输打桩；Mooncake 集成占位。
- Benchmark：合成张量 all_reduce/all_gather；KV 大块/小块传输；输出带宽/延迟曲线。

### accel

- 目标：统一加速控制（量化/稀疏/投机解码/CoT），可选择性启用。
- 接口：`AccelController.setup/get_quantized_model/run_speculative_decode`；量化器接口
  `BaseQuantizer.quantize`；投机
  `DraftModel.generate_draft`，`Verifier.verify`，`CoTAccelController.accelerate_cot`。
- 数据结构：`AccelConfig{enable_quantization, method, enable_sparsity, speculative_tokens, draft_model}`，`CoTStep{draft_tokens, verification_result, corrections}`。
- 指标：加速比、精度回退、接受率（speculative）、CoT 延迟下降、显存占用下降。
- 测试：量化数值对齐（AWQ/GPTQ/FP8）、稀疏路径、speculative 接受率边界、CoT 多步回退。
- Benchmark：对照 FP16 基线，测吞吐/TTFT/精度；输出表格与 JSON。

### engines（LMDeploy 深度集成）

- 目标：在 TurboMind 上插入前缀复用、KV 策略、IR 调度、通信钩子、加速控制。
- 关键文件：
  - `engine.py`：封装入口，注入各研究模块，暴露 generate/chat/embed。
  - `kv_manager.py`：Monkey-patch SequenceManager：prefix 查找/更新、淘汰回调、迁移接口。
  - `scheduler.py`：允许外部 IR/策略决策下发到 TurboMind 调度。
  - `kernels/prefix_aware_attention.py`：可选自定义 kernel（前缀命中路径优化）。
- 指标：与纯 LMDeploy 基线对比：TTFT/TPOT/MFU/吞吐/KV hit/通信占比。
- 测试：最小 demo（单卡）、多卡 TP 模式、与 scheduler_ir/kv_runtime 联调。

### third_party（vendor + patches）

- Submodule：`third_party/lmdeploy`（锁定 tag v0.11.0，Apache-2.0）。
- Patches：存于 `third_party/patches/lmdeploy/`，用 `apply_patches.sh` 顺序应用。
- 版本管理：`third_party/lmdeploy/VERSION` 记录 tag/commit；补丁编号与说明写入 `patches/README.md`。

### benchmarks

- 目标：统一跑 MFU/TTFT/TPOT/KV hit/通信占比/单位 token 成本；接入 CI perf gate。
- 接口：`BenchmarkRunner.run(config)`，`ci_gate.py` 解析基线与阈值。
- 配置：`benchmarks/configs/*.yaml`（模型、批大小、并发、KV 复用率、通信拓扑）。
- 输出：JSON + Markdown 报告；可选生成图表（matplotlib）。

## 引擎补丁明细（按顺序应用）

1. `0001-extend-kv-manager-api.patch`

   - SequenceManager: `get_block_info()`, `register_eviction_callback(cb)`, `migrate_blocks(plan)`
   - 目的：暴露块元数据、支持外部策略触发迁移。

1. `0002-add-prefix-reuse-hooks.patch`

   - 在 `fetch()` 前调用 prefix lookup；在 `store()` 后更新索引。
   - 目的：前缀命中时复用 KV block，减少 prefill。

1. `0003-scheduler-ir-integration.patch`

   - Scheduler 支持外部决策/IR；添加决策回调接口。
   - 目的：让 scheduler_ir 将计划直接下发引擎。

1. `0004-comm-backend-hooks.patch`

   - NCCL 调用前后插入钩子，收集带宽/时延；可注入通信融合策略。
   - 目的：comm_backend 可观测可控。

## 迁移清单（旧 → 新）

- 策略：`control_plane/strategies/*` → `scheduler_ir/strategies/`
- PD 路由：`pd_routing.py` → `scheduler_ir/pd_separation.py`
- 并行：`parallelism.py` → `scheduler_ir/`
- 拓扑：`topology.py` → `comm_backend/`
- 路由：`router.py` → scheduler_ir 内部路由决策
- 生命周期：`engine_lifecycle.py` → `engines/`
- 执行器：`executors/http_client.py` → 引擎封装；`embedding_executor` 视需要放 core/ 或独立模块
- 兼容层：legacy/、compat.py 全部删除

## 测试与验证矩阵

- 单测：各模块 tests/ 覆盖核心逻辑；mock 后端；边界与异常路径。
- 集成测：
  - prefix_reuse + kv_runtime + engines.lmdeploy（前缀命中复用）。
  - kv_policy + kv_runtime（淘汰/迁移决策生效）。
  - scheduler_ir + engines.lmdeploy（IR 下发执行）。
  - comm_backend + engines.lmdeploy（多卡 TP 通信钩子）。
  - accel + engines.lmdeploy（量化/投机解码开启）。
- Benchmark：benchmarks/runner.py，标准场景（小模型/中模型/长上下文/高并发）。
- 回归门禁：ci_gate 检查 MFU/TTFT/TPOT/KV hit/通信占比/成本。

## CI 集成步骤（建议）

1. 安装：`./tools/install/ci_install_wrapper.sh --dev --yes`
1. 单测：`pytest packages/sage-common/src/sage/common/components/sage_llm/sageLLM -q`
1. Lint：`sage-dev quality --check-only`
1. Benchmark（可选慢）：`python -m sage.common.components.sage_llm.sageLLM.benchmarks.runner --preset ci`
1. Perf
   gate：`python -m sage.common.components.sage_llm.sageLLM.benchmarks.ci_gate --baseline baseline.json --current output.json`

## 时间线与里程碑（参考）

- Week 1: PR1 (骨架+类型) + PR8 (LMDeploy 集成/补丁)，跑通最小 demo。
- Week 2: PR5 (scheduler_ir) 完成迁移与可插拔策略。
- Week 3: PR2/PR3 并行（prefix_reuse, kv_runtime）。
- Week 4: PR4/PR6（kv_policy, comm_backend）。
- Week 5: PR7（accel）+ PR9（perf gate）。

## 风险与应对

- Submodule 同步风险：锁版本 + patches；`apply_patches.sh` 持续验证。
- Kernel 兼容性：prefix_aware_attention 可选编译；默认不启用。
- 多卡通信：提供 mock/nccl 双路径；CI 走 mock，手动验证 nccl。
- 性能回退：perf gate 强制阈值；基线版本需固化。
- 维护成本：模块 README + 接口稳定；公共 Protocol 避免破坏性修改。
