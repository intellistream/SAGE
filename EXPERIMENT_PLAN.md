# SAGE 分布式调度系统实验计划

## 概述

本实验计划旨在全面评估 SAGE 分布式 LLM 推理编排系统的性能特征，重点关注以下四个方面：
1. **横向扩展性** - 系统随集群规模增长的性能表现
2. **调度效率** - 不同调度策略在多种负载下的表现
3. **延迟-吞吐量权衡** - 系统最优工作点和性能边界
4. **多管道隔离** - 并发执行多个 pipeline 时的资源隔离能力

## 硬件配置

- **计算节点**: 最多 16 个节点，每个节点配置 8 CPU 核心 + 32GB 内存
- **GPU 服务器**: NVIDIA A100 (80GB)，通过 vLLM 提供 LLM 推理服务
- **网络**: 所有节点通过 SAGE Gateway API 访问共享的 GPU 推理端点

## 实验设计

### 实验1: 横向扩展实验（Horizontal Scalability）

**研究问题**: SAGE 的吞吐量、延迟、负载均衡如何随集群规模增长而变化？

**实验配置**:
- **任务数**: 2000（固定）
- **Pipeline 类型**: RAG（检索增强生成，包含 4 个阶段：query embedding → vector retrieval → context construction → response generation）
- **节点数**: 1, 4, 8, 16
- **调度器**: LoadAware-SPREAD（默认）

**测量指标**:
- 吞吐量（tasks/s）
- 平均延迟、P99 延迟
- 加速比（相对单节点）
- 节点负载均衡度（Balance Score）

**预期结果**: 
- 吞吐量随节点数近线性增长
- P99 延迟随节点数降低（负载分散效果）
- 16 节点可能出现扩展效率降低（共享 LLM 端点瓶颈）

**命令**:
```bash
# 实验1
python packages/sage-benchmark/src/sage/benchmark/benchmark_sage/experiments/exp1_single_vs_multi/run_experiment.py --nodes 1 --tasks 2000 --pipeline rag
python packages/sage-benchmark/src/sage/benchmark/benchmark_sage/experiments/exp1_single_vs_multi/run_experiment.py --nodes 4 --tasks 2000 --pipeline rag
python packages/sage-benchmark/src/sage/benchmark/benchmark_sage/experiments/exp1_single_vs_multi/run_experiment.py --nodes 8 --tasks 2000 --pipeline rag
python packages/sage-benchmark/src/sage/benchmark/benchmark_sage/experiments/exp1_single_vs_multi/run_experiment.py --nodes 16 --tasks 2000 --pipeline rag
```

---

### 实验2a: 不同负载级别测试（Load Levels）

**研究问题**: 系统在不同负载级别下的性能特征？

**实验配置**:
- **负载级别**:
  - 低负载: 100 任务, 2 节点, 4 并行度
  - 中负载: 200 任务, 4 节点, 16 并行度
  - 高负载: 500 任务, 8 节点, 64 并行度
- **调度器**: LoadAware
- **Pipeline**: RAG

**测量指标**:
- 各负载级别的吞吐量、延迟、负载均衡
- 调度器在不同负载下的行为差异

**预期结果**:
- 低负载: 高吞吐量（资源未饱和）
- 高负载: 吞吐量下降（LLM 排队增加）
- LoadAware 调度器保持高负载均衡

**命令**:
```bash
python packages/sage-benchmark/src/sage/benchmark/benchmark_sage/experiments/exp2_high_load_parallel/run_experiment.py --load-levels low medium high
```

---

### 实验2b: 调度策略对比（Scheduling Strategy Analysis）

**研究问题**: 不同调度策略（FIFO、LoadAware、Priority）的性能差异？

**实验配置**:
- **调度器**: FIFO, LoadAware-SPREAD, Priority
- **负载**: 中等负载（200 任务, 4 节点）
- **Pipeline**: RAG

**测量指标**:
- 各调度器的吞吐量、负载均衡度
- 调度开销（scheduling overhead）

