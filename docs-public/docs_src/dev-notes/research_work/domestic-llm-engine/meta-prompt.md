# Meta Prompt：sageLLM 模块化重构（LMDeploy 深度集成版）

> 用途：为各个课题 prompt 提供统一的背景、目标、目录与接口约束，确保和最新的 `sageLLM_refactor_plan.md` 保持一致，可直接指挥 Agents
> 产出符合落地要求的设计与实现方案。

______________________________________________________________________

## 全局定位与目标

- 目标：在 SAGE 中完成 **sageLLM 模块化重构 + LMDeploy/TurboMind 深度集成**，删除 legacy 兼容层，让 6 个研究方向可独立演进。
- 关键收益：保持/提升 MFU/TTFT/TPOT，不引入性能回退；提供可观测、可插拔的 Control Plane + Engine 架构。
- 支持硬件：CUDA GPU + 国产算力（昇腾/寒武纪/海光/昆仑等），通信/调度/量化路径均需留出适配钩子。

______________________________________________________________________

## 目标目录（硬约束）

所有新模块放在 `packages/sage-common/src/sage/common/components/sage_llm/sageLLM/` 下，严禁向上依赖（遵循 L1-L6
分层）。目录骨架：

```
sageLLM/
├── core/               # 精简 ControlPlaneManager + types/config
├── prefix_reuse/       # 前缀复用检索与命中
├── kv_runtime/         # KV 运行时：池化/分层/迁移/碎片/配额 + backend 协议
├── kv_policy/          # KV 策略：生命周期预测、置换/迁移、收益-代价
├── scheduler_ir/       # Prefill/Decode 解耦执行图 IR + 策略/API
├── comm_backend/       # 通信后端：拓扑、融合、重叠、KV 传输
├── accel/              # 加速：量化/稀疏/投机解码/CoT 控制器
├── engines/            # 引擎集成（默认 LMDeploy，选配 vLLM）
├── third_party/        # vendor 引擎源码 + patches（LMDeploy v0.11.0）
└── benchmarks/         # 统一 benchmark 与 CI perf gate
```

> 所有 prompt 必须引用此目录与模块名，**禁止再使用旧的 `sage_infer/`、`transport/`、`pd_routing.py` 等路径**，并写清楚拆分/迁移关系。

______________________________________________________________________

## PR 切分（必须保留）

1. **PR1 基础架构与类型（P0）**：目录骨架、Protocol/types、`third_party/lmdeploy` submodule 占位。
1. **PR2 prefix_reuse（P1）**：Trie/Radix 索引、匹配校验、metrics、bench/tests。
1. **PR3 kv_runtime +
   lmdeploy_backend（P1）**：KVPool/BlockManager/Hierarchy/Migrator/Quota/Defrag；LMDeploy
   backend；bench+tests。
1. **PR4 kv_policy（P1）**：淘汰/迁移策略、收益-代价模型、生命周期预测；bench+tests。
1. **PR5 scheduler_ir（P0）**：IR/Builder/Optimizer/ExecutorAPI/PD 分离；迁移现有策略；bench+tests。
1. **PR6 comm_backend（P1）**：NCCL/Gloo 协议、拓扑、融合、重叠、KV transfer、Mooncake 占位；bench+tests。
1. **PR7 accel（P2）**：量化/稀疏/投机解码/CoT；bench+tests。
1. **PR8 engines/lmdeploy + patches（P0）**：`engine.py`/`kv_manager.py`/`scheduler.py`/kernels；补丁落地；最小
   demo；tests。
1. **PR9 benchmarks + CI perf gate（P1）**：统一 benchmark runner + perf gate（MFU/TTFT/TPOT/KV
   hit/通信占比/单位 token 成本）。

______________________________________________________________________

## 关键 Hook（各课题都要考虑）

