# Research Proposal: SLO-Aware KV Cache Management for Collocated LLM-Embedding Services

> **Status**: Draft\
> **Created**: 2025-12-02\
> **Target Venues**: OSDI 2025 / SOSP 2025 / EuroSys 2026 / NSDI 2026

______________________________________________________________________

## 1. 研究背景与动机

### 1.1 问题背景

现代 AI 应用（RAG、Agent、多模态问答）通常需要同时部署 LLM 推理服务和 Embedding 服务。为了降低成本和提高资源利用率，业界趋向于将两者**共置 (Collocate)**
在同一 GPU 资源池中。

然而，这种共置部署面临严峻挑战：

```
┌─────────────────────────────────────────────────────────────┐
│                    GPU Memory (e.g., 80GB)                   │
├─────────────────────────────────────────────────────────────┤
│  Model Weights   │   KV Cache (LLM)   │  Embedding Workspace │
│    (固定)        │    (动态增长)       │     (动态波动)        │
│    ~40GB         │    0-30GB          │     0-10GB           │
└─────────────────────────────────────────────────────────────┘
                          ↑
                   核心矛盾点：
            KV Cache 和 Embedding 争抢剩余显存
```

### 1.2 现有工作的局限

| 现有工作                  | 关注点                | 局限                       |
| ------------------------- | --------------------- | -------------------------- |
| **vLLM (PagedAttention)** | LLM KV Cache 内存效率 | 未考虑与 Embedding 共置    |
| **DistServe/Mooncake**    | Prefill-Decode 分离   | 物理隔离，无法共享 GPU     |
| **ICLR 2026 在审**        | 同架构 Batch 合并     | 架构约束强，未解决内存竞争 |
| **S-LoRA**                | 多 LoRA 适配器管理    | 未涉及 Embedding 工作负载  |

**关键空白**：**没有工作研究 LLM KV Cache 与 Embedding 工作负载共置时的内存管理问题**。

### 1.3 核心洞察

我们观察到以下关键特征差异：

| 特征           | LLM KV Cache              | Embedding 工作负载     |
| -------------- | ------------------------- | ---------------------- |
| **内存模式**   | 逐 token 增长，生命周期长 | 批量分配，生命周期短   |
| **可预测性**   | 输出长度难预测            | 批大小已知，完全可预测 |
| **可驱逐性**   | 驱逐代价高（需重计算）    | 无状态，计算完即释放   |
| **SLO 敏感度** | TTFT/TPOT 敏感            | 批处理延迟容忍度较高   |

**核心洞察**：Embedding 的**完全可预测性**可以用来指导 LLM KV Cache 的管理决策，而不是简单地争抢资源。

______________________________________________________________________

## 2. 问题形式化

### 2.1 系统模型

考虑一个 GPU 资源池，总显存容量为 $M$，已被模型权重占用 $M_w$，可用显存为 $M\_{avail} = M - M_w$。

**请求模型**：

- LLM 请求 $r_l = (t\_{arr}, p\_{len}, o\_{len}, slo_l)$：到达时间、prompt 长度、输出长度（未知）、SLO
- Embedding 请求 $r_e = (t\_{arr}, n\_{texts}, d\_{dim}, slo_e)$：到达时间、文本数量、向量维度、SLO

**内存需求**：

- LLM 请求 $r_l$ 的 KV Cache：$m_l(t) = 2 \\cdot n\_{layers} \\cdot d\_{head} \\cdot (p\_{len} +
  tokens_generated(t))$
- Embedding 批次 $B_e$：$m_e(B_e) = batch_size \\cdot max_seq_len \\cdot d\_{model}$

### 2.2 优化目标

**多目标优化问题**：

$$ \\max \\quad \\alpha \\cdot SLO_Attainment\_{LLM} + \\beta \\cdot SLO_Attainment\_{Emb} + \\gamma
\\cdot Throughput $$

Subject to:

$$ \\sum\_{r_l \\in Active} m_l(t) + \\sum\_{B_e \\in Running} m_e(B_e) \\leq M\_{avail}, \\quad
\\forall t $$

其中：

- $SLO_Attainment\_{LLM} = \\frac{|{r_l : TTFT < slo_l.ttft \\land TPOT < slo_l.tpot}|}{|R_l|}$
- $SLO_Attainment\_{Emb} = \\frac{|{r_e : Latency < slo_e.deadline}|}{|R_e|}$

### 2.3 问题复杂度

