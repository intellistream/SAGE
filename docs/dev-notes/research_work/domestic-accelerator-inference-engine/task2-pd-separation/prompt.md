# Prompt：课题二「计算分离与 KV Cache 管理」

> **核心定位**：本课题全部在 **sageLLM**（SAGE 的 LLM 推理引擎模块）内实现，sageLLM 位于 `packages/sage-common/src/sage/common/components/sage_llm/sageLLM/`。

---

## 前置依赖（Prerequisites）

> ⚠️ 本课题依赖 **Phase 0 公共基础设施**，请确保以下接口已定义并可用：

| 依赖项 | 来源 | 用途 |
|--------|------|------|
| `InferenceBackend` | `sageLLM/sage_infer/interfaces/inference_backend.py` | 推理后端抽象接口，解耦 vLLM |
| `CapabilityDescriptor` | `sageLLM/sage_infer/interfaces/schemas.py` | 实例能力描述，用于调度决策 |
| `KVCacheSchema` | `sageLLM/sage_infer/interfaces/schemas.py` | KV 数据格式定义 |
| `VLLMBackendAdapter` | `sageLLM/sage_infer/backends/vllm_adapter.py` | vLLM 适配器（验证用） |

### 与其他课题的关系
- **依赖课题一**：跨节点 KV Cache 迁移需要调用 `TransportEngine`（Phase 1 可用 Mock）
- **被课题三依赖**：量化后的 KV Cache 精度策略需要与本课题的分层缓存协同
- **推荐先行**：本课题定义"需要什么样的传输接口"，课题一据此实现

### 并行开发策略
1. Phase 0 完成前：可先搭建 Mock TransportEngine，定义接口契约
2. Phase 0 完成后：替换为真实 InferenceBackend，验证调度逻辑
3. 课题一完成后：替换 Mock Transport 为真实实现，端到端测试

---

## 背景

### 1. 国产算力挑战
- 国产算力（昇腾、寒武纪、海光、昆仑芯等）在算力架构、显存拓扑和互联带宽方面与 NVIDIA GPU 系不同。
- 传统 vLLM 的大一统调度策略无法自动适配国产硬件特性，大量算力被 Prefill/Decode 阶段的资源争抢和 KV Cache 的重复搬运所浪费。

### 2. sageLLM 现状
sageLLM Control Plane 已具备：
- **PD 路由** (`pd_routing.py`)：基于 threshold/adaptive 策略将请求分发到 PREFILLING/DECODING 实例
- **多调度策略** (`strategies/`)：FIFO、Priority、SLO-Aware、Cost-Optimized、Adaptive
- **实例类型** (`types.py`)：`ExecutionInstanceType` 支持 GENERAL/PREFILLING/DECODING/HYBRID/EMBEDDING/LLM_EMBEDDING
- **GPU 管理** (`gpu_manager.py`)：NVML 监控与逻辑预留

**当前缺口**：
- 无专用 Prefill/Decode 队列，PD 路由后仍共享调度循环
- 无 KV Cache 内存管理器（准入控制、配额分配、驱逐策略）
- 无分层缓存池（HBM↔DRAM↔SSD）与跨批次复用机制
- 监控指标未覆盖 KV Cache 压力、驱逐事件、复用命中率

### 3. 目标 KPI
| 指标 | 目标值 |
|------|--------|
| 单芯片有效算力 | ≥90% 理论峰值 |
| 相比 vLLM 吞吐提升 | ≥100% (2×) |
| TTFT/TPOT 提升 | ≥20% |
| 单位 token 成本下降 | ≥30% |
| 长上下文稳定性 | ≥32K 上下文保持性能 |

---

## 研究内容

### 1. PD 分离调度增强（计算分离）
**实现位置**：`sageLLM/control_plane/`

