# Prompt · Phase 0 / PR1+PR8：骨架、协议、LMDeploy 集成管线

你是负责 **sageLLM 模块化重构** 的首席工程师。请基于下述最新架构与交付要求，给出可直接指导落地的方案，交付物将作为后续所有课题的基座。

______________________________________________________________________

## 背景与目标

- 目标：完成 PR1（目录骨架+Protocol/types）与 PR8（LMDeploy submodule + patches + 最小可运行 demo），为
  prefix_reuse/kv_runtime/kv_policy/scheduler_ir/comm_backend/accel 提供稳定契约。
- 重点：**彻底去掉 legacy/compat**，用统一协议与目录替代旧的 `sage_infer/`、`pd_routing.py`、`transport/` 等路径。
- 交付：1) 目录骨架；2) Protocol/types/schema；3) LMDeploy submodule + 补丁管线；4) 最小 demo；5) README/CLI/配置入口。

______________________________________________________________________

## 研究内容（Scope）

1. **目录与协议落地**

- 创建以下目录（硬约束）：`core/`, `prefix_reuse/`, `kv_runtime/`, `kv_policy/`, `scheduler_ir/`,
  `comm_backend/`, `accel/`, `engines/`, `third_party/`, `benchmarks/`。
- 定义共用协议：`KVCacheSchema`, `CapabilityDescriptor`, `QuantizationProfile`, `KVBackendProtocol`,
  `CommBackendProtocol`, `AccelConfig`, `ExecutionPlan/IRNode/IRGraph` 关键类型。

2. **Control Plane 精简版 (core/)**

- 精简 `ControlPlaneManager`：实例注册、事件循环、健康检查、配置加载（pydantic/dataclass）。
- 数据结构：`EngineInfo`, `RequestMetadata`（KV 字段移交 kv_runtime）。

3. **LMDeploy 深度集成管线 (engines/ + third_party/)**

- 引入 `third_party/lmdeploy` submodule（tag v0.11.0，Apache-2.0），禁止 `git submodule update --init`，使用
  `tools/maintenance/sage-maintenance.sh` / `apply_patches.sh`。
- 补丁顺序（存 `third_party/patches/lmdeploy/`）：
  - `0001-extend-kv-manager-api.patch`（get_block_info/eviction_cb/migrate_blocks）
  - `0002-add-prefix-reuse-hooks.patch`（fetch/store 前后钩子）
  - `0003-scheduler-ir-integration.patch`（外部 IR/决策注入）
  - `0004-comm-backend-hooks.patch`（通信拦截/统计/融合入口）
- `engines/lmdeploy/`: `engine.py`（封装入口+依赖注入），`kv_manager.py`（SequenceManager
  扩展），`scheduler.py`（IR/策略下发），`kernels/prefix_aware_attention.py`（可选）。

4. **最小可运行 Demo**

- 路径：`tests` 或 `examples` 下提供最小
  demo：`ControlPlaneManager → scheduler_ir stub → engines.lmdeploy (patched) → generate/chat`；验证
  TTFT/TPOT 无回退（±3%）。
- CLI：`sage llm serve --engine lmdeploy --model <id>` 走新入口；`sage gateway start` 正常代理。

5. **配置与 CLI**

- CLI 入口：`sage infer` 命名空间，含 `backend list/test`, `schema dump`, `apply-patches`（可选）。
- 配置：`config/sage_llm.yaml`（engine, patches, kv_schema, comm preset, accel preset），统一使用 `SagePorts`
  取端口。

______________________________________________________________________

## 模块设计与目录（硬约束）

```
packages/sage-common/src/sage/common/components/sage_llm/sageLLM/
├── core/                # ControlPlaneManager 精简版、types/config
├── prefix_reuse/        # PR2：PrefixReuseIndex/Matcher/Metrics
├── kv_runtime/          # PR3：KVPool/Hierarchy/Migrator/Quota + KVBackendProtocol
├── kv_policy/           # PR4：Eviction/Migration/CostBenefit/LifetimePredictor
├── scheduler_ir/        # PR5：IRNode/IRGraph/IRBuilder/IROptimizer/PDSeparator/ExecutorAPI
├── comm_backend/        # PR6：CommBackendProtocol/TopologyManager/CommFusion/Overlap/KVTransfer
├── accel/               # PR7：AccelController + quant/sparse/spec-decoding/CoT
├── engines/             # PR8：LMDeploy 深度改造（engine/kv_manager/scheduler/kernels）
├── third_party/         # LMDeploy submodule + patches + apply_patches.sh
└── benchmarks/          # PR9：runner + ci_gate（MFU/TTFT/TPOT/KV hit/通信占比/成本）
```

