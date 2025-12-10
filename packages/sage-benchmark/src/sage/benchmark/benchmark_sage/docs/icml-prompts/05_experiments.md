# ICML System Track - Experiments Prompts# ICML System Track – Experiments Prompts

本文件帮助你为 ICML 系统方向的 Experiments 部分设计和撰写提示词，强调实现与扩展性、调度策略与 benchmark。本文件帮助你为 ICML 系统方向的 Experiments
部分设计和撰写提示词，强调实现与扩展性、调度策略与 benchmark。

______________________________________________________________________

## 5.1 设计实验章节结构## 5.1 设计实验章节结构

\*\*提示词（可直接复制）\*\***提示词（可直接复制）**

You are the experiments lead for an ICML systems-track paper about **SAGE**.You are the experiments
lead for an ICML systems-track paper about **SAGE**.

--- System and evaluation context ------ System and evaluation context ---

- SAGE is a system for **LLM/AI pipelines** with:- SAGE is a system for **LLM/AI pipelines** with:

  - A multi-layer architecture; - A multi-layer architecture;

  - Declarative dataflow; - Declarative dataflow;

  - A unified control plane for LLM and embedding workloads; - A unified control plane for LLM and
    embedding workloads;

  - Support for CPU-only and GPU nodes; - Support for CPU-only and GPU nodes;

  - A benchmark suite for **agent capabilities** and **control-plane policies**. - A benchmark suite
    for **agent capabilities** and **control-plane policies**.

- We want experiments that convince systems reviewers that SAGE brings **real systems benefits**,
  not just convenience.- We want experiments that convince systems reviewers that SAGE brings **real
  systems benefits**, not just convenience.

--- Required Experiment Categories (MUST include all) ------ Task ---

Design the **structure** of the Experiments section by proposing 3–5 main subsections. For each
subsection, specify:

\*\*Category A: Control Plane Effectiveness (CRITICAL - main contribution)\*\*1. **Goal** of the
experiments in this subsection (e.g., end-to-end performance, scheduling effectiveness, scalability,
robustness, ablation of design choices).

- Goal: Demonstrate that unified LLM+embedding scheduling improves performance2. **Workloads** to
  consider (e.g., multi-step LLM pipelines, mixed chat+embedding traffic, CPU-only vs
  GPU-accelerated deployments, realistic agent tasks).

- Compare: SAGE vs. vLLM-only vs. vLLM+separate-embedding-service3. **Metrics** to report (e.g.,
  throughput, mean latency, 95th/99th percentile latency, SLO satisfaction rate, CPU/GPU
  utilization, agent task success rate, planning/tool-selection accuracy).

- Metrics: p50/p95/p99 latency, throughput, SLO satisfaction rate4. **Baselines** and configurations
  to compare against, such as:

- Workload: Mixed chat + embedding traffic (e.g., 70% chat, 30% embedding) - Naive scripts or ad-hoc
  orchestration without declarative dataflow;

  - LLM-only serving systems without a unified control plane for embeddings;

**Category B: Scheduling Policy Comparison** - Different scheduling policies within SAGE (FIFO vs.
HybridSchedulingPolicy vs. priority/SLO-aware variants);

- Goal: Show that HybridSchedulingPolicy outperforms simpler policies - Ablations where we disable
  certain layers or features (e.g., no control plane, no batching, no CPU-only support).

- Compare: FIFO vs. priority vs. SLO-aware vs. hybrid5. Whether this subsection belongs in the
  **main paper** or could be partially moved to **appendix/supplementary** if space is tight, and
  what the minimum necessary experiments are for the main text.

- Metrics: Same as above, plus queue depth, wait time distribution

- Workload: Bursty traffic, steady traffic, adversarial patterns--- Output ---

- A structured experiments outline listing each subsection with bullets for goal, workloads,
  metrics, baselines, and placement (main vs. appendix).

**Category C: Scalability (CRITICAL for systems paper)**

- Goal: Demonstrate system scales with more backends and higher load---

- Variables:

  - Number of backend engines (1, 2, 4, 8)## 5.2 为每类实验撰写结果描述

  - Request rate (10, 100, 500, 1000 req/s)

  - Number of concurrent clients在你实际拿到实验数据之后，可以用下面的提示词为每类实验写结果段落。

- Metrics: Throughput saturation point, latency at saturation, resource utilization

