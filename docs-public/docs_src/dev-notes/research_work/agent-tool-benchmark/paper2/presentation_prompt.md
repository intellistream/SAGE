````markdown
# Paper 2 (SIAS) — PPT Prompt

You are acting as an elite technical presentation designer. Produce a 18–22 slide PPT (16:9) summarizing Paper 2 “SIAS: Self-Improving Agentic Systems with Reflective Memory and Streaming Adaptation.” Follow these rules:

## Source Material
1. Core narrative: `docs/dev-notes/research_work/agent-tool-benchmark/paper2/icml_prompt.md`
2. Work breakdown / ownership context: `docs/dev-notes/research_work/agent-tool-benchmark/paper2/task_division_prompt.md`
3. Architecture references: `packages/sage-libs/src/sage/libs/sias/`
4. Benchmark + experiment tooling: `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/`

Assume all cited files are available; extract concrete facts, metrics, and component names directly. Do **not** invent results—if a figure/table is TBD, clearly mark “(placeholder, insert once experiment completes)”.

## Slide Blueprint
1. **Title** – Paper title, author list, affiliations, conference target (ICML 2026).
2. **Motivation** – Pain points of static tool-using agents (lack memory, adaptability, persistent learning). Include references to ReAct, ToolLLM, etc.
3. **Benchmark Evidence** – Key findings from Paper 1 (timing/planning/tool selection saturation) motivating SIAS.
4. **Contributions Overview** – Bullet the four pillars: Reflective Memory Planner, Adaptive Execution, Collaborative Specialists, Streaming Trainer.
5. **System Diagram** – High-level pipeline: memory, planner, verifier, router, streaming trainer, tool layer.
6. **StreamingImportanceScorer (SSIS)** – Formula, intuition, expected gains over random/uncertainty.
7. **Reflective Memory Store** – Data schema, query APIs, snapshot/restore.
8. **Adaptive Executor** – Pre-/post-verification flow with localized replanning decision tree.
9. **Specialist Agents & Router** – Roles (Researcher/Coder/Analyst/Coordinator), blackboard comms.
10. **Streaming Trainer Stack** – Replay buffer, SSIS coreset, EWC regularizer, PPO/DPO hooks.
11. **Datasets** – Streaming Tool-Arena + Continual Tool Drop-In (phases, stats, scale).
12. **Experimental Setup** – Hardware, models (Qwen2.5-7B/14B, BGE embeddings), metrics.
13. **Key Results** – Sample efficiency (−35% data), coreset ablations (+3.4% vs random), continual performance (−3.1% forgetting), RL boost (+4.6%).
14. **Figures** – Mock layout instructions for Fig1–Fig5 and Tables1–4; specify data needed.
15. **Ablations & Failure Modes** – Memory size vs latency, mis-ranked episodes, collaboration overhead.
16. **Ethics & Privacy** – Logging considerations, compliance hooks.
17. **Roadmap / Remaining Work** – Summarize from `task_division_prompt.md` highlighting SSIS, Memory, Trainer priority.
18. **Call to Action** – What help is needed (implementation, experiments, doc polish) and timeline.
19. **Backup Appendix (optional)** – Detailed algorithms, convergence sketches, dataset generation notes.

## Design & Formatting Guidelines
- Theme: modern tech, dark text on light background, accent colors #4C7DFF and #FFB347.
- Include icons/graphics for each subsystem (memory chip, gears, network). Use vector-friendly placeholders.
- Every technical slide needs a citation or file path reference.
- Reserve space for plots/tables: use labeled placeholders (e.g., “Fig 3 placeholder – SSIS vs random”).
- Provide presenter notes (2–3 sentences) per slide.

## Output Specification
Return a structured JSON with fields:
```json
{
  "slides": [
    {
      "title": "...",
      "bullets": ["..."],
      "visual": "Description of diagram/figure/table",
      "notes": "Presenter notes"
    }
  ],
  "styleGuide": "...",
  "todoPlaceholders": ["List any figures/data still pending"]
}
````

The JSON should be ready for an automated PPT generator to consume. Keep bullet text concise (max 10
words). Use full sentences only in presenter notes. Identify which future data (e.g., upcoming
experiments) must be inserted later.

```
```
