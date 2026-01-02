# Paper 1 (SAGE-Bench) – ICML Writing Prompt

Use the following structured brief to draft a full ICML-style benchmark paper (10 pages +
references) **and** provide complete LaTeX source plus `.bib` entries. The draft must follow the
latest ICML formatting guidelines (two-column layout, abstract ≤ 200 words, intro with numbered
contributions).

## 0. Meta Instructions

- **Conference target**: ICML 2026 main track.
- **Tone**: Scientific, data-rich, emphasize careful benchmarking and reproducibility.
- **Audience**: Researchers working on LLM agents, tool-use evaluation, program-of-thought planning,
  and responsible deployment.
- **Deliverables**:
  1. `main.tex` compatible with `icml2025.sty` (standard `\documentclass{article}` +
     `\usepackage{icml2025}` scaffold).
  1. `references.bib` with ≥25 entries (cover 2022-2025 benchmarks on tool-use,
     ReAct/ToolLLM/Gorilla, ACE/ToolBench/API-Bank, evaluation methodology, LLM agent analysis, and
     robustness).
  1. README snippet (compilation instructions + dependency list).
  1. Figures saved as `fig/*.pdf` references inside LaTeX; tables produced with `\begin{table}`
     blocks referencing `tables/*.tex` if needed.

## 1. Title & Authors

- **Working title**:
  `SAGE-Bench: Diagnosing Timing, Planning, and Tool Selection Failures in LLM Agents`
- **Authors**: Placeholder team (e.g., Alice Zhang, David Romero, Jiaqi Wang, Priya Natarajan,
  Markus Vogel) spanning academia + industry + open-source lab.

## 2. Motivation & Problem Statement

Highlight why existing benchmarks (ToolBench, API-Bank, ACE, BFCL) fail to jointly test *timing*,
*planning*, and *tool selection* under the same controlled protocol. Stress the following pain
points:

- ReAct, ToolLLM, Gorilla, AutoGPT, Voyager, etc. report single-task metrics, avoiding cross-cutting
  failure modes.
- Current evaluations ignore *timing* ("should I call a tool?"), leading to over-triggering or
  missed opportunities.
- Task planning metrics are rarely standardized → difficult to compare hierarchical vs ReAct vs CoT
  planners.
- Tool selection datasets lack noise injection, semantic variation, and reliability perturbations.
- SAGE-Bench bridges these gaps with: (i) unified dataset of ~1k tasks with human-verified
  references, (ii) layered RQ design (RQ1 timing, RQ2 planning, RQ3 selection), (iii) scripted
  analysis suites (scaling, robustness, ablations, cross-dataset).

## 3. Benchmark Overview (Core Sections)

Structure the method section with four subsections (include diagrams / pseudo-code where helpful):

1. **Benchmark Construction**

   - Describe data sourcing: curated tasks spanning enterprise productivity, developer tooling,
     reasoning, retrieval.
   - Provide split counts (train/dev/test) and labeling pipeline (human annotation + validator
     scripts).
   - Detail challenge definitions: timing messages, planning traces, selection candidate pools (≥20
     tools per query), noise tool synthesis, reliability perturbations.

1. **Evaluation Harness**

   - Introduce the adapter registry (selectors, planners, timing deciders) located in
     `packages/sage-benchmark/.../adapter_registry.py`.
   - Emphasize controlled variables: same base models, embeddings, temperature, tool catalogs,
     latency budget.
   - Explain reproducible CLI: `sage-bench paper1 run --section {5.2|5.3|5.4|5.5}` and
     per-experiment subcommands.

1. **Baselines & Protocols**

   - Timing: rule_based, embedding, llm_based, hybrid.
   - Planning: simple, hierarchical (HuggingGPT), llm_based CoT, ReAct, Tree-of-Thoughts.
   - Tool selection: keyword/BM25, dense embedding, hybrid fusion, Gorilla, DFSDT/ToolLLM.
   - Training (Section 5.5): Standard SFT, LoRA/QLoRA/DoRA, FireAct trajectory tuning, AgentTuning
     multi-task, ToolLLM fine-tuning (Paper 2’s SIAS methods are **not** included).
   - Mention evaluation on both default and "skip LLM" modes.

1. **Analysis Suite**

   - Error breakdown taxonomies (timing FP/FN, planning step missing/order, selection confusion
     types).
   - Scaling harness (tool count list = [10,25,50,100,200,500,1000], LLM sizes from Qwen2.5-0.5B →
     14B).
   - Robustness stressors (semantic variation paraphrases, instruction quality levels, tool failure
     & latency spikes).
   - Ablations (prompt variants, hybrid weighting, timing pipeline order).
   - Cross-dataset evaluation on ACE-Bench, ToolBench, API-Bank, BFCL (train on SAGE-Bench,
     zero-shot test elsewhere).

## 4. Experimental Setup (Section 5.1 Template)

Require explicit subsections:

- **Datasets & Challenges**: Provide a table with counts per challenge + cross-dataset stats;
  mention candidate tool pool sizes and reliability annotations.
- **Baselines**: Summaries + citations for each method (ReAct, ToolLLM, Gorilla, Voyager, Reflexion,
  AutoGPT for reference, plus SFT/LoRA variants for training comparison).
