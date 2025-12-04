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
- 规划 `sageLLM/sage_infer/hal/` 目录，定义 `AcceleratorDescriptor`、`LinkProfile`、`MemoryTierSpec` 等。
- 提供最小实现：读取硬件探测结果（可 Mock）并输出 JSON Profile。
- 为课题一/三提供统一硬件能力查询 API。

### 4. CLI 与配置打通
- 新增 `sage infer` 命令空间：`sage infer backend list`, `sage infer backend test`, `sage infer schema dump`。
- 配置文件统一入口：`config/sage_infer.yaml`，描述 inference backend、kv_schema、transport preset。

### 5. 集成策略
- 在 meta prompt 中定义 Phase 0 作为所有课题的前置里程碑。
- 输出并行指导：Phase 0 完成前允许课题二搭建模拟器，但必须遵守接口契约。

---

## 模块设计（Module Design）

### 目录结构建议

> **设计原则**：`sage_infer` 对标 vLLM 推理引擎，与 `control_plane` 同级，位于 `sageLLM/` 下。
> - **Control Plane** 负责调度策略（何时驱逐、迁移、预取）
> - **sage_infer** 负责实际执行（存储、量化、格式转换）

```
sage/common/components/sage_llm/sageLLM/
├── control_plane/                  # 调度策略层
│   ├── manager.py
│   ├── request_classifier.py
│   ├── strategies/
│   ├── executors/
│   ├── memory_manager/             # 【课题二】KV Cache 调度策略
│   │   ├── admission_controller.py # 准入控制策略
│   │   ├── eviction_policy.py      # 驱逐策略（LRU/热点/SLO感知）
│   │   ├── quota_allocator.py      # 配额分配策略
│   │   └── migration_planner.py    # 迁移决策（HBM↔DRAM↔SSD）
│   └── cache_reuse/                # 【课题二】缓存复用策略
│       ├── reuse_policy.py         # 复用决策
│       └── prefetch_scheduler.py   # 预取调度
│
└── sage_infer/                     # 推理执行层
    ├── __init__.py
    ├── interfaces/
    │   ├── __init__.py
    │   ├── inference_backend.py    # InferenceBackend Protocol + base classes
    │   ├── schemas.py              # KVCacheSchema / QuantizationProfile / CapabilityDescriptor
    │   └── transport_contract.py   # KVChunk / TransportPlan
    ├── kv_cache/                   # 【课题二+三共建】KV Cache 存储实现
    │   ├── __init__.py
    │   ├── store.py                # KVStore 基类
    │   ├── paged_store.py          # 分页存储实现
    │   ├── quantized_store.py      # 【课题三】量化存储 (QuantizedKVStore)
    │   ├── tiered_backend.py       # 【课题二】分层存储后端 (HBM/DRAM/SSD)
    │   ├── slice_registry.py       # 【课题二】KV Slice 索引
    │   └── format_converter.py     # 【课题一】格式转换（与 transport 协同）
    ├── backends/
    │   ├── __init__.py
    │   ├── vllm_adapter.py         # VLLMBackendAdapter（Phase 0 交付）
    │   └── domestic/               # 国产硬件后端（课题后续实现）
    │       ├── __init__.py
    │       ├── ascend_backend.py
    │       ├── cambricon_backend.py
    │       ├── hygon_backend.py
    │       └── kunlunxin_backend.py
    ├── hal/                        # 硬件抽象层（通用能力探测）
    │   ├── __init__.py
    │   ├── accelerator_descriptor.py  # AcceleratorDescriptor 数据类
    │   ├── link_profile.py         # LinkProfile 链路描述
    │   ├── memory_tier.py          # MemoryTierSpec 内存层级
    │   └── hw_detect/              # 【通用】硬件能力探测
    │       ├── __init__.py         # 职责：算力、显存、互联拓扑、NUMA 亲和
    │       ├── base.py             # HardwareDetector 基类
    │       ├── cuda.py             # NVIDIA CUDA 能力探测
    │       ├── ascend.py           # 华为昇腾能力探测
    │       ├── cambricon.py        # 寒武纪 MLU 能力探测
    │       ├── hygon.py            # 海光 DCU 能力探测
    │       └── kunlunxin.py        # 昆仑芯 XPU 能力探测
    │       # ⚠️ 注意：仅输出静态能力描述（AcceleratorDescriptor）
    │       # 传输专用配置（DMA/RDMA 参数）由课题一 transport/hardware/ 扩展
    ├── model_router/              # 【新增】多模型路由与混合部署
    │   ├── __init__.py
    │   ├── router.py               # ModelRouter - 请求路由到正确模型
    │   ├── model_registry.py       # ModelRegistry - 已加载模型注册表
    │   ├── memory_planner.py       # MemoryPlanner - 多模型显存分配
    │   └── hybrid_backend.py       # HybridInferenceBackend 实现
    ├── common/
    │   ├── __init__.py
    │   ├── capability_registry.py  # 供 Control Plane 查询
    │   └── telemetry.py
    └── cli/
        ├── __init__.py
        └── commands.py             # `sage infer ...`
```