______________________________________________________________________

## 交付要求

- **接口/协议**：提供上述 Protocol/dataclass，文档化字段含义；路径即最终位置。
- **Submodule & Patches**：`third_party/lmdeploy` 已锁版本；`apply_patches.sh` 支持幂等；`VERSION` 记录
  tag/commit；`patches/README.md` 说明补丁目的。
- **Demo & Tests**：最小 demo 可运行；单测覆盖协议序列化/配置加载；集成测验证 patched LMDeploy 正常工作。
- **文档**：各模块 README 按模板（问题/局限、快速开始、测试/bench、指标表、接口引用）；本 prompt 不再引用外部 plan。

______________________________________________________________________

## Success Criteria

- 目录与协议一次到位；禁止再引入 legacy/compat 路径。
- 补丁应用后 LMDeploy 正常：TTFT/TPOT 与 baseline 回退 \<3%，功能等价。
- CLI/配置可列出 backend、dump schema、展示补丁状态。
- 后续课题可直接依赖协议，无额外 breaking change。

______________________________________________________________________

## 交付物清单

1. 目录骨架 + 协议/types 代码。
1. `third_party/lmdeploy` submodule + `patches/0001-0004` + `apply_patches.sh` + `VERSION`。
1. 最小 demo + 基础单测/集成测。
1. README（core/engines/third_party/benchmarks 各一份）+ CLI 用法。
1. CI
   提示：`pytest packages/sage-common/src/sage/common/components/sage_llm/sageLLM -q`，`sage-dev quality --check-only`。

````

### 与 Control Plane 集成

```python
# Control Plane 根据 HybridCapabilityDescriptor 做智能调度
capability = backend.get_hybrid_capability()

# 调度决策考虑因素：
# 1. 请求类型 → 路由到对应模型
# 2. 各模型当前负载 → 负载均衡
# 3. GPU 显存使用率 → 避免 OOM
# 4. 请求优先级和 SLO → 优先级调度
# 5. RAG 场景 → Embedding + LLM 联合调度
````

### 交互示例

1. `sage llm serve --backend vllm --kv-schema preset=fp8` → CLI 读取 Phase 0 定义的 Schema。
1. `sageLLM Control Plane` 调用 `backend.get_capability()`，根据 `instance_type` 和 `kv_schema` 进行 PD/AF
   调度。
1. 课题一实现的 `TransportEngine` 使用 Phase 0 的 `KVChunk`，无需关心调度细节。
1. 课题三产出的 `QuantizationProfile` 能被任意 InferenceBackend 加载。
1. **混合部署**：`sage infer serve --llm qwen-7b --embedding bge-m3 --sharing time_slice` 启动混合推理服务。

______________________________________________________________________

## 研究目标（Success Criteria）

### 技术指标

| 指标                      | 目标                                                    |
| ------------------------- | ------------------------------------------------------- |
| InferenceBackend 接口实现 | 能驱动 vLLM 正常推理，无性能回退 (±3%)                  |
| 接口文档                  | 覆盖 KV Schema、Capability、Transport 契约              |
| CLI 兼容性                | `sage llm serve` 支持 `--backend`、`--kv-schema` 新参数 |
| 测试覆盖                  | 新增接口的单元测试/契约测试 ≥80% 覆盖                   |
| 课题依赖                  | 三个课题均引用 Phase 0 提供的接口，无自定义重复定义     |

### 工程化指标

1. **设计文档**：位于 `docs/dev-notes/.../task0-common-infrastructure/README.md`，描述接口、调用链、演进路线。
1. **代码实现**：`InferenceBackend` 抽象、`VLLMBackendAdapter`、CLI 扩展、示例配置。
1. **测试脚本**：最小端到端用例（Control Plane → Backend Adapter → vLLM）。
1. **并行指引**：在 meta prompt 中附 Phase 0 完成标准及课题间依赖说明。

______________________________________________________________________

## 交付物要求

1. `prompt.md`（本文档）
1. `README.md`：Phase 0 设计说明、接口详解、依赖图
1. `interfaces/*.py`：接口与数据结构实现
1. `backends/vllm_adapter.py`：vLLM 适配器 + 单元测试
1. `cli/commands.py`：`sage infer` 命令实现
1. `examples/phase0_demo.py`：驱动 Control Plane 的示例
1. CI Hook：在 `sage-dev project test` 中加入 Phase 0 契约测试

______________________________________________________________________

请在方案中明确：接口契约、演进路线、向下兼容策略、以及各课题如何复用这些成果。Phase 0 完成后，再进入课题一/二/三的正式实现，以降低重复建设与后期重构成本。
