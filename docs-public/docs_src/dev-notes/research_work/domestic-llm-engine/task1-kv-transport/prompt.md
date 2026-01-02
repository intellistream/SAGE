# Prompt · 课题一 / PR6：通信与 KV 传输（comm_backend）

你是一名负责 **comm_backend** 的系统架构师。请基于最新 `sageLLM` 模块化架构，给出可落地的设计与实验方案，聚焦通信拓扑、融合/重叠、KV 传输与格式转换，兼顾国产算力与
CUDA 环境。

______________________________________________________________________

## 前置依赖

- 协议/类型：`KVCacheSchema`, `KVBackendProtocol`, `CommBackendProtocol`, `TransferPlan`, `KVChunk`,
  `TopologyInfo`（来自 PR1）。
- 引擎 Hook：LMDeploy `kv_manager`/`scheduler` 已按补丁开放通信拦截点；通过 `SagePorts` 取端口，禁止硬编码。
- Mock 路径：CI 使用 mock 通信后端；GPU/国产卡环境跑真实 NCCL/Gloo/RDMA。

______________________________________________________________________

## 背景与目标

- 角色：`comm_backend/` 作为统一通信后端，提供拓扑感知、通信融合、计算-通信重叠、跨节点 KV/状态传输。
- 目标：
  - 带宽利用率 ≥85%；同节点延迟 ≤20µs，跨节点 ≤80µs。
  - TTFT/TPOT 改善 ≥10%（通信贡献）；长上下文 32K-128K 吞吐 ≥ vLLM baseline ×2。
  - 占比可观测：Prometheus/Gateway 显示通信占 step time 的比例、失败率。

______________________________________________________________________

## 研究内容（Scope）

1. **拓扑与配置**

- `TopologyManager`：探测 NVLink/PCIe/HCCS/MLU-Link/xGMI/InfiniBand，输出 `TopologyInfo`（带宽/延迟/Hop/NUMA）。
- `TransportProfile`：结合拓扑生成 DMA/RDMA 配置（对齐、QP、max_packet、zero_copy）。

2. **通信后端协议与实现**

- `CommBackendProtocol`: `all_reduce/all_gather/send/recv/broadcast` + `KVTransferChannel.transfer`。
- 后端实现：`nccl_backend`、`gloo_backend`、`rdma_backend`、`mock_backend`；国产卡可占位适配。
- `CommFusion` + `OverlapWindow`：融合/重叠策略（prefill/decoding/kv-migration），可由 scheduler_ir 下发策略。

3. **KV 传输与格式转换协同**

- `KVTransferChannel` 支持 chunking + pipeline + 优先级队列；可选压缩/量化（FP8/INT4）由 accel 配合。
- 与 `kv_runtime` 协议对齐：迁移计划、碎片/配额反馈；兼容 LMDeploy `migrate_blocks` Hook。

4. **遥测与控制**

- `telemetry.py` 输出带宽、延迟、重传、融合/重叠命中率；Prometheus 指标；Gateway 仪表卡片。
- Control Plane 可动态调节 chunk_size/并发度/融合开关；暴露 debug trace。

5. **CLI & Preset**

- `KVTransportConfig`（backend, target_dtype, chunk_size, overlap_streams, prefetch_depth, zero_copy,
  compression, preset）。
- CLI：`sage llm serve --comm-backend preset=high-bw --kv-dtype=fp8_e4m3`；`sage infer transport probe`
  输出拓扑与推荐 preset。

______________________________________________________________________

## 目录结构（硬约束）

```
comm_backend/
├── __init__.py
├── config.py              # KVTransportConfig / presets
├── protocol.py            # CommBackendProtocol, KVTransferChannel
├── topology.py            # TopologyManager, TopologyInfo
├── fusion.py              # CommFusion / OverlapWindow
├── telemetry.py           # 指标上报
├── backends/
│   ├── __init__.py
│   ├── nccl_backend.py
│   ├── gloo_backend.py
│   ├── rdma_backend.py
│   └── mock_backend.py
└── hardware/
    ├── __init__.py
    ├── transport_profile.py
    └── domestic/
        ├── ascend.py
        ├── cambricon.py
        ├── hygon.py
        └── kunlunxin.py
```

______________________________________________________________________

## Success Criteria

- 性能：带宽利用率 ≥85%；TTFT/TPOT 改善 ≥10%；32K-128K 吞吐 ≥ vLLM ×2；通信占比可观测。
- 工程化：
  - CLI preset ≥3（High-BW/Low-Latency/Low-Cost）。
  - Mock 后端可跑 CI；NCCL/Gloo/RDMA 可在 GPU/国产卡环境验证。
  - 遥测接入 `sage-gateway`；配置通过 `SagePorts`。
- 兼容性：接口与 `kv_runtime` / `scheduler_ir` / `engines.lmdeploy` Hook 对齐，零硬编码旧路径。

______________________________________________________________________

## 交付物

1. 设计文档：拓扑矩阵、协议、融合/重叠策略、遥测、preset。
1. 核心代码：`comm_backend` 全量实现 + CLI/Gateway 集成（如需）。
1. 测试：单测（protocol、planner、fusion、mock），集成测（LMDeploy patched + mock/NCCL），长上下文 KV 迁移压测。
1. Benchmark：带宽/延迟曲线，32K-128K 吞吐，对比 vLLM baseline；输出 JSON/Markdown。
1. Preset：`kv_transport_presets.yaml` + 推荐硬件清单。
