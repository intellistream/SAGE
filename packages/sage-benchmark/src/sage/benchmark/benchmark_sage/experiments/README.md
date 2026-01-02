# SAGE 分布式调度策略评测

SAGE 分布式调度策略的性能评测实验。

## 目录结构

```
distributed_scheduling/
 common/                         # 通用组件
   ├── models.py                   # 数据模型 (TaskState, Config, Metrics)
   ├── operators.py                # Pipeline 算子
   ├── pipeline.py                 # Pipeline 工厂
   └── visualization.py            # 结果可视化
 exp1_single_vs_multi/           # 实验1: 单节点 vs 多节点
   ├── run_experiment.py           # 实验脚本
   └── results/                    # 输出结果
 exp2_high_load_parallel/        # 实验2: 高负载并行调度
   ├── run_experiment.py
   └── results/
 exp3_latency_throughput/        # 实验3: 延迟与吞吐量
   ├── run_experiment.py
   └── results/
 run_all.sh                      # 运行所有实验
 README.md
```

## 前置条件

1. **启动 Ray 集群** (多节点实验需要):

   ```bash
   # 编辑 config/cluster.yaml 配置节点
   sage cluster start
   ```

1. **启动 JobManager**:

   ```bash
   sage jobmanager start
   ```

1. **LLM/Embedding 服务** (如果使用 RAG/LLM Pipeline):

   ```bash
   sage llm serve
   ```

## 实验说明

### 实验1: 单节点 vs 多节点对比

**测试配置**:

| 配置   | 节点数 | 并行度 | 调度器           |
| ------ | ------ | ------ | ---------------- |
| 单节点 | 1      | 4      | Local            |
| 4节点  | 4      | 16     | LoadAware-SPREAD |
| 8节点  | 8      | 32     | LoadAware-SPREAD |
| 16节点 | 16     | 64     | LoadAware-SPREAD |
| 30节点 | 30     | 120    | LoadAware-SPREAD |

**运行**:

```bash
cd exp1_single_vs_multi

# 完整实验
python run_experiment.py

# 快速测试
python run_experiment.py --quick

# 指定节点数
python run_experiment.py --nodes 1 4 8 --tasks 500
```

**输出指标**:

- 吞吐量 (tasks/sec)
- 平均延迟 / P50 / P95 / P99 延迟
- 节点分布均衡度

### 实验2: 高负载流水线并行调度

**负载级别**:

| 级别     | 并行度 | 节点数 | 任务数 |
| -------- | ------ | ------ | ------ |
| 低负载   | 4      | 2      | 100    |
| 中负载   | 16     | 4      | 200    |
| 高负载   | 64     | 8      | 500    |
| 极高负载 | 128    | 16     | 1000   |

**调度策略对比**:

- FIFO: 先进先出
- LoadAware-SPREAD: 负载感知 + 分散策略
- LoadAware-PACK: 负载感 + 紧凑策略
- RoundRobin: 轮询
- Priority: 优先级

**流水线深度**:

- 浅层: 2 阶段
- 中层: 3 阶段
- 深层: 5 阶段

**运行**:

```bash
cd exp2_high_load_parallel

# 完整实验
python run_experiment.py

# 快速测试
python run_experiment.py --quick

# 指定调度器
python run_experiment.py --schedulers fifo load_aware_spread round_robin

# 指定负载级别
python run_experiment.py --load-levels low medium high
```

### 实验3: 调度延迟与吞吐量精细测量

'ENDOFFILE'

**测量项**:

- 调度延迟: 任务提交到分配的时间
- 排队延迟: 分配到开始执行的时间 if current_time - self._cache_time > self._
- 端到端延迟: 总时间

**并发度测试**:

- 1, 2, 4, 8, 16, 32 并发

**运行**:

```bash
cd exp3_latency_throughput

# 完整实验
python run_experiment.py

# 快速测试
python run_experiment.py --quick

# 指定并发度
python run_experiment.py --concurrency 1 4 8 16 32 --tasks 500
```

## 快速开始

```bash
# 1. 启动服务
sage jobmanager start
sage cluster start

# 2. 运行快速测试
./run_all.sh --quick

# 3. 查看结果
ls exp1_single_vs_multi/results/
ls exp2_high_load_parallel/results/
ls exp3_latency_throughput/results/
```

## 输出文件

```
    if current_time - self._cache_ttl: > self._cache_::::::
```

| 文件               | 描述                    |
| ------------------ | ----------------------- |
| `*_summary.txt`    | 人类可                  |
| `*_metrics.json`   | 完整的 JSON 指标数据    |
| `*_latencies.csv`  | 延迟数据 CSV (便于分析) |
| `*_comparison.txt` | 多配置对比报告          |
| `*_throughput.png` | 吞吐量对比图            |
| `*_latency.png`    | 延迟对比图              |
| `*_nodes.png`      | 节点分                  |

## 自定义实验

'ENDOFFILE''ENDOFFILE'--------的配置常量来自定义实验:

```python
# exp1_single_vs_multi/run_experiment.py
EXPERIMENT_CONFIGS = {
    "custom_config": {
        "use_remote": True,
        "num_nodes": 10,
        "parallelism": 40,
        "scheduler_type": "load_aware",
    },
}
```

## 注意事项

1. **多节点实验** 需要先配置 `config/cluster.yaml` 中的节点列表
1. **LLM/RAG Pipeline**LLM 服务已启动 'ENDOFFILE'
1. **大规模实验** 可能需要较长时间，建议先用 `--quick` 测试
1. **结果文件** 带时间戳，不会覆盖旧结果
