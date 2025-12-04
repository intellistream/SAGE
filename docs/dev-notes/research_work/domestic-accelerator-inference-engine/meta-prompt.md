# Meta Prompt：面向国产算力的高性能推理引擎研究课题

> 本文档是分配给其他 Agent 撰写具体课题 prompt 的元提示。

---

## 项目总体背景

### 项目名称
**构建面向大规模国产算力的高性能推理引擎**

### 核心定位
基于 SAGE 框架，构建一个**独立的高性能 LLM 推理执行引擎（sageInfer）**，与 vLLM 对标竞争，将国产硬件作为一等公民进行深度优化。

**架构定位**：
```
┌─────────────────────────────────────────────────────────────────┐
│  sage-gateway / sage-cli (用户接口层)                            │
├─────────────────────────────────────────────────────────────────┤
│  sageLLM Control Plane (调度/路由/PD分离/多实例管理)              │
├─────────────────────────────────────────────────────────────────┤
│  ⭐ sageInfer - 新的推理执行引擎 ⭐                               │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐     │
│  │ KV Cache    │ Attention   │ 通信库       │ 硬件适配层   │     │
│  │ Manager     │ Backend     │ (RDMA/PCIe) │ (国产算力)   │     │
│  └─────────────┴─────────────┴─────────────┴─────────────┘     │
├─────────────────────────────────────────────────────────────────┤
│  底层算子库 (C++/CUDA/国产SDK)                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 总体目标
- 推理引擎单芯片有效算力逼近理论峰值的 **90%**
- 在典型应用场景下相比 vLLM 推理吞吐提升 **≥100%**
- 首字时延（TTFT）与每字时延（TPOT）提升 **≥20%**
- 单位 token 成本较 vLLM 降低 **≥30%**
- 长上下文场景（≥32K）下通过上下文缓存优化保持稳定性能

### 支持的国产硬件
- 华为昇腾 NPU (HCCS 互联)
- 寒武纪 MLU (MLU-Link 互联)
- 海光 DCU (xGMI 互联)
- 昆仑芯 XPU

---

## 课题划分

本项目分为 **Phase 0（公共基础设施）+ 三个子课题**，请分别撰写各课题的详细 prompt：

| 阶段/课题 | 名称 | 产出模块 | 负责人 | 状态 |
|-----------|------|----------|--------|------|
| **Phase 0** | 公共基础设施与接口解耦 | `sageInfer/interfaces/` + `sageInfer/backends/` | TBD | 🔴 必需前置 |
| 课题一 | 高性能通信库与 KV 传输 | `sageInfer/transport/` | TBD | 依赖 Phase 0 |
| 课题二 | KV Cache 管理与调度优化 | `sageLLM/control_plane/` + `sageInfer/kv_cache/` | TBD | 依赖 Phase 0 |
| 课题三 | 模型压缩技术 | `sageInfer/quantization/` + `sageInfer/pruning/` | TBD | 依赖 Phase 0 |

---

## Phase 0：公共基础设施（必需前置）

### 目标
在正式启动三个课题之前，必须先完成 Phase 0，建立统一的接口层与数据结构，确保：
1. **解耦 vLLM 依赖**：定义 `InferenceBackend` 抽象接口，实现 `VLLMBackendAdapter`
2. **统一数据结构**：`KVCacheSchema`、`CapabilityDescriptor`、`TransportPlan`、`QuantizationProfile`
3. **硬件抽象层**：`sageInfer/hal/` 提供国产硬件能力查询的统一 API
4. **CLI 扩展**：`sage infer` 命令空间

### 产出模块
```
sageInfer/
├── interfaces/
│   ├── inference_backend.py    # InferenceBackend Protocol
│   ├── schemas.py              # 共享数据结构
│   └── transport_contract.py   # KVChunk / TransportPlan
├── backends/
│   └── vllm_adapter.py         # vLLM 适配器（验证解耦有效）
├── hal/
│   └── accelerator_descriptor.py
└── cli/
    └── commands.py             # sage infer ...
```

### 完成标准
- [ ] `InferenceBackend` 接口能驱动 vLLM 正常推理，性能无回退 (±3%)
- [ ] 三个课题的 prompt 均引用 Phase 0 定义的接口，无重复定义
- [ ] `sage infer backends:list` 命令可用

### Prompt 文件
- `task0-common-infrastructure/prompt.md`

---

## 课题并行性与执行顺序

### 依赖关系图
```
                         Phase 0 (公共基础设施)
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
           课题二           课题一           课题三
        (PD分离/Cache)    (通信库)        (模型压缩)
              │               │               │
              │◄──────────────┤               │
              │   需要传输接口 │               │
              │               │◄──────────────┤
              │               │   需要量化格式 │
              └───────────────┴───────────────┘
                              │
                              ▼
                     sageInfer 集成测试
