# Evaluation

This directory contains standalone evaluation and benchmarking entrypoints for the main SAGE repository.

- `run_langchain_sage_rag_experiment.py`: thin CLI wrapper for the shared-workload LangChain + SAGE RAG comparison harness.
- `generate_langchain_rag_paper_report.py`: builds paper-ready tables and figures from one or more batch result directories.
- `langchain_rag/`: modular implementation split into workload entry, retrieval corpus construction, SAGE stages, metrics, output management, and runner orchestration.
- `results/`: batch-isolated experiment outputs. Each invocation creates a new batch directory so different runs never overwrite each other.

Each batch manifest records the fairness policy used for the comparison run. The comparison directory also includes `fairness_audit.json`, which captures workload-level variant execution order, aggregate method, source timing semantics, and generation backend consistency requirements.