### 架构关系图
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              sageLLM                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  control_plane/                     │  sage_infer/                           │
│  ┌──────────────────────────────┐   │  ┌────────────────────────────────┐   │
│  │ ControlPlaneManager          │   │  │ InferenceBackend (Protocol)    │   │
│  │ - 请求调度                    │──▶│  │ - prefill() / decode()         │   │
│  │ - PD 分离决策                 │   │  │ - generate()                   │   │
│  │ - 负载均衡                    │   │  └───────────┬──────────────────┘   │
│  └──────────────────────────────┘   │              │                        │
│                                     │  ┌───────────▼──────────────────────┐ │
│  ┌──────────────────────────────┐   │  │ HybridInferenceBackend (Protocol)│ │
│  │ HybridSchedulingPolicy       │   │  │ - generate(model=...) 【LLM】    │ │
│  │ - LLM/Embedding 混合调度      │──▶│  │ - embed(model=...)    【Embed】 │ │
│  │ - RAG 场景联合调度            │   │  │ - load_model() / unload_model()│ │
│  └──────────────────────────────┘   │  └───────────┬──────────────────────┘ │
│                                     │              │                        │
│                                     │  ┌───────────▼──────────────────────┐ │
│                                     │  │ model_router/                    │ │
│                                     │  │ ├─ ModelRouter (请求路由)         │ │
│                                     │  │ ├─ ModelRegistry (模型注册)       │ │
│                                     │  │ └─ MemoryPlanner (显存规划)       │ │
│                                     │  └─────────────────────────────────┘  │
│                                     │                                       │
│                                     │  ┌───────────────────────────────────┐│
│                                     │  │ backends/                         ││
│                                     │  │ ├─ VLLMBackendAdapter (LLM)       ││
│                                     │  │ ├─ EmbeddingBackendAdapter (Embed)││
│                                     │  │ ├─ AscendBackend / CambriconBackend││
│                                     │  │ └─ ...                            ││
│                                     │  └───────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
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
    """实例能力描述符 - 统一定义，供所有课题使用"""
    # 基础信息
    backend_name: str
    instance_type: Literal["prefill", "decode", "general", "embedding", "hybrid"]
    hardware_backend: Literal["cuda", "ascend", "cambricon", "hygon", "kunlunxin"]

    # 容量限制
    max_batch_size: int
    max_sequence_length: int
    kv_cache_capacity_gb: float

    # 精度能力
    supported_precisions: list[str]  # ["fp16", "fp8_e4m3", "int4", ...]
    kv_schema: KVCacheSchema

    # 量化/稀疏能力 (课题三扩展)
    quant_profile_id: str | None = None
    sparsity_ratio: float = 0.0

    # 性能提示
    throughput_hint_tps: float = 0.0
    ttft_hint_ms: float = 0.0

@dataclass
class ModelDescriptor:
    """模型描述符 - 支持多模型混合部署"""
    model_id: str
    model_type: Literal["llm", "embedding", "reranker", "multimodal"]
    model_path: str

    # 资源配置
    device_ids: list[int]              # 占用的 GPU/NPU
    memory_gb: float                   # 显存占用

    # 能力描述
    max_batch_size: int
    max_sequence_length: int
    supported_precisions: list[str]

    # Embedding 专用字段
    embedding_dim: int | None = None   # 输出向量维度
    pooling_type: Literal["mean", "cls", "last"] | None = None

    # Reranker 专用字段
    max_pair_length: int | None = None

@dataclass
class HybridCapabilityDescriptor:
    """混合实例能力描述符 - 支持 LLM + Embedding 同时服务"""
    # 基础能力（继承 CapabilityDescriptor 的核心字段）
    backend_name: str
    instance_type: Literal["hybrid", "llm_embedding"] = "hybrid"
    hardware_backend: Literal["cuda", "ascend", "cambricon", "hygon", "kunlunxin"] = "cuda"

    # 多模型支持
    loaded_models: list[ModelDescriptor] = field(default_factory=list)

    # 资源共享策略
    gpu_sharing_mode: Literal["exclusive", "mps", "time_slice"] = "time_slice"
    memory_isolation: bool = False

    # 聚合能力
    total_memory_gb: float = 0.0
    available_memory_gb: float = 0.0

    def get_llm_models(self) -> list[ModelDescriptor]:
        return [m for m in self.loaded_models if m.model_type == "llm"]

    def get_embedding_models(self) -> list[ModelDescriptor]:
        return [m for m in self.loaded_models if m.model_type == "embedding"]

@dataclass
class QuantizationProfile:
    """量化配置描述符 - 统一定义，供课题三及其他课题使用

    课题三在 quantization/profiles.py 中 re-export 此类，
    并提供 load_profile_from_yaml(), validate_profile() 等工具函数。
    """
    # 位宽配置
    weight_bits: Literal[16, 8, 4]
    activation_bits: Literal[16, 8, 4]
    kv_bits_prefill: Literal[16, 8, 4]
    kv_bits_decode: Literal[16, 8, 4]

    # 稀疏配置
    sparsity_ratio: float = 0.0
    sparsity_pattern: Literal["none", "2:4", "block", "unstructured"] = "none"

    # 硬件后端
    kernel_backend: Literal["cuda", "ascend", "cambricon", "hygon", "kunlunxin"] = "cuda"

    # 校准配置
    calibration_dataset: str = ""
    calibration_samples: int = 512

    # 约束
    max_sequence_length: int = 8192

