# Prompt · 课题二：KV Cache 管理与调度优化

你是一名负责 SAGE/sageInfer 推理引擎开发的系统架构师，请依据以下背景与要求，输出详细的技术方案与实验路线。

---

## 背景（Background）
### 项目定位
- **sageInfer**：新建的高性能推理执行引擎，位于 sageLLM Control Plane 之下，负责 KV Cache 管理、算子执行和国产硬件适配。
- **课题二定位**：在 sageInfer 中构建 KV Cache 池化、分层存储、跨批次复用与软硬协同机制，并将其调度语义接入 sageLLM Control Plane（PD/AF 分离策略、KV-aware scheduler），形成“Control Plane + Execution Plane”协同优化闭环。

### 问题背景
- 国产算力平台的 HBM/DDR/SSD 拓扑差异大，现有 vLLM 栈无法高效管理长上下文 KV Cache，导致显存浪费与跨设备搬运开销。
- 现有 sageLLM 仅能进行请求级调度，缺乏对 KV Cache 生命周期、配额、驱逐的掌控，无法在 PD/AF 分离或混合工作负载下保持高吞吐与低 TTFT/TPOT。
- Prefix caching、热点预取和跨批次复用尚未标准化，阻碍 32K+ 上下文场景的稳定性。

### 现有技术基础（可复用模块）
- `sageLLM/control_plane/pd_routing.py`：Prefill/Decode 路由基础
- `sageLLM/control_plane/strategies/`：调度策略框架，可注入 KV-aware 策略
- `sageLLM/control_plane/metrics_collector.py`：遥测与指标上报渠道
- `sage-common` 中已有的 GPU/NVML 监控、SagePorts 端口管理

---

## 研究内容（Research Scope）
### 1. KV Cache 池化与分层管理
- 设计统一的 KV Block 抽象，支持 HBM → DDR → SSD 三级存储，提供分配、迁移、压缩接口。
- 引入碎片整理与生命周期跟踪，确保 32K+ 上下文下的空间利用率 ≥90%。
- 结合国产硬件 SDK（昇腾、寒武纪、海光、昆仑芯）的内存 API，实现零拷贝/异构寻址。

### 2. 跨批次复用与热点预取
- 构建 Prefix Fingerprint 服务：对 prompt 哈希、语义编码，识别可复用 KV Slice。
- 设计热点谱系（Hotset DAG），驱动后台预取 worker 在请求到达前加载/迁移 KV。
- 制定淘汰策略：结合访问频率、SLO slack、重计算代价，防止热点 OOM。

### 3. PD/AF 分离调度优化
- 在 sageLLM 内扩展 PD/AF 专用队列与 KV-aware scheduler，支持 Prefill/Decode/AF 阶段独立限流与配额。
- 提供计算-存储解耦接口：调度决策可请求额外 KV 预算或触发迁移。
- 探索 Attention/FFN 分离（可选），按算子特点调度到异构芯片池。

### 4. 软硬协同加速
- 利用国产硬件特性（如昇腾 DVPP、寒武纪 MLU 原语）实现 KV 压缩、DMA overlap。
- 异构内存（HBM+DDR）统一寻址与 QoS 管理，暴露优先级接口给 Control Plane。

---

## 模块设计（Module Design）
### 目录结构建议
```
sageInfer/
└── kv_cache/
    ├── __init__.py
    ├── block.py                 # KV Block 抽象（meta + data handle）
    ├── pool_manager.py          # 池化与配额管理
    ├── hierarchical_store.py    # HBM/DDR/SSD tier driver
    ├── allocator/
    │   ├── buddy.py             # Buddy allocator for HBM
    │   └── slab.py              # Slab allocator for DDR/SSD
    ├── prefix_cache.py          # Prefix fingerprint & lookup
    ├── hotspot.py               # 热点分析/预取调度
    ├── eviction.py              # 多策略淘汰（LRU/SLO-aware）
    ├── telemetry.py             # KV 指标采集
    └── hw/
        ├── ascend.py            # 昇腾内存 API 封装
        ├── cambricon.py         # 寒武纪适配
        ├── hygon.py             # 海光适配
        └── kunlunxin.py         # 昆仑芯适配

sageLLM/control_plane/
├── kv_aware_scheduler.py        # 新增：KV-aware 调度策略
├── pd_routing.py                # 增强：支持 AF、KV 预算传递
└── monitoring.py                # 增强：KV 指标上报
```

### 核心接口定义（示例）
```python
# block.py
@dataclass
class KVBlockHandle:
    block_id: str
    tier: CacheTier
    size_bytes: int
    kv_format: KVFormat  # FP16/FP8/INT4
    owner_request_id: str | None
    ref_count: int

# pool_manager.py
class KVPoolManager:
    def allocate(self, tokens: int, precision: KVFormat) -> KVBlockHandle:
        ...
    def migrate(self, handle: KVBlockHandle, target_tier: CacheTier) -> KVBlockHandle:
        ...
    def release(self, handle: KVBlockHandle) -> None:
        ...

# kv_aware_scheduler.py
class KVAwareSchedulingDecision(SchedulingDecision):
    kv_budget_mb: float
    requires_prefetch: list[KVBlockHint]
```

---

## 研究目标（Success Criteria）
### 性能指标
| 指标 | 目标 |
|------|------|
| 单芯片有效算力 | ≥90% 理论峰值 |
| 相比 vLLM 吞吐 | ≥2×（相同模型与硬件） |
| TTFT/TPOT 改善 | ≥20% |
| KV Cache 命中率 | ≥60%（跨批次复用） |
| 热点预取命中率 | ≥85% |
| HBM→DDR 迁移带宽利用 | ≥80% |

### 工程化指标
1. KV 池化/分层管理单元测试覆盖率 ≥80%
2. SageLLM Control Plane 能读取 KV 遥测并做调度决策
3. 提供 ≥3 套国产硬件配置预设（昇腾/寒武纪/海光）
4. 长上下文（32K、64K）实验脚本自动化，可在 CI GPU 节点复现

---

## 交付物要求
1. **设计文档**：分层缓存架构、调度策略、硬件适配方案，含序列图/状态机
2. **核心代码**：`sageInfer/kv_cache/` 与 `sageLLM/control_plane/kv_aware_scheduler.py`
3. **性能评估报告**：含 vLLM 对比、国产硬件多配置数据、TTFT/TPOT 曲线
4. **可重复实验脚本**：基于 `sage-benchmark` 的 KV 压力测试与长上下文稳定性套件
