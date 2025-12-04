# Prompt · Phase 0：公共基础设施与接口解耦

你是一名负责 **sageLLM + sageInfer** 推理栈整体架构的首席工程师。请基于以下背景、目标与交付要求，输出一份可指导实际落地的技术方案，用于 Phase 0 公共建设。这一阶段的成果将成为课题一、课题二、课题三的共同基座，确保多课题并行时的接口兼容与演进路线稳定。

---

## 背景（Background）

### 项目定位
- Phase 0 处于 **meta prompt 与三个课题 prompt 之上**，负责定义通用的接口层、数据结构和 CLI 入口，使得后续课题可以并行推进且复用统一契约。
- 关键目标：**解耦 vLLM 依赖**、建立 `sageInfer` 目录结构、固化 KV Cache/传输/量化等跨课题共用的 Schema。

### 现状与问题
- 目前 `sageLLM` 直接 `import vllm.AsyncLLMEngine / vllm.LLM`，导致无法插拔自研的 **sageInfer** 或其他国产硬件后端。
- 各课题 prompt 中对 `sageInfer` 的目录、接口、数据结构描述不完全一致，容易造成重复实现甚至冲突。
- 缺少统一的 **硬件抽象层 (HAL)**、**KV Cache Schema**、**Capability Descriptor** 等跨课题约束。

### 总体目标
1. 定义 `InferenceBackend` 抽象接口，完成 vLLM 解耦，为 sageInfer 接入铺路。
2. 规范 `sageInfer` 的目录布局与公共模块（interfaces / hal / common / cli）。
3. 定义 KV Cache Schema、Capability Descriptor、Transport Contract 等跨课题共享结构。
4. 提供最小可运行 Demo：在不改变现有 vLLM 功能的情况下，通过新接口驱动 vLLM 来验证解耦有效。

---

## 研究内容（Research Scope）

### 1. 推理后端抽象（InferenceBackend）
- 设计 `InferenceBackend` Protocol，覆盖 `prefill`, `decode`, `generate`, `get_capability`, `get_kv_schema`, `load_quant_profile` 等接口。
- 为 vLLM 实现 `VLLMBackendAdapter`，验证与原有行为等价。
- 输出最小 Demo：`sageLLM Control Plane → InferenceBackend → vLLM`。

### 2. 共享数据结构 & Schema
- `KVCacheSchema`: dtype、page_size、num_layers、num_heads、head_dim、scale_schema。
- `CapabilityDescriptor`: instance_type、supported_precisions、max_batch、max_seq_len、throughput_hint、ttft_hint、hardware_backend、kv_schema。
- `TransportPlan` / `KVChunk` 基础类型，供课题一/二共用。
- `QuantizationProfile`: weight_bits、activation_bits、kv_bits_prefill/decode、sparsity_ratio、calibration_dataset。

### 3. 硬件抽象层 (HAL)
- 规划 `sageInfer/hal/` 目录，定义 `AcceleratorDescriptor`、`LinkProfile`、`MemoryTierSpec` 等。
- 提供最小实现：读取硬件探测结果（可 Mock）并输出 JSON Profile。
- 为课题一/三提供统一硬件能力查询 API。

### 4. CLI 与配置打通
- 新增 `sage infer` 命令空间：`sage infer backends:list`, `sage infer backend:test`, `sage infer schema:dump`。
- 配置文件统一入口：`config/sage_infer.yaml`，描述 inference backend、kv_schema、transport preset。

### 5. 集成策略
- 在 meta prompt 中定义 Phase 0 作为所有课题的前置里程碑。
- 输出并行指导：Phase 0 完成前允许课题二搭建模拟器，但必须遵守接口契约。

---

## 模块设计（Module Design）