**定理 1**：混合工作负载的 SLO 感知内存分配问题是 **NP-Hard**。

**证明思路**：可从带期限的背包问题 (Knapsack with Deadlines) 规约。每个请求对应一个物品，内存需求对应重量，SLO 满足对应价值，显存容量对应背包容量。由于 LLM
输出长度未知，问题具有在线特性，进一步增加复杂度。

______________________________________________________________________

## 3. 核心方法

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Unified Request Queue                         │
│         (LLM Chat / LLM Batch / Embedding Requests)             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Predictive Memory Planner                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Output Length   │  │ Embedding Load  │  │ Memory Budget   │  │
│  │ Predictor       │  │ Forecaster      │  │ Allocator       │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              SLO-Aware KV Cache Manager (核心贡献)               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Admission Control: 基于预测的请求准入决策                    ││
│  │  Quota Allocation: LLM/Embedding 动态内存配额                ││
│  │  Preemption Policy: SLO 感知的 KV Cache 驱逐策略             ││
│  │  Speculative Reservation: 为高优先级请求预留空间             ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GPU Execution Engine                        │
│            (vLLM Backend + Embedding Backend)                    │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 核心算法 1：Embedding-Aware KV Cache Admission Control

**动机**：传统的 KV Cache 管理只看当前状态，不考虑即将到来的 Embedding 批次。

**算法思想**：利用 Embedding 请求的可预测性，在 LLM 请求准入时**预留**未来 Embedding 批次所需的内存。

```
Algorithm 1: Embedding-Aware Admission Control
────────────────────────────────────────────────
Input:
  - new_llm_request r_l
  - pending_embedding_queue Q_e
  - current_memory_usage m_current
  - available_memory M_avail

Output:
  - ADMIT or REJECT or DEFER

1:  # 预测新请求的 KV Cache 需求
2:  predicted_output_len = OutputPredictor.predict(r_l.prompt)
3:  predicted_kv_memory = compute_kv_size(r_l.prompt_len + predicted_output_len)
4:  
5:  # 预测近期 Embedding 批次的内存需求
6:  future_window = estimate_completion_time(r_l, predicted_output_len)
7:  embedding_memory_forecast = 0
8:  for batch in Q_e where batch.expected_start < future_window:
9:      embedding_memory_forecast += compute_embedding_memory(batch)
10:
11: # 计算安全内存阈值
12: safety_margin = M_avail * SAFETY_RATIO  # e.g., 10%
13: required_memory = predicted_kv_memory + embedding_memory_forecast + safety_margin
14:
15: if m_current + required_memory <= M_avail:
16:     return ADMIT
17: elif r_l.priority == HIGH and can_preempt_low_priority():
18:     return ADMIT_WITH_PREEMPTION
19: elif r_l.slo.deadline - current_time > DEFER_THRESHOLD:
20:     return DEFER  # 等待内存释放
21: else:
22:     return REJECT
```

### 3.3 核心算法 2：SLO-Driven Dynamic Memory Quota

**动机**：静态划分 LLM/Embedding 内存配额无法适应动态工作负载。

**算法思想**：基于**队列状态**和 **SLO 紧迫度**动态调整内存配额。

```
Algorithm 2: SLO-Driven Quota Adjustment
────────────────────────────────────────────────
Input:
  - llm_queue_state: {pending, running, slo_violations}
  - embedding_queue_state: {pending, running, slo_violations}
  - current_quota: {llm_quota, embedding_quota}

Output:
  - new_quota: {llm_quota, embedding_quota}

1:  # 计算 SLO 紧迫度分数
2:  llm_urgency = compute_urgency(llm_queue_state)
3:  embedding_urgency = compute_urgency(embedding_queue_state)
4:  
5:  # 基于紧迫度重新分配
6:  total_flexible = M_avail - MIN_LLM_QUOTA - MIN_EMBEDDING_QUOTA
7:  
8:  if llm_urgency + embedding_urgency == 0:
9:      # 无紧迫请求，按默认比例
10:     llm_share = DEFAULT_LLM_RATIO
11: else:
12:     llm_share = llm_urgency / (llm_urgency + embedding_urgency)
13:
14: # 平滑调整，避免震荡
15: new_llm_quota = MIN_LLM_QUOTA + total_flexible * llm_share
16: new_llm_quota = smooth_adjust(current_quota.llm, new_llm_quota, MAX_CHANGE_RATE)
17: new_embedding_quota = M_avail - new_llm_quota
18:
19: return {new_llm_quota, new_embedding_quota}

Function compute_urgency(queue_state):
    urgency = 0
    for request in queue_state.pending + queue_state.running:
        time_to_deadline = request.slo.deadline - current_time
        estimated_completion = estimate_completion_time(request)
        slack = time_to_deadline - estimated_completion
        if slack < 0:
            urgency += VIOLATION_WEIGHT * abs(slack)
        elif slack < CRITICAL_THRESHOLD:
            urgency += CRITICAL_WEIGHT / (slack + 1)
    return urgency
```