- **prefix_reuse**：在 LMDeploy `SequenceManager.fetch/store` 前后查找/更新前缀；暴露命中统计。
- **kv_runtime**：块分配/释放/迁移/碎片查询；`KVBackendProtocol` 实现（默认 lmdeploy_backend）。
- **kv_policy**：驱逐候选、迁移触发回调；收益-代价模型。
- **scheduler_ir**：请求队列、PD 分离、外部 IR/决策注入；策略迁移（fifo/priority/slo_aware/adaptive/aegaeon/hybrid）。
- **comm_backend**：通信拦截、拓扑/融合/重叠、跨节点 KV 传输。
- **accel**：量化/稀疏/投机解码/CoT 控制器；kv_precision 协同。
- **engines**：LMDeploy 深度改造（engine/scheduler/kv_manager/kernels）；patches 下发顺序 0001-0004。

______________________________________________________________________

## 课题映射（对齐新目录）

| Prompt 文件                             | 对应 PR / 模块                                            | 主要交付                                                                 | 特别注意                                                                                                          |
| --------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| `task0-common-infrastructure/prompt.md` | PR1 + PR8 骨架                                            | 目录/Protocol/types + LMDeploy submodule/patch 管线 + 最小 demo          | 禁止旧路径；写清 third_party/lmdeploy 管理、补丁顺序、control_plane 精简版接口                                    |
| `task1-kv-transport/prompt.md`          | PR6 comm_backend                                          | 拓扑/融合/重叠/KV transfer + Mooncake 占位 + telemetry + presets         | 绑定 SagePorts；强调 NCCL/Gloo/mock 双路径；CI 走 mock，GPU 手动验证                                              |
| `task2-kv-cache-scheduling/prompt.md`   | PR2 + PR3 + PR4 （prefix_reuse + kv_runtime + kv_policy） | 前缀索引 + KVPool/Hierarchy/Migration + 策略/收益模型 + bench/tests      | 和 LMDeploy `kv_manager` Hook 对齐；调度接口通过 scheduler_ir，不再写旧 pd_routing                                |
| `task2-pd-separation/prompt.md`         | PR5 scheduler_ir                                          | IR/Builder/Optimizer/ExecutorAPI/PD 分离 + 策略迁移 + 控制面事件循环精简 | 迁移 `control_plane/strategies/*` → `scheduler_ir/strategies/`，`pd_routing.py` → `scheduler_ir/pd_separation.py` |
| `task3-model-compression/prompt.md`     | PR7 accel                                                 | 量化/稀疏/投机解码/CoT 控制器 + QuantizedKV + bench/tests                | 不再单独建 quantization/transport；统一放 `accel/`，并与 `kv_runtime`/`comm_backend` 协同                         |

______________________________________________________________________

## Prompt 结构模板（保持不变）

每个课题的 prompt 需包含：背景、问题、可复用模块、研究内容（分子任务）、模块设计（目录/核心接口）、Success Criteria（性能+工程化）、交付物。路径、接口、指标须使用上表映射与
`sageLLM_refactor_plan.md` 中的术语。

______________________________________________________________________

## 统一指标基线（用于 Success Criteria）

- MFU ≥ 基线 -1%
- TTFT/TPOT p50/p95 回退 \<5%
- KV hit 提升需量化；长上下文（≥32K/64K/128K）稳定运行
- 通信占比下降或持平；单位 token 成本（GPU·s/token 或 ￥/token）不劣于基线
- Bench & CI：`sage.common.components.sage_llm.sageLLM.benchmarks` runner + `ci_gate` perf gate

______________________________________________________________________

## 文档/实现迁移提示

- 删除 legacy/compat 层；旧文件迁移：`control_plane/strategies/*` → `scheduler_ir/strategies/`；`pd_routing.py`
  → `scheduler_ir/pd_separation.py`；`parallelism.py` → `scheduler_ir/`；`topology.py` →
  `comm_backend/`；`router.py` → scheduler_ir；`engine_lifecycle.py` →
  engines；`executors/http_client.py` → 引擎层替代。