**预期结果**:
- FIFO: 吞吐量高，但负载不均（某些节点过载）
- LoadAware: 吞吐量适中，负载均衡最佳
- Priority: 吞吐量最高，适合同质化任务

**命令**:
```bash
python packages/sage-benchmark/src/sage/benchmark/benchmark_sage/experiments/exp2_high_load_parallel/run_experiment.py --schedulers fifo load_aware_spread priority
```

---

### 实验3: 并发级别与延迟特性（Concurrency and Latency Characteristics）

**研究问题**: 系统的最优并发度是多少？超过最优点后性能如何恶化？

**实验配置**:
- **节点数**: 4（固定）
- **任务数**: 2000
- **并发度**: 1, 4, 8, 16, 32
- **Pipeline**: RAG

**测量指标**:
- 各并发度下的吞吐量、平均延迟、P99 延迟
- 延迟分解（scheduling delay + queueing delay + execution time）

**预期结果**:
- 存在最优并发度（预计 8-16），吞吐量达到峰值
- 超过最优点后，吞吐量下降、延迟暴增（进入拥塞区）
- 调度开销始终很小（< 1ms）

**命令**:
```bash
python packages/sage-benchmark/src/sage/benchmark/benchmark_sage/experiments/exp3_latency_throughput/run_experiment.py --concurrency 1 4 8 16 32 --tasks 2000 --pipeline rag
```

---

### 实验4a: 多管道隔离（Multi-Pipeline Isolation）

**研究问题**: 多个 pipeline 并发执行时，系统能否保证资源隔离和性能稳定性？

**实验配置**:
- **节点数**: 4
- **Pipeline 类型**: rag, compute, llm（3 种不同类型）
- **启动延迟**: 2.0s（交错启动）
- **每个 pipeline 任务数**: 1000

**测量指标**:
- 每个 pipeline 的吞吐量、延迟、完成时间
- 资源竞争对性能的影响
- 总执行时间 vs 顺序执行时间

**预期结果**:
- 3 个 pipeline 吞吐量方差 < 10%（良好隔离）
- 先启动的 pipeline 性能略好（资源抢占优势）
- 并行执行时间 ≈ 0.4 × 顺序执行时间（2.5x 加速）

**命令**:
```bash
python packages/sage-benchmark/src/sage/benchmark/benchmark_sage/experiments/exp4_parallel_jobs/run_experiment.py --nodes 4 --pipelines rag compute llm --delay 2.0 --tasks 1000
```

---

### 实验4b: Admission Control（准入控制对比）

**研究问题**: 同时启动 vs 延迟启动对尾延迟的影响？

**实验配置**:
- **节点数**: 4
- **Pipeline**: 3 个相同的 rag pipeline
- **启动延迟**: 对比 0s（同时启动）和 2s（交错启动）
- **任务数**: 每个 pipeline 1000 任务

**测量指标**:
- 各 pipeline 的 P99 延迟
- 启动延迟对后续 pipeline 的影响

**预期结果**:
- 交错启动降低后续 pipeline 的 P99 延迟（15-20%）
- 总吞吐量基本不变
- 验证简单准入控制策略的有效性

**命令**:
```bash
python packages/sage-benchmark/src/sage/benchmark/benchmark_sage/experiments/exp4_parallel_jobs/run_experiment.py --experiment staggered --nodes 4 --pipelines rag rag rag --tasks 1000
```

---

## 执行流程

### 自动化脚本

所有实验已整合到 `sage_experiment.sh` 中，串行执行并自动清理资源：

```bash
chmod +x sage_experiment.sh
./sage_experiment.sh
```

### 资源清理策略

每个实验完成后，脚本会自动执行：
```bash
echo "y" | sage jobmanager cleanup
```
确保 Ray 集群的所有资源（CPU/内存/进程）完全释放，避免干扰后续实验。

### 预计执行时间

