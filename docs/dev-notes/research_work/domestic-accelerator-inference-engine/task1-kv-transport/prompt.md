# Prompt · 课题一：高性能通信库与 KV 传输

你是一名负责 SAGE / sageInfer 推理引擎的系统架构师。请基于以下背景、要求与交付清单，输出完整的技术方案、代码/伪代码示例、实验设计与验证指标，确保能够指导实际研发落地。

---

## 前置依赖（Prerequisites）

> ⚠️ 本课题依赖 **Phase 0 公共基础设施**，请确保以下接口已定义并可用：

| 依赖项 | 来源 | 用途 |
|--------|------|------|
| `KVCacheSchema` | `sageInfer/interfaces/schemas.py` | KV 数据格式定义（dtype, page_size 等） |
| `TransportPlan` / `KVChunk` | `sageInfer/interfaces/transport_contract.py` | 传输契约基础类型 |
| `AcceleratorDescriptor` | `sageInfer/hal/accelerator_descriptor.py` | 硬件能力描述 |
| `InferenceBackend` | `sageInfer/interfaces/inference_backend.py` | 推理后端接口（用于集成测试） |

### 与其他课题的关系
- **被课题二依赖**：课题二的 KV Cache 管理需要调用本课题的 `TransportEngine` 进行跨节点传输
- **与课题三协同**：量化后的 KV Cache 需要格式转换，复用本课题的 `format.converter`

---

## 背景（Background）

### 项目定位
- 课题一聚焦 **sageInfer/transport** 子系统，负责长上下文 KV Cache 在多 GPU / 多节点之间的高速搬移与格式转换，是国产算力推理栈的“数据血管”。
- 该模块需向下适配华为昇腾（HCCS + PCIe）、寒武纪 MLU（MLU-Link）、海光 DCU（xGMI）、昆仑芯等互联拓扑，并向上暴露统一的 `TransportEngine` API 给 sageLLM Control Plane。
- 成果需与 `sage llm serve` CLI、`sage-gateway` 监控面板一键联动，让运维可按硬件/业务需求快速切换通信策略。

### 问题背景
- 现有 vLLM/SGLang 等开源引擎以 NVIDIA CUDA + NVLink 为主，对国产加速卡的 DMA/NIC/互联特性缺乏优化，导致长上下文推理时 KV 传输成为瓶颈。
- 国产硬件的链路拓扑、带宽、包长限制、SRAM Window、页表能力各不相同，单纯 memcpy + CPU 调度会造成 ≥40% 带宽浪费。
- 目标是做出软硬协同的 KV 传输库，达到 **单芯片有效算力 ≥90%**、**吞吐量较 vLLM ≥2×**、32K+ 上下文稳定、TTFT/TPOT 至少再降低 10%（通信贡献）。

### 现有技术积累
- `packages/sage-common/src/sage/common/components/sage_llm/control_plane/` 已有 GPU 资源管理、拓扑描述、策略调度骨架，可扩展为硬件感知接口。
- `sage llm serve` CLI 与 `sage-gateway` 监控链路已支持扩展 flag / Prometheus 指标，可挂载新的 KV Transport config 与遥测。
- 可借鉴的参考：vLLM PagedAttention prefix cache、TensorRT-LLM 通信插件、SGLang RadixAttention 的流水线传输。

---

## 研究内容（Research Scope）

### 1. 国产硬件互联拓扑适配
- 构建 `hardware.topology` 探测器：自动识别 HCCS、MLU-Link、xGMI、PCIe 等链路，采集带宽、延迟、Hop 数、最大包长、SRAM window、NUMA 亲和性。
- 设计 `AcceleratorDescriptor`：封装 DMA 对齐、页表能力、可用 API（昇腾 ACL、寒武纪 CNRT、海光 ROCm、昆仑芯 XPU）。
- 输出统一的 `HardwareProfile`（JSON/schema），供 CLI 及控制平面加载。

### 2. 高性能 KV 传输引擎
- 定义 `TransportEngine` 抽象，提供 `send_kv_chunk`、`recv_kv_chunk`、`stream_pipeline` 等接口，支持 chunking + overlap + 优先队列。
- 实现多后端：`RDMA`（RoCEv2/xGMI）、`PCIeDMA`（BAR direct + peer2peer）、`SharedMemory`（NUMA pinned buffer），支持零拷贝与分层缓存（HBM↔SRAM）。
- 设计 `TransferPlanner`，根据拓扑/负载决定 chunk_size、prefetch_depth、是否启用压缩。

### 3. 混合精度格式转换
- 在 `format.converter` 中实现 FP8 (E4M3/E5M2)、INT4、FP16/32 互转，支持 per-channel scaling + error feedback。
- 提供 CUDA/CANN/MLU kernel 或 HIP/ACL 实现，要求转换阶段占总推理时间 <5%。
- 允许运营在 CLI 层通过 `--kv-transport target-dtype` 控制。