- 第三方：`third_party/lmdeploy` (tag v0.11.0, Apache-2.0) + `third_party/patches/lmdeploy/0001-0004`，提供
  `apply_patches.sh`。
- 端口：统一使用 `SagePorts`，禁止硬编码。

______________________________________________________________________

## 交付与验证矩阵

- 单测：各模块 tests/ 覆盖核心逻辑；mock 后端；异常与边界。
- 集成测：prefix_reuse↔kv_runtime↔engines.lmdeploy；kv_policy↔kv_runtime；scheduler_ir↔engines；comm_backend↔engines；accel↔engines。
- Benchmark：长上下文、混合负载、通信吞吐、加速比；输出 JSON/Markdown。
- Perf gate：`ci_gate` 检查 MFU/TTFT/TPOT/KV hit/通信占比/成本。 │ 提供高速 KV 传输 │ KV Cache 量化存储 │
  │◄─────────────────────│◄─────────────────────│ │ │ │
  └──────────────────────┴──────────────────────┘ │ ▼ ┌─────────────────────────────┐ │ sageInfer
  统一推理引擎 │ │ (替代 vLLM 的国产化方案) │ └─────────────────────────────┘

```

### 接口依赖关系
| 消费方 | 依赖的接口/Schema | 提供方 |
|--------|-------------------|--------|
| 课题一 | `KVCacheSchema`, `TransportPlan` | Phase 0 |
| 课题二 | `InferenceBackend`, `CapabilityDescriptor`, `KVCacheSchema` | Phase 0 |
| 课题三 | `QuantizationProfile`, `KVCacheSchema` | Phase 0 |
| 课题二 | `TransportEngine` (Mock → 真实) | 课题一 |
| 课题一/二 | `QuantizationProfile`, KV 压缩格式 | 课题三 |

---

## Agent 任务分配

### Agent 0 - Phase 0 公共基础设施
- 输出文件：`task0-common-infrastructure/prompt.md`
- 重点：vLLM 解耦、InferenceBackend 接口、共享 Schema、HAL 骨架、CLI 扩展
- **优先级：最高（阻塞其他课题）**

### Agent 1 - 课题一 Prompt 撰写
- 输出文件：`task1-kv-transport/prompt.md`
- 重点：传输引擎架构、硬件适配接口、格式转换内核设计
- **前置依赖**：Phase 0 的 `KVCacheSchema`, `TransportPlan`

### Agent 2 - 课题二 Prompt 撰写
- 输出文件：`task2-pd-separation/prompt.md`
- 重点：KV Cache 生命周期管理、与 Control Plane 集成、分层存储策略
- **前置依赖**：Phase 0 的 `InferenceBackend`, `CapabilityDescriptor`

### Agent 3 - 课题三 Prompt 撰写
- 输出文件：`task3-model-compression/prompt.md`
- 重点：量化方案选型、与国产硬件量化加速能力结合、精度保持策略
- **前置依赖**：Phase 0 的 `QuantizationProfile`, `KVCacheSchema`

---

## 参考资源

### SAGE 代码库位置
- sageLLM Control Plane: `packages/sage-common/src/sage/common/components/sage_llm/sageLLM/control_plane/`
- sageInfer (待创建): `packages/sage-common/src/sage/common/components/sage_llm/sageLLM/sage_infer/`
  > 注：`sage_infer` 与 `control_plane` 同级，Control Plane 负责调度，`sage_infer` 负责实际推理执行。

### 相关论文/项目
- vLLM: PagedAttention, Prefix Caching
- SGLang: RadixAttention
- TensorRT-LLM: 量化推理
- FlashAttention: 高效注意力计算
- DistServe/Mooncake: PD 分离

### SAGE 文档
- 架构文档: `docs-public/docs_src/dev-notes/package-architecture.md`
- Copilot 指南: `.github/copilot-instructions.md`
```
