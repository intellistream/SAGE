# Runbooks 配置文档

本目录包含流式向量数据库基准测试的 runbook 配置文件。设计参考 big-ann-benchmarks 的 neurips23/runbooks/congestion。

## 📁 目录结构

18 个实验类别，共 60+ 个 runbook 文件：

- **基础测试**: `simple.yaml`, `baseline.yaml`
- **batch_sizes/**: 批量大小实验（8 个文件）
- **event_rates/**: 事件速率实验（11 个文件）
- **deletion_patterns/**: 删除模式实验（5 个文件）
- **bulk_deletion/**: 大量删除实验（5 个文件）
- **random_drop/**: 随机丢弃实验（5 个文件）
- **random_contamination/**: 随机污染实验（5 个文件）
- **stress_tests/**: 压力测试（6 个文件）
- **search_patterns/**: 搜索模式实验
- **data_volumes/**: 数据量实验
- **concept_drift/**: 概念漂移实验
- **dimensions/**: 维度实验
- **multi_modal/**: 多模态实验
- **word_contamination/**: 词污染实验
- **out_of_order/**: 乱序实验
- **fairness/**: 公平性实验（3 个文件）
- **general_experiment/**: 通用实验
- **algo_optimizations/**: 算法优化
- **param_tuning/**: 参数调优

## 🎯 Runbook 格式

## 🎯 Runbook 格式

每个 runbook 文件按照操作序列定义实验流程：

```yaml
dataset-name:
  max_pts: 1000000              # 数据集总向量数

  1:
    operation: "startHPC"       # 启动性能监控

  2:
    operation: "initial"        # 初始化数据
    start: 0
    end: 50000

  3:
    operation: "batch_insert"   # 批量插入
    start: 50000
    end: 1000000
    batchSize: 2500            # 每批向量数
    eventRate: 10000           # 事件速率 (events/sec)

  4:
    operation: "waitPending"    # 等待所有操作完成

  5:
    operation: "search"         # 执行搜索评估

  6:
    operation: "endHPC"         # 结束监控

  gt_url: "none"               # Ground truth URL
```

### 支持的操作

| 操作           | 说明               | 参数                             |
| -------------- | ------------------ | -------------------------------- |
| `startHPC`     | 启动性能监控       | -                                |
| `initial`      | 初始化数据         | start, end                       |
| `batch_insert` | 批量插入           | start, end, batchSize, eventRate |
| `search`       | 执行搜索评估       | -                                |
| `waitPending`  | 等待所有操作完成   | -                                |
| `delete`       | 删除数据           | start, end                       |
| `endHPC`       | 停止监控并保存结果 | -                                |

## 🚀 使用方法

### 基本用法

```bash
# 运行单个实验
python -m benchmark_anns run-streaming \
    --runbook runbooks/simple.yaml \
    --algorithm faiss_hnsw \
    --dataset sift

# 使用备用命令
python run_benchmark.py \
    --algorithm faiss_HNSW \
    --dataset sift \
    --runbook general_experiment
```

### 批量实验

```bash
# 测试所有批量大小
for yaml in runbooks/batch_sizes/*.yaml; do
    python -m benchmark_anns run-streaming \
        --runbook $yaml \
        --algorithm faiss_hnsw \
        --dataset sift
done

# 测试所有事件速率
for yaml in runbooks/event_rates/*.yaml; do
    python run_benchmark.py \
        --algorithm faiss_HNSW \
        --dataset sift \
        --runbook $(basename $yaml .yaml)
done
```

### 对比多个算法

```bash
python -m benchmark_anns run-streaming \
    --runbook runbooks/event_rates/rate_10000.yaml \
    --algorithms faiss_hnsw diskann candy_lshapg \
    --dataset sift
```

## 📊 实验类型说明

### Batch Sizes（批量大小）

- **测试目标**: 不同批量大小对性能的影响
- **固定参数**: eventRate = 10000
- **变化范围**: 100, 500, 1000, 2500, 5000, 10000, 20000, 50000
- **应用场景**: 批处理策略优化

### Event Rates（事件速率）

- **测试目标**: 系统吞吐量上限
- **固定参数**: batchSize = 2500
- **变化范围**: 100 ~ 500000 (11 个级别)
- **应用场景**: 负载能力评估

### Deletion Patterns（删除模式）

- **测试目标**: 索引更新效率
- **删除比例**: 10%, 20%, 30%, 40%, 50%
- **应用场景**: 动态数据管理

### Stress Tests（压力测试）

- **测试目标**: 高负载稳定性
- **压力等级**: 0.1 ~ 0.5 + medium
- **应用场景**: 系统稳定性验证

### 其他实验类型

- **Random Drop**: 模拟数据丢失场景（5%, 10%, 15%, 20%, 25%）
- **Random Contamination**: 数据质量影响评估
- **Concept Drift**: 数据分布变化适应性
- **Fairness**: 算法公平性评估（auto, static_20, static_50）
- **Multi Modal**: 多模态数据处理
- **Out of Order**: 乱序数据处理

## 💡 快速参考

### 常用批量大小

- 100 (极小) → 500 (小) → 1000 (中小) → 2500 (标准) → 5000 (大) → 10000+ (极大)

### 常用事件速率

- 100 (极低) → 1000 (低) → 5000 (中) → 10000 (标准) → 50000 (高) → 100000+ (极高)

### 推荐数据集

- **random-xs**: 10K vectors (快速验证)
- **sift**: 1M vectors (标准测试)
- **glove**: 1.19M vectors (大规模测试)

## 🔍 调试建议

1. **从小规模开始**: 使用 `random-xs` 数据集和 `simple.yaml` 快速验证
1. **逐步增加负载**: 先低速率，再提升到目标速率
1. **监控系统资源**: 关注 CPU、内存、磁盘 I/O
1. **对比基线**: 使用 `baseline.yaml` 建立性能基准
1. **保存实验日志**: 便于问题追踪和结果分析

## 📈 预期性能指标

- **吞吐量**: 10,000 - 50,000 events/sec (取决于算法和硬件)
- **延迟**: P99 < 10ms (取决于负载)
- **召回率**: Recall@10 > 0.95 (取决于算法参数)

## 参考资料

- [big-ann-benchmarks](https://github.com/harsha-simhadri/big-ann-benchmarks)
- 测试文件位置: `runbooks/`
