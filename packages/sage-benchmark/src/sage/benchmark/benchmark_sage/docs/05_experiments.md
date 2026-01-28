# Experiments Prompts – SAGE Systems Paper

本文件帮助你为系统论文的 Experiments 部分设计结构和写作提示词。 **关键更新**：本提示词已与 `sage-benchmark` 中的实际实验脚本（`exp_5_1` 至
`exp_5_5`）和画图工具（`plotting.py`）完全对齐。

______________________________________________________________________

## 5.1 设计实验章节结构 (Structure Design)

**提示词（可直接复制）**

You are the experiments lead for a systems-track paper about **SAGE**.

--- System and evaluation context ---

SAGE is a system for **LLM/AI pipelines** with a unified control plane, declarative dataflow, and
support for heterogeneous hardware. We have implemented a comprehensive benchmark suite
(`sage-benchmark`) with 5 specific experiments.

--- Task ---

Design the **structure** of the Experiments section. It MUST follow this exact 5-subsection
structure to match our experimental results:

### 5.1 End-to-End Pipeline Performance

- **Goal**: Demonstrate SAGE's efficiency in executing complex, multi-stage pipelines (specifically
  RAG: Embedding -> Retrieval -> Generation).
- **Workload**: Simulated RAG pipeline with concurrent users; mixed embedding and LLM calls.
- **Key Figure**: **Latency CDF** (Cumulative Distribution Function) showing the distribution of
  end-to-end pipeline latencies.
- **Key Figure**: **Request Timeline** (Waterfall plot) showing the interleaving of embedding and
  generation tasks.

### 5.2 Control Plane Effectiveness

- **Goal**: Prove that SAGE's unified control plane (co-scheduling LLM and Embeddings) outperforms
  separate services.
- **Workload**: Mixed traffic (e.g., 70% Chat, 30% Embedding) at varying request rates.
- **Key Figure**: **Throughput vs. Latency** curve comparing "Unified Control Plane" vs. "Separate
  Services".
- **Key Figure**: **Latency CDF** comparing tail latencies (p99) of the two approaches.

### 5.3 Isolation & Fairness

- **Goal**: Show SAGE's ability to protect latency-sensitive "Interactive" users from
  high-throughput "Batch" users (Noisy Neighbors).
- **Workload**: Two concurrent user groups: "Interactive" (low rate, high priority) and "Batch"
  (high rate, low priority).
- **Key Figure**: **Latency CDF** for the Interactive user, comparing "With SAGE Isolation" vs.
  "Without Isolation".

### 5.4 Scalability

- **Goal**: Demonstrate linear scaling of throughput as backend resources increase.
- **Workload**: High-concurrency traffic against 1, 2, 4, and 8 vLLM backend instances.
- **Key Figure**: **Scalability Bar Chart** showing Request/Second (RPS) vs. Number of GPUs.

### 5.5 Heterogeneous Hardware Support

- **Goal**: Validate the benefit of offloading Embedding tasks to CPU nodes to save GPU resources
  for LLM inference.
- **Workload**: Mixed workload running on "GPU-only" vs. "Hybrid (GPU for LLM + CPU for Embed)"
  configurations.
- **Key Figure**: **Resource Efficiency** comparison (or Latency CDF showing minimal degradation
  with CPU offloading).

--- Output ---

- A structured outline for the Experiments section.
- For each subsection, write a short paragraph describing the **experimental setup** (workload,
  metrics) and the **expected visual evidence** (the figures mentioned above).

______________________________________________________________________

## 5.2 撰写具体实验分析 (Detailed Analysis Prompts)

以下提示词用于指导大模型撰写具体的实验分析段落。

### 5.1 End-to-End Pipeline Analysis

**Prompt:** "Write the analysis for Section 5.1 (End-to-End Pipeline Performance). The experiment
ran a simulated RAG pipeline (Embed -> Retrieve -> Generate). Refer to **Figure 5.1(a) (Latency
CDF)**, which shows a tight latency distribution with a p99 of [X] ms, indicating stable
performance. Refer to **Figure 5.1(b) (Request Timeline)**, which illustrates how SAGE's scheduler
efficiently interleaves embedding and generation tasks, minimizing gaps and maximizing resource
usage."

