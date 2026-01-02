# Prompt · 课题三 / PR7：accel（量化/稀疏/投机解码/CoT）

你是负责 **accel/** 的架构师。请实现统一加速控制器与执行栈，覆盖量化、稀疏、投机解码、CoT 加速，并与
`kv_runtime`、`scheduler_ir`、`engines.lmdeploy` 协同。

______________________________________________________________________

## 前置依赖

- 协议/类型：`AccelConfig`, `QuantizationProfile`, `CapabilityDescriptor`, `KVCacheSchema`（来自
  PR1）；`KVBackendProtocol`/`CommBackendProtocol` 供协同。
- Hook：LMDeploy patched 允许 kv_precision/投机解码/CoT 控制注入；kv_runtime 可切换 kv 精度；comm_backend 可携带压缩/量化标记。

______________________________________________________________________

## 背景与目标

- 目标：在国产算力与 CUDA 环境实现“可插拔加速层”，提升吞吐/降低成本且精度可控。
- 输出：量化/稀疏/投机解码/CoT 控制器、kernel 适配、配置/CLI、bench + ci gate 接口。

______________________________________________________________________

## 研究内容（Scope）

1. **量化栈**

- 统一 `QuantizationProfile`（weight/activation/kv prefill/kv decode
  位宽、sparsity、calibration、max_seq_len）。
- 算法：GPTQ/AWQ/SmoothQuant；KV on-the-fly 量化；per-channel scale；误差反馈。
- Kernel 适配：CUDA/ASCEND/MLU/HyGON/昆仑；输出 kernel meta。

2. **稀疏与剪枝**

- 结构化 (2:4/4:8/BlockSparse) + 非结构化；Attention/FFN 通路优化。
- Kernel：SparseAttention/SparseMatMul 针对国产硬件；mask/meta 序列化格式。

3. **投机解码 / CoT 加速**

- Draft/Verifier/合并逻辑；CoTAccelController 支持多步校验；接受率、回退策略。

4. **运行时与协同**

- `AccelController.setup/get_quantized_model/run_speculative_decode` 等接口；
- 与 `kv_runtime`：KV 精度切换、quantized KV 存储、收益-代价评估。
- 与 `scheduler_ir`：计划中携带量化/稀疏/投机策略；与 `comm_backend` 协同压缩。

5. **CLI/工具链**

- CLI：`sage infer quantize/prune/distill/run-speculative`；profile 加载/验证；硬件兼容检查。
- 工具：校准、蒸馏、profile 验证；生成可部署工件（权重+scale+mask+meta）。

______________________________________________________________________

## 目录结构（硬约束）

```
accel/
├── __init__.py
├── controller.py         # AccelController
├── config.py             # AccelConfig/QuantizationProfile re-export
├── quantization/
│   ├── __init__.py
│   ├── weight_quant.py
│   ├── activation_quant.py
│   ├── kv_quant.py
│   ├── calibration.py
│   └── kernels/
├── sparsity/
│   ├── __init__.py
│   ├── structured.py
│   ├── unstructured.py
│   └── kernels/
├── speculative/
│   ├── __init__.py
│   ├── draft.py
│   ├── verifier.py
│   └── cot_controller.py
├── runtime/
│   ├── quant_backend.py
│   ├── mixed_precision.py
│   └── loaders.py
└── tools/
    ├── distillation/
    ├── presets.py
    └── cli.py
```

______________________________________________________________________

## Success Criteria

- 性能：吞吐 ≥ vLLM baseline 200%；TTFT/TPOT 下降 ≥20%；Prefill 显存 -40%，Decode 显存 -30%；长上下文错误率 \<1%，吞吐波动
  \<10%。
- 工程化：
  - CLI 完成 quantize/prune/distill/speculative；生成可部署工件；兼容检查。
  - ≥4 款国产硬件端到端 demo（kernel+runtime+bench）。
  - 调度日志包含量化/稀疏标签；scheduler_ir 可按标签路由。
  - Studio/Gateway 成本面板可对比 baseline vs 压缩配置。
- 可观测：暴露吞吐/延迟/成本/精度/接受率/回退指标；纳入 perf gate。

______________________________________________________________________

## 交付物

1. 设计文档：量化/稀疏/投机/CoT 架构、硬件适配、KV 协同、指标与风险。
1. 核心代码：`accel/` 全量实现 + kernel 适配 + CLI/工具。
1. 测试：单测（量化/稀疏/投机核心逻辑），集成测（LMDeploy patched + kv_runtime + scheduler_ir），精度回归。
1. Benchmark：吞吐/TTFT/TPOT/显存/精度/成本，对比 FP16 baseline；输出 JSON/Markdown。
