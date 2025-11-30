# Memory Benchmark - 评估模块

## 📋 概述

本目录用于 Memory Benchmark 的实验结果分析与评估。

## ⚠️ 当前状态

**本模块处于早期探索阶段**

由于算法集成尚未完成（LoCoMo、LongMem、ReMI等算法仍在开发中），暂时无法进行全量算法的系统化对比评估。

当前采用\*\*专项分析（Specialized Analysis）\*\*的方式，进行指标探索和初步可视化。

## 📁 目录结构

```
evaluation/
├── README.md                       # 本文档
└── specialized_analysis/           # 专项分析目录（探索阶段）
    ├── README.md                   # 专项分析说明
    ├── explore_metrics.py          # 指标探索脚本
    ├── quick_visualize.py          # 快速可视化脚本
    └── results/                    # 分析结果输出
        ├── metrics/                # 指标计算结果
        └── plots/                  # 图表文件
```

## 🚀 快速开始

### 1. 指标探索

计算基础指标（F1、精确匹配率等）：

```bash
cd packages/sage-benchmark/src/sage/benchmark/benchmark_memory/evaluation/specialized_analysis

# 分析整个结果文件夹
python explore_metrics.py \
    --input /path/to/benchmark/results \
    --output ./results/metrics

# 只分析特定任务
python explore_metrics.py \
    --input /path/to/benchmark/results \
    --task conv-26 \
    --output ./results/metrics
```

### 2. 快速可视化

生成指标变化曲线和对比图：

```bash
# 从原始结果生成图表
python quick_visualize.py \
    --input /path/to/benchmark/results \
    --output ./results/plots

# 从已计算的指标文件生成图表
python quick_visualize.py \
    --input ./results/metrics/metrics_results.json \
    --mode from_metrics \
    --output ./results/plots
```

## 📊 当前支持的指标

### 准确性指标

- **Token-based F1**: 基于词级别的F1分数
- **Precision**: 精确率
- **Recall**: 召回率
- **Exact Match**: 精确匹配率（答案完全一致）

### 统计信息

- 各轮次指标值
- 平均值、最大值、最小值
- 跨任务对比

## 🔮 未来规划

等算法集成完成后，本模块将重构为**系统化评估框架**，包括：

### 1. 全面的评估指标

- **准确性**: F1、EM、ROUGE、BLEU等
- **效率**: 推理时间、内存使用、token消耗
- **鲁棒性**: 噪声干扰、长度变化的影响
- **可解释性**: 记忆召回分析、注意力可视化

### 2. 标准化报告

- 自动生成论文级别的对比图表
- LaTeX表格导出
- 统计显著性测试

### 3. 多维度对比

- 不同算法横向对比（LoCoMo vs LongMem vs ReMI）
- 不同数据集纵向分析（LongBench vs InfBench）
- 参数影响分析（记忆大小、更新策略等）

### 4. 消融实验支持

- 组件效果分析
- 超参数敏感性测试
- 最优配置推荐

## 📝 注意事项

1. **当前脚本仅供探索使用**，代码质量以快速迭代为主
1. **分析结果仅供参考**，不作为最终论文数据
1. **发现问题请及时记录**，为后续重构提供依据
1. 详细使用说明见 `specialized_analysis/README.md`

## 🤝 贡献指南

如果你在探索过程中：

- 发现有用的指标 → 记录在 `specialized_analysis/` 中
- 遇到数据格式问题 → 提issue或直接修复
- 有可视化想法 → 直接在脚本中尝试

所有探索性的工作都欢迎！等算法齐全后，我们会一起重构为正式的评估框架。