**提示词（可直接复制，每个子节可复用）**

**Category D: Heterogeneous Hardware**

- Goal: Show CPU-only node support and CPU/GPU mixed deploymentsWe now have experimental results for
  the subsection:

- Compare: GPU-only vs. CPU-only vs. mixed for embedding workloads

- Metrics: Cost-performance ratio, latency, throughput> \[INSERT EXPERIMENT SUBSECTION TITLE HERE,
  e.g., "End-to-End Pipeline Performance"\]

\*\*Category E: Agent Capability Evaluation (if claiming agent contribution)\*\*Here is the design
of this subsection (goal, workloads, metrics, baselines):

- Goal: Evaluate tool selection, planning, timing decisions

- Compare: SAGE agent strategies vs. baselines[PASTE THE DESIGN OUTLINE FOR THIS SUBSECTION HERE]

- Metrics: Task success rate, tool selection accuracy, planning quality

- Note: Can be moved to appendix if page limit is tightHere are the preliminary results (tables,
  plots, or bullet points):

--- Task ---[PASTE YOUR NUMERIC OR QUALITATIVE RESULTS HERE]

Design the **structure** of the Experiments section by proposing 4-5 main subsections based on the
categories above. For each subsection, specify:

1. **Goal** of the experiments in this subsection--- Task ---

1. **Workloads** to use (be specific about traffic patterns, request rates, model sizes)Write the
   **Results and Analysis** text for this subsection in English, targeting ICML systems reviewers.

1. **Metrics** to report (with specific targets, e.g., "p99 < 500ms")

1. **Baselines** and configurations to compare againstRequirements:

1. **Placement**: main paper vs. appendix1. Start by restating **what the experiment tries to
   verify** (e.g., whether the control plane improves tail latency under mixed workloads, whether
   declarative dataflow leads to better resource utilization, etc.).

1. Describe **what the key trends in the results are**, referencing specific metrics (throughput,
   latency, SLO satisfaction, success rates, etc.).

--- Output ---3. Clearly explain **why SAGE behaves better or differently** than baselines, relating
back to design choices (layering, control plane, dataflow, CPU-only support, etc.).

- A structured experiments outline listing each subsection with bullets for goal, workloads,
  metrics, baselines, and placement.4. If results are mixed, be honest and propose plausible
  explanations or follow-up experiments.

5. Propose **candidate figure/table captions** for the plots or tables we have, and specify which
   should be in the main paper vs. appendix.

______________________________________________________________________

--- Output ---

## 5.2 Scalability 实验设计（CRITICAL - 系统论文必备）1. A few paragraphs of result description and analysis for this subsection.

2. A list of suggested figure/table captions with a short description each.

\*\*提示词（可直接复制）\*\*3. If applicable, a short note on what additional experiments could strengthen
this story.

Design a **scalability study** for SAGE that will convince ICML systems reviewers.

--- Scalability Dimensions to Test ---

1. **Horizontal scaling (number of backend engines)**

   - Test with 1, 2, 4, 8 vLLM instances
   - Measure: linear speedup? sublinear? overhead?
   - Key question: How does the control plane overhead scale?

1. **Load scaling (requests per second)**

   - Test from 10 req/s to saturation point
   - Measure: throughput curve, latency curve (especially tail)
   - Key question: What is the throughput ceiling? Why?

1. **Concurrent clients**

   - Test with 1, 10, 50, 100 concurrent clients
   - Measure: per-client latency, fairness, starvation
   - Key question: Does SAGE maintain fairness under high concurrency?

1. **Model size scaling**

   - Test with different model sizes (7B, 13B, 70B if available)
   - Measure: how does control plane overhead relate to model inference time?
   - Key question: Is control plane overhead negligible for large models?

--- Experimental Setup Requirements ---

```
Hardware specification (fill in actual values):
- GPU type: [e.g., A100 40GB, RTX 4090]
- Number of GPUs: [e.g., 4]
- CPU cores: [e.g., 64]
- Memory: [e.g., 256GB]
- Network: [e.g., InfiniBand, 10GbE]

Software versions:
- SAGE version: [e.g., 0.5.0]
- vLLM version: [e.g., 0.4.0]
- CUDA version: [e.g., 12.1]
- Python version: [e.g., 3.11]

Workload specification:
- Model: [e.g., Qwen2.5-7B-Instruct]
- Embedding model: [e.g., BGE-M3]
- Input token length: [e.g., 512 tokens, uniform/sampled]
- Output token length: [e.g., 128 tokens, uniform/sampled]
- Request arrival: [e.g., Poisson, bursty, constant]
```

