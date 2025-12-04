# Prompt · 课题三：模型压缩 / 推理执行引擎量化

你是一名负责 **sageInfer** 推理引擎量化与稀疏加速的系统架构师，请依据以下背景与要求，输出详细的技术方案、模块设计和实验路线，确保压缩技术在 **sageLLM + sageInfer** 推理栈中落地。

---

## 前置依赖（Prerequisites）

> ⚠️ 本课题依赖 **Phase 0 公共基础设施**，请确保以下接口已定义并可用：

| 依赖项 | 来源 | 用途 |
|--------|------|------|
| `QuantizationProfile` | `sageInfer/interfaces/schemas.py` | 量化配置描述（位宽、校准集等） |
| `KVCacheSchema` | `sageInfer/interfaces/schemas.py` | KV 数据格式，与课题二共定 |
| `CapabilityDescriptor` | `sageInfer/interfaces/schemas.py` | 实例能力上报（含量化/稀疏能力） |
| `AcceleratorDescriptor` | `sageInfer/hal/accelerator_descriptor.py` | 硬件量化/稀疏加速能力查询 |

### 与其他课题的关系
- **与课题一协同**：量化后的 KV Cache 需要格式转换，复用课题一的 `format.converter`
- **与课题二协同**：KV Cache 量化精度策略需要与课题二的分层缓存联动
- **相对独立**：量化工具链（离线部分）可独立开发，不强依赖在线调度

### 并行开发策略
1. **Phase 1 可并行**：离线量化工具链（GPTQ/AWQ/校准）不依赖在线系统
2. **Phase 2 集成**：在线推理（QuantizedAttentionBackend）需要 InferenceBackend 接口
3. **与课题二同步**：KV Cache 量化格式需要双方共同定义

---

## 背景（Background）

### 项目定位
- **架构位置**：课题三负责 `sageInfer/quantization/` 与 `sageInfer/pruning/` 核心模块，并向 `sageLLM` 控制平面和 `sage-gateway/sage-cli` 提供推理配置、校准与指标接口。
- **与其他课题关系**：
  - 产出的量化/稀疏模型需要在课题一的高速通信链路中传输，并与课题二的 KV Cache 管理共享统一格式。
  - 本课题聚焦“模型层面压缩 + 推理内核适配”，让 sageInfer 运行时原生理解国产硬件的 INT4/FP8 张量核、稀疏执行单元、KV Cache 压缩能力。

### 问题背景
- 现有 vLLM 面向 NVIDIA CUDA 设计，国产硬件（昇腾/寒武纪/昆仑/海光）缺乏原生量化算子与稀疏 kernel 支撑，压缩模型无法高效运行。
- 项目总体目标：单芯片有效算力 ≥90% 峰值、吞吐≥ vLLM 的 2×、TTFT/TPOT 至少提升 20%、单位 token 成本下降 ≥30%、在 ≥32K 上下文稳定运行。
- 需要“一体化量化栈”：既产出高质量压缩模型，又驱动 sageInfer 的注意力后端、KV Cache、通信管线按压缩格式运作。

### 现有技术基础
- `sageLLM/control_plane` 已具备调度/PD 分离能力，可根据实例能力标签进行路由。
- `sage.common.components.sage_llm.service` 提供 vLLM 封装，可作为兼容层。
- 可复用：SAGE model registry、`sage-benchmark`、CLI/Studio 观测体系。

---

## 研究内容（Research Scope）

### 1. 量化执行栈（`sageInfer/quantization/`）
- 统一 `QuantizationProfile` 描述权重/激活/KV Cache/注意力分块的位宽与范围，支持 INT8/INT4/FP8 混合策略。
- 实现 GPTQ、AWQ、SmoothQuant 等权重量化，激活校准、KV Cache on-the-fly 量化，并映射到昇腾 CANN、寒武纪 Neuware、海光 ROCm/xGMI、昆仑 XPU 的张量核。
- 提供 CLI：`sage infer quantize --profile profile.yaml`，生成 sageInfer 可直接加载的压缩工件（权重、scale map、kernel meta）。

### 2. 稀疏化与结构化剪枝（`sageInfer/pruning/`）
- 支持 2:4 / 4:8 结构化稀疏、Attention head/FFN channel 剪枝、BlockSparse（64×64 等）策略。
- 针对国产硬件稀疏核心（昇腾 SparseTensorCore、寒武纪 Sparse GEMM 等）实现 `SparseAttentionKernel`、`SparseMatMulKernel`。
- 定义稀疏掩码 + kernel meta 文件格式，使 sageLLM 控制平面可感知“稀疏能力”并调度合适实例。

### 3. KV Cache 量化协同
- 与课题二共定 KV Cache 压缩格式（FP8/INT4 分块、动态范围表、分页化 scale）。
- 在 sageInfer 注意力后端内实现 `QuantizedKVStore`，Prefill/Decode 可用不同精度，支持跨批/热点复用。
- 定义 `kv_quant_schema` 上报接口，让 sageLLM 按链路带宽、显存压力自适应选择精度。

