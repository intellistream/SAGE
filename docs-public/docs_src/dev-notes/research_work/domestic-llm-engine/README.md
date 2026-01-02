# 面向国产算力的 sageLLM 模块化重构（提示词合集）

> **状态**：规划中（对齐 `docs/dev-notes/sageLLM_refactor_plan.md`）\
> **项目代号**：SAGE-Domestic-Accelerator\
> **更新时间**：自动随着 prompt 调整

______________________________________________________________________

## 项目概述

依托 SAGE 框架，重构 `sageLLM` 为模块化架构并深度集成 **LMDeploy/TurboMind**。目标是在国产算力和通用 GPU 上提供可插拔的 Control Plane +
Engine 栈，保持或提升 MFU/TTFT/TPOT、长上下文稳定性和单位 token 成本。

**核心目录（新）**

```
packages/sage-common/src/sage/common/components/sage_llm/sageLLM/
├── core/            # 精简 ControlPlaneManager + types/config
├── prefix_reuse/    # 前缀复用索引与校验
├── kv_runtime/      # KV 池化/分层/迁移/碎片/配额 + backend 协议
├── kv_policy/       # 驱逐/迁移策略 + 收益模型
├── scheduler_ir/    # Prefill/Decode 解耦的执行图 IR + 策略/API
├── comm_backend/    # 通信后端：拓扑/融合/重叠/跨节点 KV 传输
├── accel/           # 量化/稀疏/投机解码/CoT 控制器
├── engines/         # 引擎集成（默认 LMDeploy；选配 vLLM）
├── third_party/     # vendor 引擎 + patches（LMDeploy v0.11.0）
└── benchmarks/      # 统一 bench + CI perf gate
```

**关键指标**：MFU ≥ 基线 -1%，TTFT/TPOT 回退 \<5%，KV hit 提升可量化，通信占比下降或持平，单位 token
成本不劣于基线，长上下文（≥32K/64K/128K）稳定。

______________________________________________________________________

## Prompt 导航（已对齐重构计划）

- **[Meta Prompt](./meta-prompt.md)**：全局约束、目录、PR 切分、Hook 清单
- **Phase/PR 切片 Prompts**
  - [task0-common-infrastructure](./task0-common-infrastructure/prompt.md) — PR1 + PR8 骨架、LMDeploy
    submodule/补丁、最小 demo
  - [task1-kv-transport](./task1-kv-transport/prompt.md) — PR6 comm_backend：拓扑/融合/重叠/KV 传输 +
    Mooncake 占位
  - [task2-kv-cache-scheduling](./task2-kv-cache-scheduling/prompt.md) — PR2 + PR3 +
    PR4：prefix_reuse + kv_runtime + kv_policy
  - [task2-pd-separation](./task2-pd-separation/prompt.md) — PR5 scheduler_ir：IR/PD 分离/策略迁移
  - [task3-model-compression](./task3-model-compression/prompt.md) — PR7 accel：量化/稀疏/投机解码/CoT

______________________________________________________________________

## 验收与协作提示

- 端口：统一使用 `SagePorts`，严禁硬编码。
- Submodule：`third_party/lmdeploy`（tag v0.11.0）+ `third_party/patches/lmdeploy/0001-0004`，提供
  `apply_patches.sh`；禁止 `git submodule update --init`。
- 迁移：删除 legacy/compat；旧策略/路由/拓扑文件按 `sageLLM_refactor_plan.md` 指定位置迁移。
- CI/Perf：`benchmarks` runner + `ci_gate` 作为 perf gate；各课题 prompt 均需列明单测/集成测/bench 要求。