### 5.2 Control Plane Analysis

**Prompt:** "Write the analysis for Section 5.2 (Control Plane Effectiveness). Compare SAGE's
unified scheduling against a baseline of separate services. Refer to **Figure 5.2 (Throughput vs.
Latency)**. Highlight that SAGE sustains [Y]% higher throughput before latency saturation. Explain
that by co-scheduling, SAGE utilizes idle GPU cycles (during LLM decoding gaps) for embedding tasks,
as evidenced by the lower tail latency in the **Latency CDF**."

### 5.3 Isolation Analysis

**Prompt:** "Write the analysis for Section 5.3 (Isolation & Fairness). Describe the 'Noisy
Neighbor' scenario with Interactive vs. Batch users. Refer to **Figure 5.3**, showing that without
isolation, the Interactive user's p99 latency spikes to [A] ms. With SAGE's priority-aware
scheduling, the Interactive user's latency curve remains close to the baseline, demonstrating
effective performance isolation."

### 5.4 Scalability Analysis

**Prompt:** "Write the analysis for Section 5.4 (Scalability). Refer to **Figure 5.4 (Scalability
Bar Chart)**. Observe that throughput scales nearly linearly from 1 to 8 GPUs. Calculate the scaling
efficiency (e.g., '7.2x speedup on 8 GPUs'), proving that the SAGE control plane introduces minimal
overhead."

### 5.5 Heterogeneity Analysis

**Prompt:** "Write the analysis for Section 5.5 (Heterogeneous Hardware). Discuss the trade-off of
offloading embeddings to CPU. State that while CPU embedding latency is slightly higher, the overall
system throughput for LLM tokens increases significantly because GPU resources are freed up.
Conclude that SAGE's flexible node selection enables cost-efficient deployments."

- Test with 1, 2, 4, 8 vLLM instances (and optionally multiple embedding servers).
- Measure: throughput, speedup vs. single-engine baseline, control-plane overhead ratio.

2. **Load scaling (requests per second)**
   - Sweep request rate from light load up to and beyond saturation.
   - Measure: throughput curve, latency curve (especially tail), SLO hit rate.
1. **Concurrent clients**
   - Test with 1, 10, 50, 100 concurrent clients.
   - Measure: per-client latency, fairness, starvation or head-of-line blocking.
1. **Model size scaling**
   - Test with different model sizes (e.g., 7B, 13B, 70B) if available.
   - Measure: how control-plane overhead compares to model inference time.

--- Experimental setup checklist ---

Ask the model to force the following information to be specified:

```text
Hardware specification:
- GPU type: [e.g., A100 40GB, RTX 4090]
- Number of GPUs: [e.g., 4]
- CPU cores: [e.g., 64]
- Memory: [e.g., 256 GB]
- Network: [e.g., InfiniBand, 10GbE]

Software versions:
- SAGE version: [e.g., 0.5.0]
- vLLM version: [e.g., 0.4.0]
- CUDA version: [e.g., 12.1]
- Python version: [e.g., 3.11]

Workload specification:
- LLM model: [e.g., Qwen2.5-7B-Instruct]
- Embedding model: [e.g., BGE-M3]
- Input token length: [e.g., 512 tokens]
- Output token length: [e.g., 128 tokens]
- Request arrival: [e.g., Poisson, bursty, constant]
```

--- Expected result formats ---

Table: Throughput vs. Number of Backends

| Backends | Throughput (req/s) | Speedup | Control Plane Overhead |
| -------: | -----------------: | ------: | ---------------------: |
|        1 |         [baseline] |    1.0× |                   [X]% |
|        2 |                [?] |    [?]× |                   [?]% |
|        4 |                [?] |    [?]× |                   [?]% |
|        8 |                [?] |    [?]× |                   [?]% |

Figure: Latency vs. Request Rate