| 模块 | 描述 |
|------|------|
| `queues/prefill_queue.py` | Prefilling 专用队列，优化吞吐，支持 chunked prefill |
| `queues/decode_queue.py` | Decoding 专用队列，优化延迟，支持 continuous batching |
| `pd_routing.py` 增强 | 加入 AF (Autoregressive Fill) 分离路由 |
| `strategies/pd_separation.py` | PD/AF 分离调度策略，独立队列调度循环 |
| `chip_pool/` | 异构芯片池管理（GPU/NPU/CPU/ASIC 能力描述与亲和性） |
| `manager.py` 增强 | 多队列调度循环、实例-队列绑定 |

**关键能力**：
- Prefill 阶段：高 TP (4-8)，大批处理，优化吞吐
- Decode 阶段：低 TP (1)，高并发，优化延迟
- 支持异构芯片池的任务亲和性匹配与资源隔离

### 2. 分层 KV Cache 管理器

> **分层设计**：策略层在 `control_plane/memory_manager/`，实现层在 `sage_infer/kv_cache/`

**策略层**：`sageLLM/control_plane/memory_manager/`（新建）

| 模块 | 描述 |
|------|------|
| `admission_controller.py` | 准入控制策略，基于预测的请求准入决策 |
| `quota_allocator.py` | 内存配额分配策略，LLM/Embedding 动态预算 |
| `eviction_policy.py` | 驱逐策略（LRU/热点感知/SLO 感知） |
| `migration_planner.py` | 迁移决策，决定何时在 HBM↔DRAM↔SSD 间迁移 |

**实现层**：`sageLLM/sage_infer/kv_cache/`（新建，与课题三共建）

| 模块 | 描述 |
|------|------|
| `store.py` | KVStore 基类，定义存储接口 |
| `paged_store.py` | 分页存储实现，兼容 vLLM PagedAttention |
| `tiered_backend.py` | 分层存储后端（HBM Tier / DRAM Tier / SSD Spill）|
| `slice_registry.py` | KV Slice 注册表，索引可复用的上下文片段 |
| `block_manager_wrapper.py` | vLLM BlockManager 适配层，Hook 驱逐事件 |

**关键能力**：
- HBM（最快）→ 共享 DRAM（中等）→ SSD spill（最大）分层管理
- SLO 感知驱逐：结合请求优先级、deadline slack、重计算代价
- 与 `gpu_manager.py` 集成，实时监控各层利用率

### 3. 跨批次复用与热点预取

> **分层设计**：策略层在 `control_plane/cache_reuse/`，实现层在 `sage_infer/kv_cache/`

**策略层**：`sageLLM/control_plane/cache_reuse/`（新建）

| 模块 | 描述 |
|------|------|
| `reuse_policy.py` | 复用策略（精确前缀匹配 / 语义相似匹配） |
| `prefetch_scheduler.py` | 预取调度，根据访问热点决定预取时机 |

**实现层**：`sageLLM/sage_infer/kv_cache/`（复用上节模块）

| 模块 | 描述 |
|------|------|
| `prompt_fingerprint.py` | Prompt 指纹计算（prefix hash / semantic hash） |
| `slice_registry.py` | KV Slice 注册表，索引可复用的上下文片段 |
| `prefetch_worker.py` | 后台预取工作器，执行实际的数据加载 |

**关键能力**：
- 跨批次识别相同/相似 prompt 前缀，复用已计算的 KV Cache
- 热点预取：基于 `metrics_collector.py` 的访问模式分析，提前迁移热点数据
- 与分层缓存池协同，热点保护防止被驱逐

### 4. 指标监测与遥测
**实现位置**：`sageLLM/control_plane/` 现有模块增强

| 模块 | 增强内容 |
|------|---------|
| `types.py` | `RequestMetadata` 增加 `kv_cache_size_tokens`、`slo_slack_ms` |
| `types.py` | `ExecutionInstance` 增加 `kv_cache_usage_gb`、`eviction_count` |
| `metrics_collector.py` | 新增 KV Cache 压力、驱逐事件、复用命中率指标 |
| `monitoring.py` | 暴露 TTFT/TPOT/throughput/cache_hit_rate 端点 |