### 目录结构建议
```
sage/common/components/sage_infer/
├── __init__.py
├── interfaces/
│   ├── inference_backend.py        # InferenceBackend Protocol + base classes
│   ├── schemas.py                  # KVCacheSchema / QuantizationProfile / CapabilityDescriptor
│   └── transport_contract.py       # KVChunk / TransportPlan
├── backends/
│   ├── __init__.py
│   └── vllm_adapter.py             # VLLMBackendAdapter（Phase 0 交付）
├── hal/
│   ├── __init__.py
│   ├── accelerator_descriptor.py
│   └── domestic/
│       ├── ascend.py
│       ├── cambricon.py
│       ├── hygon.py
│       └── kunlunxin.py
├── common/
│   ├── capability_registry.py      # 供 Control Plane 查询
│   └── telemetry.py
└── cli/
    ├── __init__.py
    └── commands.py                 # `sage infer ...`
```

### 核心接口草案
```python
@dataclass
class KVCacheSchema:
    dtype: Literal["fp16", "fp8_e4m3", "fp8_e5m2", "int4"]
    page_size: int
    num_layers: int
    num_heads: int
    head_dim: int
    scale_dtype: Literal["fp16", "fp32", "int8"]
    layout: Literal["paged", "contiguous"]

@dataclass
class CapabilityDescriptor:
    backend_name: str
    instance_type: Literal["prefill", "decode", "general"]
    supported_precisions: list[str]
    max_batch_size: int
    max_sequence_length: int
    throughput_hint_tps: float
    ttft_hint_ms: float
    kv_cache_capacity_gb: float
    hardware_backend: Literal["cuda", "ascend", "cambricon", "hygon", "kunlunxin"]
    kv_schema: KVCacheSchema

class InferenceBackend(Protocol):
    async def prefill(self, prompts: list[str], *, request_id: str) -> PrefillResult: ...
    async def decode(self, state: DecodeState, *, request_id: str) -> DecodeResult: ...
    async def generate(self, prompts: list[str], params: SamplingParams) -> list[TokenStream]: ...
    def get_capability(self) -> CapabilityDescriptor: ...
    def get_kv_schema(self) -> KVCacheSchema: ...
    def load_quant_profile(self, profile: QuantizationProfile) -> None: ...
```

### 交互示例
1. `sage llm serve --backend vllm --kv-schema preset=fp8` → CLI 读取 Phase 0 定义的 Schema。
2. `sageLLM Control Plane` 调用 `backend.get_capability()`，根据 `instance_type` 和 `kv_schema` 进行 PD/AF 调度。
3. 课题一实现的 `TransportEngine` 使用 Phase 0 的 `KVChunk`，无需关心调度细节。
4. 课题三产出的 `QuantizationProfile` 能被任意 InferenceBackend 加载。

---

## 研究目标（Success Criteria）

### 技术指标
| 指标 | 目标 |
|------|------|
| InferenceBackend 接口实现 | 能驱动 vLLM 正常推理，无性能回退 (±3%) |
| 接口文档 | 覆盖 KV Schema、Capability、Transport 契约 |
| CLI 兼容性 | `sage llm serve` 支持 `--backend`、`--kv-schema` 新参数 |
| 测试覆盖 | 新增接口的单元测试/契约测试 ≥80% 覆盖 |
| 课题依赖 | 三个课题均引用 Phase 0 提供的接口，无自定义重复定义 |

### 工程化指标
1. **设计文档**：位于 `docs/dev-notes/.../task0-common-infrastructure/README.md`，描述接口、调用链、演进路线。
2. **代码实现**：`InferenceBackend` 抽象、`VLLMBackendAdapter`、CLI 扩展、示例配置。
3. **测试脚本**：最小端到端用例（Control Plane → Backend Adapter → vLLM）。
4. **并行指引**：在 meta prompt 中附 Phase 0 完成标准及课题间依赖说明。

---

## 交付物要求
1. `prompt.md`（本文档）
2. `README.md`：Phase 0 设计说明、接口详解、依赖图
3. `interfaces/*.py`：接口与数据结构实现
4. `backends/vllm_adapter.py`：vLLM 适配器 + 单元测试
5. `cli/commands.py`：`sage infer` 命令实现
6. `examples/phase0_demo.py`：驱动 Control Plane 的示例
7. CI Hook：在 `sage-dev project test` 中加入 Phase 0 契约测试

---

请在方案中明确：接口契约、演进路线、向下兼容策略、以及各课题如何复用这些成果。Phase 0 完成后，再进入课题一/二/三的正式实现，以降低重复建设与后期重构成本。