```

### 推荐执行策略

| 阶段 | 时间 | 内容 | 并行度 |
|------|------|------|--------|
| **Phase 0** | 1-2 周 | 接口定义、vLLM 解耦、HAL 骨架 | 串行（必需） |
| **Phase 1** | 4-6 周 | 课题二 + 课题三 并行 | ⭐⭐ 并行 |
| **Phase 2** | 4-6 周 | 课题一 实现 + 课题三 在线集成 | ⭐⭐ 并行 |
| **Phase 3** | 2-4 周 | 三课题集成测试 + 性能调优 | 串行 |

### 为什么推荐「先课题二 → 再课题一」？
1. **课题二定义需求**：PD 分离调度和 KV Cache 管理决定了"需要什么样的传输接口"
2. **课题一提供实现**：通信库是"怎么高效传输"，需要先知道传什么
3. **课题三相对独立**：量化工具链可离线运行，不强依赖在线调度

### 各课题可并行的前提
- Phase 0 已完成，提供 `KVCacheSchema`、`TransportPlan`、`CapabilityDescriptor`
- 课题之间通过 **接口契约** 而非 **具体实现** 交互
- 未完成的依赖模块可用 **Mock 实现** 代替

---

## 各课题 Prompt 撰写要求

请为每个课题撰写独立的 `prompt.md` 文件，放置在对应目录下：
- `task0-common-infrastructure/prompt.md` ← **Phase 0（必需前置）**
- `task1-kv-transport/prompt.md`
- `task2-pd-separation/prompt.md` ← 原 task2-kv-cache-scheduling
- `task3-model-compression/prompt.md`

### Prompt 结构模板

每个课题的 prompt 必须包含以下部分：

```markdown
# Prompt · 课题X：[课题名称]

你是一名负责 SAGE/sageInfer 推理引擎开发的系统架构师，请依据以下背景与要求，输出详细的技术方案与实验路线。

---

## 背景（Background）
### 项目定位
[说明本课题在整体架构中的位置]

### 问题背景
[描述要解决的核心问题]

### 现有技术基础
[SAGE/sageLLM 中可复用的模块]

---

## 研究内容（Research Scope）
### 1. [子任务1名称]
[详细描述]

### 2. [子任务2名称]
[详细描述]

...

---

## 模块设计（Module Design）
### 目录结构建议
[代码组织结构]

### 核心接口定义
[关键 API/数据结构]

---

## 研究目标（Success Criteria）
### 性能指标
[量化目标表格]

### 工程化指标
[交付物要求]

---

## 交付物要求
1. 设计文档
2. 核心代码
3. 性能评估报告
4. 可重复实验脚本
```

---

## 课题一：高性能通信库与 KV 传输

### 课题目标
研发高性能通信库，实现国产硬件的高速 KV Cache 传输与格式转换。

### 核心任务
1. **国产硬件互联拓扑适配**
   - HCCS / MLU-Link / xGMI / PCIe 拓扑检测与带宽建模
   - 硬件描述符设计（带宽、包长限制、SRAM 窗口、DMA 对齐）

2. **高性能传输引擎**
   - 零拷贝 KV 流水线（chunking + overlap）
   - 多后端支持：RDMA/RoCE、PCIe DMA、共享内存
   - 传输带宽利用率目标 ≥85%

3. **混合精度格式转换**
   - FP8/INT4 ↔ FP16/FP32 自动转换内核
   - 转换开销目标 < 总推理时间的 5%

### 产出模块
```
sageInfer/
└── transport/
    ├── __init__.py
    ├── engine.py              # 传输引擎
    ├── backends/
    │   ├── rdma.py            # RDMA 后端
    │   ├── pcie.py            # PCIe DMA 后端
    │   └── shm.py             # 共享内存后端
    ├── hardware/
    │   ├── topology.py        # 拓扑检测
    │   ├── ascend.py          # 昇腾适配
    │   ├── cambricon.py       # 寒武纪适配
    │   ├── hygon.py           # 海光适配
    │   └── kunlunxin.py       # 昆仑芯适配
    └── format/
        ├── converter.py       # 格式转换器
        └── kernels/           # C++/CUDA 内核
```

---

## 课题二：KV Cache 管理与调度优化

### 课题目标
研究计算分离（PD分离和AF分离等）调度优化与上下文缓存机制，实现 KV Cache 的池化与分层管理、跨批次复用和热点预取。

### 核心任务
1. **KV Cache 池化与分层管理**
   - 多级存储：HBM → DDR → SSD
   - 动态分配与回收策略
   - 内存碎片优化

2. **跨批次复用与热点预取**
   - Prefix caching（公共前缀共享）
   - 热点 KV 预取策略
   - 基于访问模式的缓存淘汰

3. **PD/AF 分离调度优化**
   - Prefilling/Decoding 分离路由
   - Attention/FFN 分离调度（可选）
   - 与 sageLLM Control Plane 集成

4. **软硬协同加速**
   - 利用国产硬件的特殊能力（如昇腾的 DVPP、寒武纪的 MLU 通信原语）
   - 异构内存管理（HBM + DDR 统一寻址）

### 产出模块
```
sageInfer/
└── kv_cache/
    ├── __init__.py
    ├── pool_manager.py        # 池化管理器
    ├── hierarchical_store.py  # 分层存储
    ├── prefix_cache.py        # 前缀缓存
    ├── prefetch.py            # 热点预取
    └── eviction.py            # 淘汰策略