--- Expected Results Format ---

Table: Throughput vs. Number of Backends

| Backends | Throughput (req/s) | Speedup | Control Plane Overhead |
| -------- | ------------------ | ------- | ---------------------- |
| 1        | [baseline]         | 1.0x    | [X]%                   |
| 2        | [?]                | [?]x    | [?]%                   |
| 4        | [?]                | [?]x    | [?]%                   |
| 8        | [?]                | [?]x    | [?]%                   |

Figure: Latency vs. Request Rate

- X-axis: Request rate (req/s)
- Y-axis: Latency (ms)
- Lines: p50, p95, p99
- Mark saturation point

--- Output ---

1. Detailed experimental plan with specific configurations
1. Expected table/figure formats
1. Key claims the scalability study should support

______________________________________________________________________

## 5.3 为每类实验撰写结果描述

在你实际拿到实验数据之后，可以用下面的提示词为每类实验写结果段落。

**提示词（可直接复制，每个子节可复用）**

We now have experimental results for the subsection:

> [INSERT EXPERIMENT SUBSECTION TITLE HERE, e.g., "Scalability Study"]

Here is the design of this subsection (goal, workloads, metrics, baselines):

[PASTE THE DESIGN OUTLINE FOR THIS SUBSECTION HERE]

Here are the preliminary results (tables, plots, or bullet points):

[PASTE YOUR NUMERIC OR QUALITATIVE RESULTS HERE]

--- Task --- Write the **Results and Analysis** text for this subsection in English, targeting ICML
systems reviewers.

Requirements:

1. Start by restating **what the experiment tries to verify**
1. Describe **key trends in the results**, referencing specific metrics
1. Include **quantitative claims**: "SAGE achieves [X]x speedup" or "reduces p99 latency by [Y]%"
1. Explain **why** SAGE behaves differently (connect to design choices)
1. Acknowledge **limitations** if results are mixed
1. Propose **figure/table captions**

--- Output ---

1. A few paragraphs of result description and analysis
1. Suggested figure/table captions
1. Notes on additional experiments that could strengthen claims

______________________________________________________________________

## 5.4 Baseline 选择指南

**为什么需要仔细选择 baseline：** 系统论文审稿人会严格审视你的 baseline 是否公平、是否代表了 state-of-the-art。

| SAGE Feature          | Recommended Baseline                                      | Why This Baseline                          |
| --------------------- | --------------------------------------------------------- | ------------------------------------------ |
| Unified control plane | vLLM + separate embedding service (manual load balancing) | Shows the benefit of unified scheduling    |
| Hybrid scheduling     | SAGE with FIFO policy                                     | Ablation showing scheduling policy matters |
| Multi-engine support  | Single vLLM instance                                      | Shows horizontal scaling works             |
| CPU-only support      | GPU-only deployment                                       | Shows cost-effectiveness                   |
| Declarative dataflow  | Ad-hoc Python scripts                                     | Shows programmability benefit (optional)   |

**Baseline 实现要求：**

1. 所有 baseline 必须使用相同硬件配置
1. vLLM baseline 必须使用相同版本和参数
1. 如果无法使用相同硬件，必须说明并归一化结果
1. 必须报告 baseline 的最优配置（不能故意用差的配置）

______________________________________________________________________

## 5.5 实验结果的可重复性

**ICML 系统论文对可重复性要求很高。** 确保包含以下信息：

```markdown
### Reproducibility Checklist

- [ ] Hardware specification (GPU model, memory, CPU cores, network)
- [ ] Software versions (SAGE, vLLM, CUDA, Python, key dependencies)
- [ ] Model details (model name, size, quantization if any)
- [ ] Workload specification (input/output length distribution, arrival pattern)
- [ ] Warm-up procedure (how many requests before measurement?)
- [ ] Measurement duration (how long did you run each experiment?)
- [ ] Number of repetitions (how many times did you repeat? error bars?)
- [ ] Code availability (will you release experiment scripts?)
```

**建议在论文附录或 supplementary material 中包含：**

1. 完整的实验配置文件
1. 用于生成图表的原始数据
1. 运行实验的脚本