### 3.4 核心算法 3：SLO-Aware KV Cache Eviction

**动机**：当内存不足时，需要驱逐 KV Cache。传统 LRU/FIFO 策略不考虑 SLO。

**算法思想**：结合**请求优先级**、**SLO 松弛度**和**重计算代价**设计驱逐策略。

```
Algorithm 3: SLO-Aware Eviction Policy
────────────────────────────────────────────────
Input:
  - active_requests: list of LLM requests with KV Cache
  - memory_needed: amount of memory to free
  - incoming_request: the request causing eviction (optional)

Output:
  - eviction_list: requests to evict

1:  # 计算每个请求的驱逐代价
2:  eviction_costs = []
3:  for r in active_requests:
4:      # SLO 松弛度：距离 deadline 的时间
5:      slack = r.slo.deadline - (current_time + estimated_remaining_time(r))
6:  
7:      # 重计算代价：已生成的 token 数
8:      recompute_cost = r.generated_tokens * RECOMPUTE_WEIGHT
9:  
10:     # 优先级因子
11:     priority_factor = PRIORITY_WEIGHTS[r.priority]
12:  
13:     # 综合驱逐代价（越高越不应该驱逐）
14:     cost = priority_factor * (1 / (slack + ε)) + recompute_cost
15:     eviction_costs.append((r, cost, r.kv_cache_size))
16:
17: # 按代价升序排序（先驱逐代价低的）
18: eviction_costs.sort(key=lambda x: x[1])
19:
20: # 贪心选择直到释放足够内存
21: eviction_list = []
22: freed_memory = 0
23: for r, cost, size in eviction_costs:
24:     if freed_memory >= memory_needed:
25:         break
26:     # 保护即将完成的请求
27:     if r.estimated_remaining_tokens < COMPLETION_THRESHOLD:
28:         continue
29:     eviction_list.append(r)
30:     freed_memory += size
31:
32: return eviction_list
```

### 3.5 理论分析

**定理 2 (Admission Control 的有效性)**：在 Embedding 负载可准确预测的情况下，Algorithm 1 可以将内存溢出导致的 SLO 违反率降低至
$O(\\frac{1}{n})$，其中 $n$ 是预测窗口内的请求数。

**定理 3 (Quota Adjustment 的稳定性)**：Algorithm 2 在 smooth_adjust 的约束下，内存配额变化满足 Lyapunov 稳定性条件，不会产生震荡。

**定理 4 (Eviction Policy 的竞争比)**：在请求优先级均匀分布的情况下，Algorithm 3 相对于离线最优策略的竞争比为 $O(\\log k)$，其中 $k$
是优先级级别数。

______________________________________________________________________

## 4. 系统实现

### 4.1 SAGE 集成架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         SAGE Framework                           │
├─────────────────────────────────────────────────────────────────┤
│  sage-common/components/sage_llm/sageLLM/                       │
│  ├── control_plane/                                              │
│  │   ├── memory_manager/           ← 新增：核心贡献              │
│  │   │   ├── admission_controller.py                            │
│  │   │   ├── quota_allocator.py                                 │
│  │   │   ├── eviction_policy.py                                 │
│  │   │   └── memory_monitor.py                                  │
│  │   ├── predictors/               ← 新增：预测组件              │
│  │   │   ├── output_length_predictor.py                         │
│  │   │   └── embedding_load_forecaster.py                       │
│  │   ├── strategies/                                             │
│  │   │   └── hybrid_policy.py      ← 扩展：集成内存感知          │
│  │   └── manager.py                ← 扩展：内存管理集成          │
│  └── unified_client.py                                           │
├─────────────────────────────────────────────────────────────────┤
│  sage-benchmark/benchmark_control_plane/                         │
│  └── memory_benchmark/             ← 新增：内存管理评测          │
│      ├── workload_generator.py                                   │
│      ├── memory_metrics.py                                       │
│      └── slo_analyzer.py                                         │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 关键实现细节