- X-axis: request rate (req/s)
- Y-axis: latency (ms)
- Lines: p50, p95, p99
- Mark saturation point and discuss where SAGE’s control plane becomes the bottleneck (if at all)

--- Output ---

1. A detailed experimental plan with specific configurations.
1. Expected table/figure formats.
1. Key claims the scalability study should support (e.g., near-linear scaling up to N backends,
   negligible control-plane overhead for large models).

______________________________________________________________________

## 5.3 为每类实验撰写结果描述

在你实际拿到实验数据之后，可以用下面的提示词为每类实验写结果段落。

**提示词（可直接复制，每个子节可复用）**

We now have experimental results for the subsection:

> \[INSERT EXPERIMENT SUBSECTION TITLE HERE, e.g., "End-to-End Pipeline Performance" or "Scalability
> Study"\]

Here is the design of this subsection (goal, workloads, metrics, baselines):

[PASTE THE DESIGN OUTLINE FOR THIS SUBSECTION HERE]

Here are the preliminary results (tables, plots, or bullet points):

[PASTE YOUR NUMERIC OR QUALITATIVE RESULTS HERE]

--- Task ---

Write the **Results and Analysis** text for this subsection in English, targeting systems reviewers.

Requirements:

1. Start by restating **what the experiment tries to verify** (e.g., whether the control plane
   improves tail latency under mixed workloads, whether declarative dataflow leads to better
   resource utilization, whether heterogeneous deployment is practical).
1. Describe **key trends in the results**, referencing specific metrics (throughput, latency, SLO
   satisfaction, success rates, cost-performance, etc.).
1. Clearly explain **why SAGE behaves better or differently** than baselines, relating back to
   design choices (layering, control plane, dataflow, CPU-only support, benchmarks, tooling).
1. If results are mixed, be honest and propose plausible explanations or follow-up experiments.
1. Propose **candidate figure/table captions** for the plots or tables we have, and specify which
   should be in the main paper vs. appendix.

--- Output ---

1. A few paragraphs of result description and analysis for this subsection.
1. A list of suggested figure/table captions with a short description each.
1. If applicable, a short note on what additional experiments could strengthen this story.

______________________________________________________________________

## 5.4 Baseline 选择指南（SAGE 特化）

**为什么需要仔细选择 baseline：** 系统论文审稿人会严格审视 baseline 是否公平、是否代表了 state-of-the-art。

| SAGE Feature                    | Recommended Baseline                                      | Why This Baseline                              |
| ------------------------------- | --------------------------------------------------------- | ---------------------------------------------- |
| Layered architecture + dataflow | Ad-hoc Python scripts or flat microservices               | Shows maintainability / complexity differences |
| Unified control plane           | vLLM + separate embedding service (manual load balancing) | Shows the benefit of unified scheduling        |
| Hybrid scheduling               | SAGE with FIFO policy                                     | Ablation showing scheduling policy matters     |
| Multi-engine support            | Single vLLM instance                                      | Shows horizontal scaling works                 |
| CPU-only support                | GPU-only deployment or naive CPU-only baseline            | Shows cost-effectiveness and feasibility       |
| System-level benchmark          | AgentBench / ToolBench / single-engine benchmark          | Shows SAGE’s broader system metrics vs. others |

Baseline 实现要求：

1. 所有 baseline 必须使用相同或明确定义的硬件配置。
1. vLLM baseline 必须使用相同版本和参数。
1. 如果无法使用相同硬件，必须说明并尽量归一化结果（例如用吞吐/成本等指标）。
1. 必须报告 baseline 的最优合理配置（不能故意用明显较差的配置）。

______________________________________________________________________

## 5.5 实验结果的可重复性

**系统论文对可重复性要求很高。** 确保包含以下信息：

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

建议在论文附录或 supplementary material 中包含：

1. 完整的实验配置文件；
1. 用于生成图表的原始数据；
1. 运行实验的脚本（可基于 `sage-dev` 或 `sage.benchmark` 的 CLI）。