- **Metrics**: list per challenge (Accuracy, Precision/Recall/F1, Plan Success Rate, Step Accuracy,
  Tool Coverage, Top-K Accuracy@5, MRR, Latency); for analysis mention adaptation lag, forgetting,
  robustness deltas.
- **Implementation Details**: unify on Qwen2.5-7B/14B via vLLM, embeddings = BAAI/bge-m3, hardware =
  4×A100 80GB (benchmarks) + reproducible seeds, CLI command schedule.

## 5. Main Results (Section 5.2 RQ1–RQ3)

Provide templates for describing each RQ:

- **RQ1 Timing**: Table summarizing accuracy/precision/recall/F1/latency; highlight hybrid
  surpassing 95% accuracy, analyze FP vs FN trade-offs.
- **RQ2 Planning**: Table + figure comparing success rate, step accuracy; observe ReAct vs ToT vs
  hierarchical differences, report average plan length.
- **RQ3 Tool Selection**: Top-K accuracy curves, MRR table, latency plot; show hybrid vs Gorilla vs
  DFSDT performance under noise. Include textual guidance for referencing figure files
  `fig1_timing.pdf`, `fig2_planning.pdf`, `fig3_selection.pdf` and tables `table_timing.tex`, etc.

## 6. Analysis & Cross-Dataset Sections

Outline what to emphasize in Sections 5.3–5.5:

- **Error Analysis**: Provide narrative on cascading failures and recommended mitigations.
- **Scaling Analysis**: Discuss saturation regimes, emergent gains when moving from 1.5B → 7B
  models, diminishing returns beyond 200 tools.
- **Robustness**: Report semantic variation sensitivity (\<5% drop target) and instruction quality
  gaps; note reliability tolerance thresholds.
- **Ablations**: Quantify prompt impacts (+2.3% with CoT) and hybrid weight sweeps.
- **Cross-Dataset Generalization (5.4)**: Table comparing SAGE-Bench-trained models on ACE,
  ToolBench, API-Bank, BFCL; emphasize zero-shot gap and how timing/planning improvements transfer
  to selection-only benchmarks.
- **Training Comparison (5.5)**: Provide figure/table showing baseline SFT vs LoRA/QLoRA/DoRA vs
  FireAct vs AgentTuning vs ToolLLM; highlight fairness (same data size) and note that SIAS methods
  are reserved for Paper 2.

## 7. Key Findings to Highlight

Ensure the narrative surfaces these quantitative bullets:

- Hybrid timing reaches 95.8% accuracy with 30% fewer FP than LLM-only.
- Planning: ReAct improves success by +6.4% over hierarchical on long-horizon tasks;
  Tree-of-Thoughts yields highest step accuracy but +18% latency.
- Tool selection: Hybrid fusion beats Gorilla by +3.1% Top-5 under 500-tool setting; DFSDT best
  under small tool sets but scales poorly.
- Scaling: Accuracy plateaus beyond 7B models; tool count >200 drastically hurts lexical methods.
- Robustness: Semantic paraphrases cost ≤2% for embedding methods but ≥7% for keyword baseline.
- Cross-dataset: Training on SAGE-Bench transfers, improving ACE-Bench top-5 by +4.5% vs prior SOTA.
- Training comparison: LoRA/QLoRA retain 97% of full SFT accuracy with 38% compute savings; FireAct
  helps planning but hurts timing; AgentTuning boosts overall benchmark score by +2.8%.

## 8. Figures & Tables Checklist

Mandate at least these assets:

- **Fig 1** Timing comparison (bar + latency inset).
- **Fig 2** Planning success & plan length.
- **Fig 3** Tool selection Top-5 accuracy vs tool count.
- **Fig 4** Error cascade Sankey / stacked bars.
- **Fig 5** Scaling curves (tool count & LLM size).
- **Fig 6** Robustness heatmap (semantic × reliability).
- **Fig 7** Ablation radar chart.
- **Fig 8** Cross-dataset transfer plot.
- **Table 1** Benchmark summary + statistics.
- **Table 2** RQ1 metrics.
- **Table 3** RQ2 metrics.
- **Table 4** RQ3 metrics.
- **Table 5** Robustness / scaling results.
- **Table 6** Training method comparison (Section 5.5).

## 9. Discussion Prompts

Provide bullet prompts for the discussion section:

- Benchmark takeaways: where agents still fail despite large models.
- Trade-offs between timing conservatism vs latency budgets.
- Limitations: curated dataset bias, reliance on Qwen family, remaining gap to closed-source LLMs.
- Ethical considerations: evaluating real tools safely, logging policies, aligning agent autonomy
  with compliance.
- Future work: integrate SIAS (Paper 2) improvements, expand to multi-modal instructions, introduce
  human-in-the-loop verification.

## 10. Appendix Requirements

- Full dataset curation pipeline, annotation UI screenshots.
- Additional per-dataset breakdown tables (ACE, ToolBench, API-Bank, BFCL).
- Extended error taxonomies + qualitative failure cases.
- Reproducibility checklist (seeds, versions, CLI commands, hardware cost analysis).
- License + release plan for SAGE-Bench artifacts.

> **Output format reminder**: Provide `main.tex`, `references.bib`, `README.md`, and figure/table
> placeholders. All citations in LaTeX must match BibTeX keys; ensure
> `\icmltitlerunning{SAGE-Bench}` is set.