#### 4.2.1 内存监控机制

```python
class MemoryMonitor:
    """实时监控 GPU 显存使用"""

    def __init__(self, device_id: int, sample_interval_ms: float = 10):
        self.device_id = device_id
        self.sample_interval = sample_interval_ms
        self.kv_cache_tracker = KVCacheTracker()
        self.embedding_tracker = EmbeddingMemoryTracker()

    def get_memory_snapshot(self) -> MemorySnapshot:
        return MemorySnapshot(
            total=torch.cuda.get_device_properties(self.device_id).total_memory,
            allocated=torch.cuda.memory_allocated(self.device_id),
            reserved=torch.cuda.memory_reserved(self.device_id),
            kv_cache_usage=self.kv_cache_tracker.get_usage(),
            embedding_usage=self.embedding_tracker.get_usage(),
            timestamp=time.time(),
        )
```

#### 4.2.2 与 vLLM 的集成

```python
class SLOAwareBlockManager:
    """扩展 vLLM 的 BlockManager，集成 SLO 感知驱逐"""

    def __init__(self, vllm_block_manager, eviction_policy: SLOAwareEvictionPolicy):
        self.base_manager = vllm_block_manager
        self.eviction_policy = eviction_policy

    def allocate(self, request: LLMRequest) -> Optional[BlockAllocation]:
        # 先尝试直接分配
        allocation = self.base_manager.try_allocate(request.num_blocks_needed)
        if allocation:
            return allocation

        # 内存不足，触发 SLO 感知驱逐
        eviction_list = self.eviction_policy.select_victims(
            active_requests=self.get_active_requests(),
            memory_needed=request.num_blocks_needed * BLOCK_SIZE,
            incoming_request=request,
        )

        for victim in eviction_list:
            self.evict(victim)

        return self.base_manager.try_allocate(request.num_blocks_needed)
```

______________________________________________________________________

## 5. 实验设计

### 5.1 实验环境

| 配置项    | 规格                                          |
| --------- | --------------------------------------------- |
| GPU       | NVIDIA A100 80GB / H100 80GB                  |
| 模型      | LLaMA-2-7B/13B/70B, Qwen2.5-7B/72B            |
| Embedding | BGE-M3, E5-Large, GTE-Large                   |
| Baseline  | vLLM, DistServe, Mooncake, ICLR 2026 在审工作 |

### 5.2 工作负载设计

#### 5.2.1 合成工作负载

| 参数               | 范围                                      |
| ------------------ | ----------------------------------------- |
| LLM:Embedding 比例 | 1:9, 3:7, 5:5, 7:3, 9:1                   |
| 请求到达模式       | Poisson, Bursty, Periodic                 |
| LLM 输出长度分布   | 短 (50-100), 中 (200-500), 长 (1000-2000) |
| Embedding 批大小   | 16, 32, 64, 128                           |

#### 5.2.2 真实工作负载

- **Azure LLM Traces** (BurstGPT 数据集)
- **Embedding Production Logs** (自采集或公开数据集)

### 5.3 评估指标

| 指标类别       | 具体指标                                  |
| -------------- | ----------------------------------------- |
| **SLO 达成率** | LLM TTFT P99, LLM TPOT P99, Embedding P99 |
| **吞吐量**     | Requests/sec, Tokens/sec                  |
| **资源效率**   | GPU 利用率, 显存利用率, KV Cache 命中率   |
| **公平性**     | 不同优先级请求的 SLO 达成率差异           |

### 5.4 关键实验

**实验 1：SLO 达成率对比**

- 对比不同系统在相同 SLO 约束下的达成率
- 变量：工作负载强度 (50%-150% of capacity)

**实验 2：内存压力测试**

- 人为制造高内存压力（大量长输出 LLM + 大批量 Embedding）
- 观察各系统的退化行为

**实验 3：预测准确性影响**

- 消融实验：对比有/无预测组件的性能差异
- 分析预测误差与系统性能的关系

**实验 4：扩展性测试**

- 单 GPU → 多 GPU → 多节点
- 分析通信开销和一致性维护成本

**实验 5：与 ICLR 工作的直接对比**

- 在其支持的场景（同架构模型）下进行公平对比
- 在其不支持的场景（异构模型）下展示我们的优势

______________________________________________________________________

