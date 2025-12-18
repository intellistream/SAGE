# PreRetrieval 实验批量运行脚本

## 快速运行核心对比实验 (6个配置)

```bash
# 向量数据库结构 (TiM)
python -m sage.benchmark.benchmark_memory.experiment.memory_test_pipeline \
    --config_path config/query_formulation_strategy/pre_retrieval_tim_baseline.yaml \
    --output_dir results/pre_retrieval_v1_tim_baseline

python -m sage.benchmark.benchmark_memory.experiment.memory_test_pipeline \
    --config_path config/query_formulation_strategy/pre_retrieval_tim_expand_keywords.yaml \
    --output_dir results/pre_retrieval_v3_tim_expand_keywords

# 分层结构 (MemoryOS)  
python -m sage.benchmark.benchmark_memory.experiment.memory_test_pipeline \
    --config_path config/query_formulation_strategy/pre_retrieval_memoryos_baseline.yaml \
    --output_dir results/pre_retrieval_h1_memoryos_baseline

python -m sage.benchmark.benchmark_memory.experiment.memory_test_pipeline \
    --config_path config/query_formulation_strategy/pre_retrieval_memoryos_hybrid_hints.yaml \
    --output_dir results/pre_retrieval_h3_memoryos_hybrid_hints

# 图结构 (Mem0ᵍ)
python -m sage.benchmark.benchmark_memory.experiment.memory_test_pipeline \
    --config_path config/query_formulation_strategy/pre_retrieval_mem0g_baseline.yaml \
    --output_dir results/pre_retrieval_g1_mem0g_baseline

python -m sage.benchmark.benchmark_memory.experiment.memory_test_pipeline \
    --config_path config/query_formulation_strategy/pre_retrieval_mem0g_expand_keywords.yaml \
    --output_dir results/pre_retrieval_g2_mem0g_expand_keywords
```

## 结果分析脚本

```bash
# 汇总实验结果
python -m sage.benchmark.benchmark_memory.analysis.compare_results \
    --result_dirs results/pre_retrieval_* \
    --output_file analysis/pre_retrieval_comparison.csv \
    --metrics accuracy,retrieval_recall,avg_response_time
```

## 配置文件说明

| 配置文件                                   | 记忆体结构      | PreRetrieval策略 | 实验编号 |
| ------------------------------------------ | --------------- | ---------------- | -------- |
| `pre_retrieval_tim_baseline.yaml`          | TiM (向量哈希)  | none             | V1       |
| `pre_retrieval_tim_expand_keywords.yaml`   | TiM (向量哈希)  | expand_keywords  | V3       |
| `pre_retrieval_memoryos_baseline.yaml`     | MemoryOS (分层) | none             | H1       |
| `pre_retrieval_memoryos_hybrid_hints.yaml` | MemoryOS (分层) | hybrid_hints     | H3       |
| `pre_retrieval_mem0g_baseline.yaml`        | Mem0ᵍ (图)      | none             | G1       |
| `pre_retrieval_mem0g_expand_keywords.yaml` | Mem0ᵍ (图)      | expand_keywords  | G2       |