- 实验1（横向扩展）: ~2 小时（4 次实验 × 2000 任务）
- 实验2a（负载级别）: ~1 小时
- 实验2b（调度对比）: ~1.5 小时（3 个调度器）
- 实验3（并发级别）: ~2.5 小时（5 个并发度）
- 实验4a（多管道隔离）: ~30 分钟
- 实验4b（准入控制）: ~40 分钟

**总计**: ~8-10 小时（视硬件性能而定）

---

## 数据输出

实验结果保存在以下目录：
```
packages/sage-benchmark/src/sage/benchmark/benchmark_sage/experiments/
├── exp1_single_vs_multi/results/
├── exp2_high_load_parallel/results/
├── exp3_latency_throughput/results/
└── exp4_parallel_jobs/results/
```

每个实验包含：
- `metrics.json` - 原始性能指标
- `summary.txt` - 文本格式摘要
- `comparison.txt` - 对比报告
- `*.png` - 可视化图表

---

## 论文对应关系

| 实验 | 论文章节 | LaTeX 表格 |
|------|---------|-----------|
| 实验1 | §5.2 Horizontal Scalability | Table 1: Node Scaling |
| 实验2a | §5.3 Scheduling Strategy Analysis | Table 2: Load Levels |
| 实验2b | §5.3 Scheduling Strategy Analysis | Table 3: Scheduler Comparison |
| 实验3 | §5.4 Concurrency and Latency | Table 4: Throughput Curve<br>Table 5: Latency Breakdown |
| 实验4a | §5.5 Multi-Pipeline Isolation | Table 6: Parallel Jobs |
| 实验4b | §5.5 Multi-Pipeline Isolation | 正文讨论（P99 对比）|

---

## 已知问题与注意事项

### 1. Pipeline 类型限制
- **exp1, exp2, exp3**: 支持 `compute, llm, rag`（单 pipeline）
- **exp4**: 仅支持 `compute, llm, rag`（不支持 `adaptive_rag, rag_service`）
- 如需测试更复杂 pipeline，需修改实验代码支持

### 2. 任务数规模
- 当前脚本使用 2000 任务（exp1/2/3）和 1000 任务（exp4）
- 如硬件性能允许，可提升到 5000-10000 任务以获得更显著的扩展性差异

### 3. 共享 LLM 端点瓶颈
- 所有实验共享单个 A100 GPU 端点
- 16 节点时可能出现 GPU 排队瓶颈，导致扩展效率降低
- 未来可考虑分布式模型服务（多 GPU）

### 4. WSL2 端口问题
- 如在 WSL2 环境运行，vLLM 默认端口 8001 可能失效
- 使用 `SagePorts.get_recommended_llm_port()` 或手动指定 8901

---

## 故障排查

### 实验失败后如何恢复？

1. **检查 Ray 状态**:
   ```bash
   ray status
   ```

2. **手动清理资源**:
   ```bash
   echo "y" | sage jobmanager cleanup
   ray stop --force
   ```

3. **重新运行失败的单个实验**:
   复制对应的 python 命令单独执行

### 数据不一致怎么办？

- 删除 `results/` 目录，重新运行整个实验组
- 确保每次实验后 `cleanup_resources` 成功执行

---

## 改进建议

### 未来实验扩展方向

1. **Pipeline 类型多样化**:
   - 添加 `adaptive_rag`（自适应检索）
   - 添加 `rag_service`（服务型 pipeline，带外部 API 调用）
   - 测试混合 pipeline 场景

2. **更大规模集群**:
   - 扩展到 32/64 节点
   - 研究更大规模下的协调开销

3. **异构任务分布**:
   - 当前任务都是同质化的
   - 引入不同复杂度的任务混合（light/medium/heavy）

4. **容错性测试**:
   - 模拟节点故障
   - 测试 SAGE 的任务重试和恢复机制

---

## 联系与支持

如有问题，请查阅：
- SAGE 文档: `docs-public/docs_src/`
- 实验代码: `packages/sage-benchmark/src/sage/benchmark/benchmark_sage/experiments/`
- 论文草稿: `packages/sage-benchmark/src/sage/benchmark/benchmark_sage/latex/05_experiments.tex`
