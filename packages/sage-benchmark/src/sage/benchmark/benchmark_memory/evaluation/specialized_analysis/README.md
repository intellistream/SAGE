# Specialized Analysis - 专项分析

## 目的

本目录用于对 Memory Benchmark 的实验结果进行**探索性分析**，目标是：

1. **探索适用指标**：测试哪些指标适合评估记忆增强系统（F1、准确率、召回率等）
1. **初步可视化**：生成基础图表，观察算法在不同场景下的表现
1. **问题发现**：识别当前实验中的问题和改进方向

## 当前状态

⚠️ **本目录处于早期探索阶段**

- 算法集成尚未完成，无法做全量算法对比
- 暂时采用简单的分析脚本，快速迭代
- 待算法齐全后，会重构为系统化的评估框架

## 目录结构

```
specialized_analysis/
├── README.md                    # 本文档
├── explore_metrics.py           # 指标探索脚本
├── quick_visualize.py           # 快速可视化脚本
└── results/                     # 分析结果输出目录
    ├── metrics/                 # 指标计算结果
    └── plots/                   # 图表输出
```

## 使用方法

### 1. 指标探索

```bash
# 计算基础指标（F1、准确率等）
python explore_metrics.py --input .sage/benchmarks/benchmark_memory/locomo/251121 --output ./results/metrics

# 指定特定任务
python explore_metrics.py --input .sage/benchmarks/benchmark_memory/locomo/251121 --task conv-26
```

### 2. 快速可视化

```bash
# 生成轮次变化曲线
python quick_visualize.py --input .sage/benchmarks/benchmark_memory/locomo/251121 --output ./results/plots

# 只画特定指标
python quick_visualize.py --input .sage/benchmarks/benchmark_memory/locomo/251121 --metric f1
```

## 下一步计划

等算法集成完成后（完整版 LoCoMo、优化版 LongMem、ReMI 等），将进行：

1. **系统化评估框架**：统一的指标计算、多算法对比
1. **标准化报告**：自动生成论文级别的对比图表
1. **性能分析**：内存使用、推理速度等效率指标
1. **消融实验**：不同配置参数的影响分析

## 注意事项

- 本目录的代码以**快速迭代**为主，不保证代码质量
- 分析结果仅供参考，不作为最终论文数据
- 发现问题请及时记录，为后续重构提供依据