### 4. 蒸馏与精度守护
- 在 `sageInfer/tools/distillation/` 提供 `DistillationPreset`（response/layer/self），保障压缩模型精度。
- 构建自动评估：perplexity、MMLU、RAG、LongBench、长上下文稳定性；限定精度退化 ≤5%。
- CLI/Studio 成本面板实时展示“吞吐/延迟/成本/精度”四维对比。

### 5. 推理运行时集成
- 在 sageInfer Runtime 中实现 `QuantizedAttentionBackend`、`MixedPrecisionExecutor`，根据 profile 调度 kernel、管理 scale 与缓存。
- 向 `sageLLM Control Plane` 上报 `CapabilityDescriptor`（位宽、稀疏度、KV schema、推荐 batch 上限、吞吐/TTFT 估计），供 PD 分离与自适应策略使用。

---

## 模块设计（Module Design）

### 目录结构建议
```
sageInfer/
├── quantization/
│   ├── __init__.py
│   ├── profiles.py          # QuantizationProfile/Capability 定义
│   ├── weight_quant.py      # GPTQ/AWQ/FP8 权重量化
│   ├── activation_quant.py  # 激活 & 动态范围统计
│   ├── kv_quant.py          # KV Cache 压缩/解压
│   ├── calibration.py       # 校准数据管线
│   └── kernels/
│       ├── ascend_fp8_kernel.cc
│       ├── cambricon_int4_kernel.cc
│       ├── hygon_sparse_kernel.cc
│       └── ...
├── pruning/
│   ├── __init__.py
│   ├── structured.py        # 2:4 / block 稀疏
│   ├── unstructured.py      # movement/magnitude
│   ├── mask_serializer.py   # kernel meta 输出
│   └── kernels/
├── runtime/
│   ├── quant_backend.py     # QuantizedAttentionBackend
│   ├── kv_store.py          # QuantizedKVStore
│   ├── capability.py        # CapabilityDescriptor
│   └── loaders.py           # 压缩模型加载/校验
└── tools/
    ├── distillation/
    │   ├── presets.py
    │   └── trainer.py
    └── cli.py               # `sage infer quantize/prune/...`
```

### 核心接口定义
```python
@dataclass
class QuantizationProfile:
    weight_bits: Literal[16, 8, 4]
    activation_bits: Literal[16, 8, 4]
    kv_bits_prefill: Literal[16, 8, 4]
    kv_bits_decode: Literal[16, 8, 4]
    sparsity_ratio: float
    kernel_backend: Literal["ascend", "cambricon", "hygon", "kunlunxin"]
    calibration_dataset: str
    max_sequence_length: int

class QuantizedAttentionBackend(Protocol):
    def load_profile(self, profile: QuantizationProfile, artifacts: QuantArtifacts) -> None: ...
    def run(self, prompts: list[str], sampling_params: SamplingParams) -> GenerationResult: ...

@dataclass
class CapabilityDescriptor:
    profile_id: str
    throughput_hint_tps: float
    ttft_hint_ms: float
    kv_quant_schema: str
    sparsity_ratio: float
    hardware_backend: str
```

---

## 研究目标（Success Criteria）

### 性能指标
| 指标 | 目标 |
|------|------|
| 单芯片吞吐 | ≥ vLLM baseline 的 200% |
| TTFT / TPOT | 相比 FP16 baseline 降低 ≥20% |
| 单位 token 成本 | 下降 ≥30%（含能耗） |
| 显存占用 | Prefill 阶段减少 ≥40%，Decode 阶段减少 ≥30% |
| 长上下文稳定性 | 32K/64K/128K 上错误率 <1%，吞吐波动 <10% |

### 工程化指标
1. 新增 CLI：`sage infer quantize/prune/distill/validate`，生成可部署的 `SagePreset`。
2. 完成 ≥4 款国产硬件（昇腾、寒武纪、海光、昆仑芯）端到端 demo（kernel + runtime + benchmark）。
3. sageLLM 调度日志可展示量化/稀疏能力标签，PD 分离/自适应策略按标签路由。
4. CLI/Studio 成本面板可一键对比 baseline vs. 压缩配置，输出吞吐/延迟/成本/精度报告。

---

## 交付物要求
1. **设计文档**：量化/稀疏架构、硬件适配指南、KV schema 规格。
2. **核心代码**：`sageInfer/quantization`, `sageInfer/pruning`, `sageInfer/runtime` 及相关 kernel 实现。
3. **性能评估报告**：吞吐、TTFT、TPOT、长上下文稳定性、单位 token 成本、能耗对比。
4. **可复现实验脚本**：量化/剪枝/蒸馏流程、benchmark、CLI 示例，支持国产硬件环境复现。