### 4. 遥测与控制平面协同
- 在 `telemetry.py` 输出实时带宽、延迟、错误率、热点 chunk 分布，暴露 Prometheus Counter/Gauge。
- Control Plane 接收传输遥测，根据 QoS 策略动态调节 chunk_size、并发度、优先级，甚至触发跨节点重新布置。
- Gateway 仪表盘新增 KV Transport 卡片，显示各链路利用率、格式转换开销、失败告警。

### 5. CLI / Preset 配置
- 新增 `KVTransportConfig`（支持 `preset`, `backend`, `target_dtype`, `prefetch_depth`, `zero_copy`, `compression` 等字段）。
- 在 `sage llm serve` 中加入 `--kv-transport preset`、`--kv-transport backend=rdma` 等选项；提供不少于 3 个 preset（High-BW、Low-Latency、Low-Cost）。
- 提供 `sage transport probe` demo 命令，输出硬件探测结果与推荐配置。

---

## 模块设计（Module Design）

### 目录结构建议
```
sage/common/components/sage_infer/
└── transport/
    ├── __init__.py
    ├── config.py                  # KVTransportConfig / presets
    ├── engine.py                  # TransportEngine + planner
    ├── telemetry.py               # 遥测采集/上报
    ├── hardware/
    │   ├── __init__.py
    │   ├── topology.py            # 链路探测
    │   ├── accelerator_descriptor.py
    │   └── domestic/
    │       ├── ascend.py
    │       ├── cambricon.py
    │       ├── hygon.py
    │       └── kunlunxin.py
    ├── backends/
    │   ├── __init__.py
    │   ├── rdma.py
    │   ├── pcie.py
    │   └── shm.py
    └── format/
        ├── __init__.py
        ├── converter.py
        └── kernels/
            ├── fp8_convert.cu
            ├── int4_pack.cu
            └── ascend_kernel.cc
```

### 核心接口草案
```python
@dataclass
class KVTransportConfig:
    transport_backend: str = "auto"      # auto|rdma|pcie|shm
    target_dtype: str = "fp16"           # fp16|fp8_e4m3|fp8_e5m2|int4
    chunk_size: int = 4096
    overlap_streams: int = 2
    prefetch_depth: int = 2
    enable_zero_copy: bool = True
    enable_compression: bool = False

class TransportEngine(Protocol):
    async def send_kv_chunk(self, chunk: KVChunk, dest: DeviceSpec) -> TransferStats: ...
    async def recv_kv_chunk(self, chunk: KVChunk, src: DeviceSpec) -> TransferStats: ...
    async def stream_pipeline(self, chunks: Iterable[KVChunk], plan: TransferPlan) -> TransferReport: ...
```

### CLI 集成要点
- `sage llm serve --kv-transport preset=high-bw --kv-transport target-dtype=fp8_e4m3`
- CLI 自动调用 `hardware.topology.probe()`，若检测在 WSL2/PCIe-only，fallback 到 `pcie` backend。
- 配置写入 `config/config.yaml` 或独立 `kv_transport.yaml`，供服务端与 Gateway 共享。

---

## 研究目标（Success Criteria）

### 性能 & 通信指标
| 指标 | 目标 |
|------|------|
| 跨节点 KV 传输带宽利用率 | ≥85% |
| 单跳传输延迟 | ≤20µs（同节点） / ≤80µs（跨节点） |
| FP8/INT4 转换阶段占比 | ≤5% 总推理时间 |
| TTFT / TPOT 改善 | ≥10% 由通信层贡献 |
| 32K-128K 上下文吞吐 | 稳定且 ≥ vLLM baseline ×2 |

### 工程化指标
- 支持 ≥4 款国产加速卡的端到端 demo（含自动探测脚本）。
- CLI 提供 ≥3 个内置 preset，Gateway 面板有 KV Transport 卡片。
- 遥测指标纳入 `sage-dev project test --coverage` 的 e2e 测试覆盖。
- 提供 `docs/dev-notes/.../task1-kv-transport/README.md`，详述配置、调试、FAQ。

---

## 交付物清单
1. **设计文档**：含架构、硬件描述矩阵、传输协议、格式转换方案、遥测接口。
2. **核心代码**：`sageInfer/transport/` 全量实现 + `sage-cli` / `sage-gateway` 扩展 + vendored kernel（如需）。
3. **性能评估报告**：覆盖吞吐、TTFT/TPOT、带宽利用率、格式转换开销，与 vLLM baseline 对比（≥32K 上下文、RAG 负载）。
4. **可重复实验脚本**：硬件探测 demo、KV 传输 micro-benchmark、端到端推理 benchmark、遥测验证脚本。
5. **Preset 配置**：`kv_transport_presets.yaml`（High-BW / Low-Latency / Low-Cost），附推荐硬件清单。

请在方案中明确任务拆解、技术路线、关键 API/数据结构、实验矩阵、风险与缓解策略，输出可直接指导研发的计划。