sageLLM/control_plane/
├── pd_routing.py              # (扩展) PD 分离路由
└── kv_aware_scheduler.py      # (新增) KV 感知调度器
```

---

## 课题三：模型压缩技术

### 课题目标
研究模型压缩技术，如剪枝、量化和知识蒸馏，保持推理精度的同时减少显存占用。

### 核心任务
1. **量化技术**
   - 权重量化：INT8/INT4/FP8
   - KV Cache 量化：FP8/INT4
   - 激活量化与校准

2. **剪枝技术**
   - 结构化剪枝（Attention head、FFN 通道）
   - 非结构化稀疏
   - 与国产硬件稀疏加速能力结合

3. **知识蒸馏**（可选）
   - 在线蒸馏
   - 层级蒸馏

4. **压缩模型推理优化**
   - 量化算子融合
   - 稀疏矩阵高效计算
   - 混合精度推理策略

### 产出模块
```
sageInfer/
└── quantization/
    ├── __init__.py
    ├── weight_quant.py        # 权重量化
    ├── kv_quant.py            # KV Cache 量化
    ├── activation_quant.py    # 激活量化
    ├── calibration.py         # 校准工具
    └── kernels/               # 量化算子内核

sageInfer/
└── pruning/
    ├── __init__.py
    ├── structured.py          # 结构化剪枝
    └── sparse.py              # 稀疏化
```

---

## 各课题关联性

```
                         Phase 0 (公共基础设施)
                    ┌────────────────────────────────┐
                    │  InferenceBackend 接口          │
                    │  KVCacheSchema / Capability    │
                    │  HAL / CLI                     │
                    └────────────────┬───────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
              ▼                      ▼                      ▼
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │  课题一          │    │  课题二          │    │  课题三          │
    │  通信库          │    │  PD分离/Cache   │    │  模型压缩        │
    │  KV传输          │◄───│  管理           │◄───│  量化/稀疏       │
    └────────┬────────┘    └────────┬────────┘    └────────┬────────┘
             │                      │                      │
             │ 提供高速 KV 传输      │ KV Cache 量化存储     │
             │◄─────────────────────│◄─────────────────────│
             │                      │                      │
             └──────────────────────┴──────────────────────┘
                                    │
                                    ▼
                     ┌─────────────────────────────┐
                     │  sageInfer 统一推理引擎      │
                     │  (替代 vLLM 的国产化方案)    │
                     └─────────────────────────────┘
```

### 接口依赖关系
| 消费方 | 依赖的接口/Schema | 提供方 |
|--------|-------------------|--------|
| 课题一 | `KVCacheSchema`, `TransportPlan` | Phase 0 |
| 课题二 | `InferenceBackend`, `CapabilityDescriptor`, `KVCacheSchema` | Phase 0 |
| 课题三 | `QuantizationProfile`, `KVCacheSchema` | Phase 0 |
| 课题二 | `TransportEngine` (Mock → 真实) | 课题一 |
| 课题一/二 | `QuantizationProfile`, KV 压缩格式 | 课题三 |

---

## Agent 任务分配

### Agent 0 - Phase 0 公共基础设施
- 输出文件：`task0-common-infrastructure/prompt.md`
- 重点：vLLM 解耦、InferenceBackend 接口、共享 Schema、HAL 骨架、CLI 扩展
- **优先级：最高（阻塞其他课题）**

### Agent 1 - 课题一 Prompt 撰写
- 输出文件：`task1-kv-transport/prompt.md`
- 重点：传输引擎架构、硬件适配接口、格式转换内核设计
- **前置依赖**：Phase 0 的 `KVCacheSchema`, `TransportPlan`

### Agent 2 - 课题二 Prompt 撰写
- 输出文件：`task2-pd-separation/prompt.md`
- 重点：KV Cache 生命周期管理、与 Control Plane 集成、分层存储策略
- **前置依赖**：Phase 0 的 `InferenceBackend`, `CapabilityDescriptor`

### Agent 3 - 课题三 Prompt 撰写
- 输出文件：`task3-model-compression/prompt.md`
- 重点：量化方案选型、与国产硬件量化加速能力结合、精度保持策略
- **前置依赖**：Phase 0 的 `QuantizationProfile`, `KVCacheSchema`

---

## 参考资源

### SAGE 代码库位置
- sageLLM Control Plane: `packages/sage-common/src/sage/common/components/sage_llm/sageLLM/control_plane/`
- sageInfer (待创建): `packages/sage-common/src/sage/common/components/sage_infer/`

### 相关论文/项目
- vLLM: PagedAttention, Prefix Caching
- SGLang: RadixAttention
- TensorRT-LLM: 量化推理
- FlashAttention: 高效注意力计算
- DistServe/Mooncake: PD 分离

### SAGE 文档
- 架构文档: `docs-public/docs_src/dev-notes/package-architecture.md`
- Copilot 指南: `.github/copilot-instructions.md`