---

## 目标

### 算力利用
- PD/AF 阶段分离后，单芯片有效算力 ≥ 理论峰值的 90%
- 批混合场景中 GPU/NPU 占用波动 ≤ 10%

### 吞吐与延迟
- 相比同期 vLLM 吞吐能力 ≥ 2×
- TTFT（首字时延）提升 ≥ 20%
- TPOT（每字时延）提升 ≥ 20%

### 成本与缓存效率
- 单位 token 成本较国际主流开源框架下降 ≥ 30%
- KV Cache 跨批次复用命中率 ≥ 60%
- 热点迁移失败率 ≤ 5%

### 长上下文稳定性
- ≥32K 上下文压测中，分层缓存与热点预取保持吞吐波动 ≤ 15%
- 无大规模 OOM 或 SLO 违约

---

## 实现路径

> **分层架构**：策略层在 `control_plane/`，实现层在 `sage_infer/kv_cache/`

```
sageLLM/
├── control_plane/                   # 策略层
│   ├── queues/                      # 【新建】专用队列
│   │   ├── __init__.py
│   │   ├── prefill_queue.py
│   │   └── decode_queue.py
│   ├── chip_pool/                   # 【新建】异构芯片池
│   │   ├── __init__.py
│   │   ├── pool_manager.py
│   │   └── device_capability.py
│   ├── memory_manager/              # 【新建】KV Cache 调度策略
│   │   ├── __init__.py
│   │   ├── admission_controller.py  # 准入控制策略
│   │   ├── quota_allocator.py       # 配额分配策略
│   │   ├── eviction_policy.py       # 驱逐策略
│   │   └── migration_planner.py     # 迁移决策
│   ├── cache_reuse/                 # 【新建】缓存复用策略
│   │   ├── __init__.py
│   │   ├── reuse_policy.py          # 复用决策
│   │   └── prefetch_scheduler.py    # 预取调度
│   ├── strategies/
│   │   └── pd_separation.py         # 【新建】PD/AF 分离策略
│   ├── pd_routing.py                # 【增强】AF 路由支持
│   ├── manager.py                   # 【增强】多队列调度循环
│   ├── types.py                     # 【增强】KV Cache 相关字段
│   ├── metrics_collector.py         # 【增强】缓存指标
│   └── monitoring.py                # 【增强】遥测端点
│
└── sage_infer/
    ├── interfaces/                  # 【Phase 0 提供，本课题引用】
    │   ├── schemas.py               # KVCacheSchema, CapabilityDescriptor
    │   │   # - KVCacheSchema: 定义 KV 数据格式，用于分层存储配置
    │   │   # - CapabilityDescriptor: 实例能力描述，用于 PD 路由决策
    │   ├── inference_backend.py     # InferenceBackend Protocol
    │   │   # - get_kv_schema(): 获取后端 KV 格式
    │   │   # - get_capability(): 获取实例能力
    │   └── transport_contract.py    # KVChunk, TransportPlan
    │       # - 跨节点迁移时调用（依赖课题一）
    │
    └── kv_cache/                    # 【新建】KV Cache 存储实现
        ├── __init__.py
        ├── store.py                 # KVStore 基类
        ├── paged_store.py           # 分页存储实现
        ├── tiered_backend.py        # 分层存储后端
        ├── slice_registry.py        # KV Slice 索引
        ├── prompt_fingerprint.py    # Prompt 指纹计算
        ├── prefetch_worker.py       # 预取工作器
        └── block_manager_wrapper.py # vLLM 适配层
```

---

## 使用方式

1. 将本 Prompt 作为课题二的研究/实现入口
2. 策略层代码在 `sageLLM/control_plane/`，实现层代码在 `sageLLM/sage_infer/kv_cache/`
3. 在 PR/里程碑中引用本文档，确保与课题一（KV 传输库）、课题三（模型压缩）协同
4. 评测扩展在 `sage-benchmark/benchmark_control_plane/` 中进行
