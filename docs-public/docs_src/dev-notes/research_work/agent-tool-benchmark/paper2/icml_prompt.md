# Paper 2 (SAGE-Agent) – ICML Writing Prompt

Use the following structured brief to draft a full ICML-style paper (10 pages + references) **and**
provide complete LaTeX source plus `.bib` entries. The draft must follow the latest ICML formatting
guidelines (two-column layout, abstract ≤ 200 words, intro with numbered contributions).

## 0. Meta Instructions

- **Conference target**: ICML 2026 main track.
- **Tone**: Technical, precise, mix of theoretical insight + empirical rigor.
- **Audience**: Researchers in LLM agents, continual learning, streaming optimization.
- **Deliverables**:
  1. `main.tex` compatible with `icml2025.sty` (use `\documentclass{article}` +
     `\usepackage{icml2025}` pattern).
  1. `references.bib` with ≥20 entries (include 2023-2025 works on streaming learning, agentic LLMs,
     reflexion, multi-agent coordination, RLHF/RLAIF, continual learning, coreset selection,
     tool-use benchmarks).
  1. README snippet describing how to compile.

## 1. Title & Authors

- **Working title**:
  `SIAS: Self-Improving Agentic Systems with Reflective Memory and Streaming Adaptation`
- **Authors**: Placeholder names (e.g., Alice Zhang, Bo Chen, etc.) across institutions in US/CN/EU.

## 2. Motivation

- Existing tool-augmented LLM agents (e.g., ReAct, ToolLLM, Gorilla, AutoGPT) follow a **static plan
  \+ best-of-one reasoning** paradigm.
- They fail in long-horizon tasks because they **lack persistence** (no memory), **lack
  adaptability** (no re-planning when tools fail), and **relearn from scratch** when new tools/data
  arrive.
- Benchmark evidence from Paper 1 (SAGE-Bench) shows timing/planning/tool-selection accuracy
  plateaus even when models scale.
- Need an agent that **learns continuously from experience while remaining sample-efficient**.

## 3. Method Overview (Core Sections)

Describe four tightly coupled innovations:

1. **Reflective Memory Planner**

   - Maintains a streaming execution memory of `(query, plan, execution trace, reflection)` tuples.
   - Uses SSIS (Streaming Sample Importance Scorer) to rank past episodes.
   - Performs self-critique before dispatching plans; integrates prior failures to avoid repetition.

1. **Adaptive Execution & Dynamic Re-Planning**

   - Pre-condition verifier + observation validator.
   - If a tool call deviates from expectations, triggers localized re-planning instead of restarting
     entire workflow.
   - Supports multi-resolution planning (high-level vs low-level steps), connecting to
     `runtime/orchestrator.py` implementation.

1. **Collaborative Specialist Agents**

   - Router assigns sub-tasks to specialized agents (Researcher, Coder, Analyst, Coordinator).
   - Agents share summaries through a streaming blackboard; only Coordinator can commit final
     answers.

1. **Streaming Training Stack (Paper 2 focus)**

   - Unified trainer covering batch, streaming, and continual regimes (ref: `streaming_trainer.py`,
     `batch_trainer.py`).
   - Incorporates coreset selectors: random, uncertainty, diversity, SSIS.
   - Includes continual-learning defenses (EWC-style regularizer + replay buffer) and RL fine-tuning
     (PPO/DPO) on execution feedback.

Provide algorithm boxes (pseudo-code) for each component.

## 4. Experimental Setup

Use these subsections and concrete details:

- **Benchmarks**: SAGE-Bench (timing/planning/tool-selection), Streaming Tool-Arena (new dataset
  with 1200 tools), Continual Tool Drop-In (phase I=1000 tools, phase II= +200 unseen tools).
- **Baselines**: ReAct, Reflexion, AutoGPT, ToolLLM, Gorilla, LATS, Voyager, and our ablations (w/o
  memory, w/o replan, w/o coreset, batch-only).
- **Metrics**: plan accuracy, tool success rate, adaptation lag (episodes to recover), catastrophic
  forgetting (Δ accuracy old tools), sample efficiency (% data to reach baseline), compute hours.
- **Implementation**: UnifiedInferenceClient + vLLM (Qwen2.5-7B/14B), embeddings (BAAI/bge-m3),
  training on 2×A100 80GB.
- **Hyperparameters**: streaming buffer size 1000, coreset size 256, RL fine-tuning 3 epochs with
  reward shaping from execution success.

## 5. Key Results to Highlight

- Streaming vs Batch: SIAS reaches target accuracy using 35% fewer samples and 28% less GPU time.
- Coreset Ablation: SSIS yields +3.4% accuracy vs random, +2.1% vs uncertainty.
- Continual Learning: Forgetting reduced from −12.7% to −3.1%; adaptation to new tools in 15
  episodes vs 48 for baselines.
- RL Fine-tuning: +4.6% end-to-end task success (especially for multi-hop reasoning tasks).
- Qualitative case study: planner catches hallucinated weather API result, re-plans via search +
  summarization.

## 6. Figures & Tables to Produce

- **Fig 1**: Architecture diagram of SIAS pipeline (memory, planner, verifier, specialist agents,
  streaming trainer).
- **Fig 2**: Sample efficiency curves (streaming vs batch).
- **Fig 3**: Coreset strategy comparison.
- **Fig 4**: Continual-learning forgetting curves.
- **Fig 5**: Ablation radar chart (memory, replan, collaboration, RL).
- **Table 1**: Benchmark comparison on SAGE-Bench (timing/planning/selection accuracy).
- **Table 2**: Streaming vs batch resource usage.
- **Table 3**: Continual-learning results (old/new tools).
- **Table 4**: RL fine-tuning improvements per task family.

## 7. Discussion Prompts

- Analyze trade-offs between memory size vs latency.
- Failure modes: when SSIS mis-ranks episodes, when collaboration overhead dominates.
- Ethical considerations: logging user/tool traces, privacy in memory.
- Future work: integrating symbolic verification, extending to multi-modal agents.

## 8. Appendix Must-Haves

- Detailed algorithm derivations for SSIS scoring.
- Proof sketch for convergence of streaming trainer under bounded drift.
- Extended implementation details (configs, hardware utilization, cost analysis).
- Additional ablation on memory warm-start length and RL reward shaping.

> **Output format reminder**: Provide `main.tex`, `references.bib`, and `README.md` (compile
> instructions). Make sure citations in LaTeX match BibTeX keys.