class InferenceBackend(Protocol):
    """单模型推理后端接口"""
    async def prefill(self, prompts: list[str], *, request_id: str) -> PrefillResult: ...
    async def decode(self, state: DecodeState, *, request_id: str) -> DecodeResult: ...
    async def generate(self, prompts: list[str], params: SamplingParams) -> list[TokenStream]: ...
    def get_capability(self) -> CapabilityDescriptor: ...
    def get_kv_schema(self) -> KVCacheSchema: ...
    def load_quant_profile(self, profile: QuantizationProfile) -> None: ...

class EmbeddingBackend(Protocol):
    """Embedding 推理后端接口"""
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    async def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]: ...
    def get_embedding_dim(self) -> int: ...
    def get_max_length(self) -> int: ...

class HybridInferenceBackend(Protocol):
    """混合推理后端 - 支持 LLM + Embedding 同时服务

    使用场景：
    1. 单 GPU 上同时部署 LLM + Embedding（显存分片）
    2. 多 GPU 分别部署不同模型（资源隔离）
    3. RAG 场景：Embedding 检索 + LLM 生成一站式服务
    """

    # === LLM 接口 ===
    async def generate(
        self,
        prompts: list[str],
        params: SamplingParams,
        model: str | None = None,  # 指定 LLM 模型，None 使用默认
    ) -> list[TokenStream]: ...

    async def chat(
        self,
        messages: list[dict],
        params: SamplingParams,
        model: str | None = None,
    ) -> ChatResponse: ...

    # === Embedding 接口 ===
    async def embed(
        self,
        texts: list[str],
        model: str | None = None,  # 指定 Embedding 模型，None 使用默认
    ) -> list[list[float]]: ...

    # === 模型管理 ===
    def list_models(self) -> list[ModelDescriptor]: ...
    def load_model(self, model: ModelDescriptor) -> None: ...
    def unload_model(self, model_id: str) -> None: ...
    def get_model_status(self, model_id: str) -> dict: ...

    # === 能力查询 ===
    def get_hybrid_capability(self) -> HybridCapabilityDescriptor: ...
```

### 混合推理使用示例

```python
# === 场景 1: 单 GPU 显存分片部署 ===
from sage_infer.backends.hybrid_backend import HybridBackend

backend = HybridBackend(
    llm_config={
        "model_id": "Qwen/Qwen2.5-7B-Instruct",
        "device_ids": [0],
        "memory_fraction": 0.7,  # 70% 显存给 LLM
    },
    embedding_config={
        "model_id": "BAAI/bge-m3",
        "device_ids": [0],
        "memory_fraction": 0.3,  # 30% 显存给 Embedding
    },
    sharing_mode="time_slice",
)

# 同一后端同时处理两种请求
embeddings = await backend.embed(["查询文本"])
response = await backend.generate(["基于检索结果回答..."], params)

# === 场景 2: 多 GPU 资源隔离部署 ===
backend = HybridBackend(
    llm_config={
        "model_id": "Qwen/Qwen2.5-72B-Instruct",
        "device_ids": [0, 1, 2, 3],  # 4 卡 TP 部署
    },
    embedding_config={
        "model_id": "BAAI/bge-m3",
        "device_ids": [4],  # 独立 1 卡
    },
    sharing_mode="exclusive",
)

# === 场景 3: 动态加载多模型 ===
backend = HybridBackend()
backend.load_model(ModelDescriptor(
    model_id="qwen-7b",
    model_type="llm",
    model_path="Qwen/Qwen2.5-7B-Instruct",
    device_ids=[0],
    memory_gb=14.0,
    max_batch_size=32,
    max_sequence_length=32768,
    supported_precisions=["fp16", "fp8_e4m3"],
))
backend.load_model(ModelDescriptor(
    model_id="bge-m3",
    model_type="embedding",
    model_path="BAAI/bge-m3",
    device_ids=[0],
    memory_gb=2.0,
    max_batch_size=256,
    max_sequence_length=8192,
    supported_precisions=["fp16"],
    embedding_dim=1024,
    pooling_type="cls",
))

# 指定模型调用
embeddings = await backend.embed(texts, model="bge-m3")
response = await backend.generate(prompts, params, model="qwen-7b")
```

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
```

### 交互示例
1. `sage llm serve --backend vllm --kv-schema preset=fp8` → CLI 读取 Phase 0 定义的 Schema。
2. `sageLLM Control Plane` 调用 `backend.get_capability()`，根据 `instance_type` 和 `kv_schema` 进行 PD/AF 调度。
3. 课题一实现的 `TransportEngine` 使用 Phase 0 的 `KVChunk`，无需关心调度细节。
4. 课题三产出的 `QuantizationProfile` 能被任意 InferenceBackend 加载。
5. **混合部署**：`sage infer serve --llm qwen-7b --embedding bge-m3 --sharing time_slice` 启动混合推理服务。

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
