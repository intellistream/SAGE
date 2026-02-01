# 实验4: 并行作业执行能力测试

## 概述

测试 SAGE 同时执行多个不同类型 Pipeline 的能力，评估系统的并发作业处理能力和资源竞争影响。

## 实验场景

### 1. 基础并行实验 (basic)

- 同时或延迟启动多个 Pipeline
- Pipeline 类型: compute, llm, rag
- 可以运行相同或不同类型的 Pipeline
- 测量每个 Pipeline 的吞吐量、延迟、资源竞争影响

### 2. 同时启动 vs 延迟启动对比 (staggered)

- 对比不同启动延迟对性能的影响
- 测试延迟: 0s (同时), 1s, 2s, 5s
- 评估错峰启动是否能提升整体性能

### 3. 作业数量扩展性测试 (scaling)

- 测试系统处理 1, 2, 4, 8... 个并发作业的能力
- 评估吞吐量和延迟随作业数量的变化趋势
- 识别系统的扩展瓶颈

## 使用示例

### 基础并行实验

```bash
# 运行默认实验 (3个pipeline: rag, compute, llm，同时启动)
python run_experiment.py

# 指定 pipeline 类型
python run_experiment.py --pipelines rag compute llm

# 运行3个相同的 RAG pipeline，间隔2秒启动
python run_experiment.py --pipelines rag rag rag --delay 2.0

# 每个pipeline使用不同的任务数
python run_experiment.py --pipelines compute llm --tasks 100 200

# 快速测试模式（更少任务，2个节点）
python run_experiment.py --quick
```

### 延迟启动对比实验

```bash
# 对比不同延迟的影响
python run_experiment.py --experiment staggered --pipelines rag compute llm

# 快速测试（只测试0s和2s延迟）
python run_experiment.py --experiment staggered --quick
```

### 扩展性测试

```bash
# 测试1, 2, 4, 8个 RAG 作业
python run_experiment.py --experiment scaling --base-pipeline rag --num-jobs 1 2 4 8

# 测试 compute pipeline 的扩展性
python run_experiment.py --experiment scaling --base-pipeline compute --num-jobs 1 2 4
```

## 参数说明

### 基础参数

- `--pipelines`: Pipeline 类型列表 (compute, llm, rag)，可重复，默认: `rag compute llm`
- `--delay`: 相邻 pipeline 启动的时间间隔（秒），默认: `0.0` (同时启动)
- `--tasks`: 每个 pipeline 的任务数，支持列表，默认: `200`
- `--parallelism`: 每个 pipeline 的并行度，默认: `8`
- `--nodes`: 集群节点数，默认: `4`
- `--output`: 输出目录（默认自动生成）

### 实验类型

- `--experiment`: 实验类型
  - `basic`: 基础并行实验（默认）
  - `staggered`: 同时启动 vs 延迟启动对比
  - `scaling`: 作业数量扩展性测试

### 扩展性测试参数

- `--base-pipeline`: 基础 pipeline 类型 (compute, llm, rag)，默认: `rag`
- `--num-jobs`: 要测试的作业数量列表，默认: `1 2 4 8`

### 其他

- `--quick`: 快速测试模式（任务数50，节点数2）

## 测量指标

### 单作业指标

- **Throughput (吞吐量)**: 任务/秒
- **Avg Latency (平均延迟)**: 毫秒
- **P95/P99 Latency**: 95%/99% 分位延迟
- **Duration**: 作业执行时长
- **Node Balance Score**: 节点负载均衡分数

### 整体指标

- **Total Duration**: 所有作业完成的总时长
- **Success Rate**: 成功作业比例
- **Total Throughput**: 所有作业吞吐量之和
- **Avg Job Throughput**: 单作业平均吞吐量

## 输出文件

### 基础实验输出

```
results/parallel_3jobs_rag_compute_llm_concurrent_20260115_120000/
├── parallel_jobs_summary.json     # JSON格式结果
├── parallel_jobs_report.txt       # 文本格式报告
├── parallel_jobs_comparison.txt   # 作业间对比
├── job0_rag_summary.txt           # 各作业详细结果
├── job0_rag_metrics.json
├── job0_rag_latencies.csv
├── job1_compute_summary.txt
├── ...
```

### 延迟对比实验输出

```
results/concurrent_vs_staggered_20260115_120000/
├── staggered_comparison_report.txt  # 总体对比报告
├── delay_0ms/                       # 同时启动结果
│   ├── parallel_jobs_summary.json
│   └── ...
├── delay_1000ms/                    # 1秒延迟结果
├── delay_2000ms/                    # 2秒延迟结果
└── delay_5000ms/                    # 5秒延迟结果
```

### 扩展性测试输出

```
results/scaling_rag_20260115_120000/
├── scaling_report.txt               # 扩展性分析报告
├── jobs_1/                          # 1个作业结果
├── jobs_2/                          # 2个作业结果
├── jobs_4/                          # 4个作业结果
└── jobs_8/                          # 8个作业结果
```

## 实验设计考虑

### 1. 线程安全

- 使用 Python 线程池并发启动多个 Pipeline
- 每个作业在独立线程中运行，互不干扰
- 结果收集使用线程安全的数据结构

### 2. 资源竞争

- 所有作业共享同一集群资源
- 通过调度器（load_aware + spread策略）分配任务
- 观察资源竞争对性能的影响

### 3. 启动延迟

- `--delay 0.0`: 所有作业同时启动，最大资源竞争
- `--delay > 0`: 错峰启动，减少初始资源竞争
- 用于研究启动策略对整体性能的影响

### 4. 混合工作负载

- 支持不同类型的 Pipeline 混合运行
- compute: 纯计算密集型
- llm: LLM 推理密集型
- rag: 检索+推理混合型

## 与其他实验的关系

- **实验1 (单节点 vs 多节点)**: 关注节点扩展性
- **实验2 (高负载并行流)**: 关注单个大规模流水线
- **实验3 (延迟吞吐量)**: 关注调度性能
- **实验4 (并行作业)**: 关注多作业并发能力 ← 本实验

## 典型使用场景

1. **多租户场景**: 模拟多个用户同时提交不同的数据处理任务
1. **混合工作负载**: 评估系统处理不同类型作业的能力
1. **资源规划**: 确定系统可以稳定支持的并发作业数量
1. **调度策略评估**: 观察不同启动策略对整体性能的影响

## 注意事项

1. **资源限制**: 确保集群有足够资源运行所有作业
1. **避免 OOM**: 并发作业数过多可能导致内存不足
1. **网络带宽**: 多作业并发可能增加网络压力
1. **监控指标**: 建议同时监控系统资源使用情况

## 故障排查

### 问题: 部分作业失败

- 检查集群资源是否充足
- 减少并发作业数或任务数
- 查看各作业的错误日志

### 问题: 性能下降明显

- 考虑增加启动延迟 (--delay)
- 减少每个作业的并行度 (--parallelism)
- 增加集群节点数 (--nodes)

### 问题: 作业卡死

- 检查是否有死锁或资源竞争
- 查看调度器日志
- 尝试使用不同的调度策略

## 下一步

基于实验结果，可以：

1. 调整调度策略以优化多作业场景
1. 实现作业间资源隔离
1. 开发智能启动策略（根据系统负载动态调整）
1. 优化资源分配算法