## 6. 预期贡献

### 6.1 学术贡献

1. **问题形式化**：首次形式化定义 LLM-Embedding 共置场景下的 SLO 感知内存管理问题
1. **理论分析**：证明问题 NP-Hard，并给出近似算法及竞争比分析
1. **新算法**：
   - Embedding-Aware Admission Control
   - SLO-Driven Dynamic Memory Quota
   - SLO-Aware KV Cache Eviction Policy
1. **系统洞察**：揭示 Embedding 可预测性如何指导 LLM 内存管理

### 6.2 系统贡献

1. **SAGE 集成实现**：完整的系统原型
1. **与 vLLM 的无缝集成**：可直接用于生产环境
1. **开源代码和数据集**

### 6.3 实验贡献

1. **全面的基准测试**：对比所有 SOTA 系统
1. **真实工作负载验证**：不仅限于合成测试

______________________________________________________________________

## 7. 时间规划

| 阶段     | 任务                  | 时间                |
| -------- | --------------------- | ------------------- |
| Phase 1  | 问题形式化 + 理论分析 | 4 周                |
| Phase 2  | 核心算法设计与实现    | 6 周                |
| Phase 3  | SAGE 系统集成         | 4 周                |
| Phase 4  | 实验评估              | 6 周                |
| Phase 5  | 论文撰写              | 4 周                |
| **总计** |                       | **24 周 (~6 个月)** |

______________________________________________________________________

## 8. 目标会议

| 优先级 | 会议             | 截止日期 (预估) |
| ------ | ---------------- | --------------- |
| 1      | **OSDI 2025**    | 2025 年 5 月    |
| 2      | **SOSP 2025**    | 2025 年 4 月    |
| 3      | **EuroSys 2026** | 2025 年 10 月   |
| 4      | **NSDI 2026**    | 2025 年 9 月    |

______________________________________________________________________

## 9. 风险与应对

| 风险                    | 应对策略                            |
| ----------------------- | ----------------------------------- |
| 预测模型不准确          | 设计鲁棒的 fallback 机制            |
| vLLM 版本更新导致不兼容 | 抽象接口层，降低耦合                |
| 实验资源不足            | 优先使用云 GPU，考虑与业界合作      |
| 与 ICLR 工作撞车        | 强调异构模型支持 + 理论贡献的差异化 |

______________________________________________________________________

## 10. 相关工作

### 10.1 LLM Serving Systems

- **vLLM** (SOSP 2023): PagedAttention for KV Cache memory efficiency
- **Orca** (OSDI 2022): Iteration-level scheduling for LLM inference
- **FastServe** (2023): Preemptive scheduling with skip-join MLFQ
- **DistServe** (OSDI 2024): Disaggregating prefill and decoding
- **Mooncake** (2024): KVCache-centric disaggregated architecture
- **SGLang** (2024): RadixAttention for KV cache reuse

### 10.2 Memory Management for ML

- **Capuchin** (ASPLOS 2020): Memory-efficient GPU memory management
- **vDNN** (MICRO 2016): Virtualized DNN with memory optimization
- **SwapAdvisor** (ASPLOS 2020): GPU memory management for DL training

### 10.3 Multi-Model Serving

- **S-LoRA** (2024): Scalable serving of many LoRA adapters
- **Punica** (2023): Multi-tenant LoRA serving with shared base model

### 10.4 SLO-Aware Systems

- **Clipper** (NSDI 2017): Low-latency prediction serving
- **INFaaS** (ATC 2021): Automated model-less inference serving

______________________________________________________________________

## 11. 参考文献

1. Kwon, W., et al. "Efficient Memory Management for Large Language Model Serving with
   PagedAttention." SOSP 2023.
1. Zhong, Y., et al. "DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large
   Language Model Serving." OSDI 2024.
1. Qin, R., et al. "Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving." arXiv
   2024\.
1. Sheng, Y., et al. "S-LoRA: Serving Thousands of Concurrent LoRA Adapters." arXiv 2024.
1. Agrawal, A., et al. "SARATHI: Efficient LLM Inference by Piggybacking Decodes with Chunked
   Prefills." arXiv 2023.
1. Zheng, L., et al. "SGLang: Efficient Execution of Structured Language Model Programs." arXiv
   2024\.
1. Wang, Y., et al. "BurstGPT: A Real-world Workload Dataset to Optimize LLM Serving Systems." arXiv
   2024\.
