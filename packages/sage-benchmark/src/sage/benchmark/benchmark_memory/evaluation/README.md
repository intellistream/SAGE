# Memory Benchmark Evaluation Framework

实验结果分析和可视化框架

## 📁 目录结构

```
evaluation/
├── __init__.py
├── data_analyze.py          # 主入口脚本
├── README.md                # 本文档
├── core/                    # 核心组件
│   ├── __init__.py
│   ├── result_loader.py     # 结果加载器
│   ├── metric_interface.py  # 指标基类接口
│   └── analyzer.py          # 分析器（协调器）
├── accuracy/                # 准确率指标
│   ├── __init__.py
│   ├── f1_score.py          # F1 分数
│   ├── precision.py         # 精确率（待实现）
│   ├── recall.py            # 召回率（待实现）
│   └── exact_match.py       # 精确匹配（待实现）
├── efficiency/              # 效率指标
│   ├── __init__.py
│   ├── latency.py           # 延迟（待实现）
│   └── throughput.py        # 吞吐量（待实现）
└── draw_method/             # 可视化方法
    ├── __init__.py
    ├── line_chart.py        # 折线图
    ├── bar_chart.py         # 柱状图（待实现）
    ├── heatmap.py           # 热力图（待实现）
    └── radar_chart.py       # 雷达图（待实现）
```

## 🚀 快速开始

### 基本用法

```bash
# 分析单个实验结果文件夹
python data_analyze.py --folder .sage/benchmarks/benchmark_memory/locomo/251121 --mode independent

# 指定输出目录
python data_analyze.py --folder .sage/benchmarks/benchmark_memory/locomo/251121 --output ./my_analysis

# 不生成图表
python data_analyze.py --folder .sage/benchmarks/benchmark_memory/locomo/251121 --no-plot
```

### 高级用法

```bash
# 未来支持：聚合模式分析
python data_analyze.py --folder .sage/benchmarks/benchmark_memory/locomo/251121 --mode aggregate

# 指定多个指标
python data_analyze.py --folder .sage/benchmarks/benchmark_memory/locomo/251121 --metrics F1 Precision Recall
```

## 📊 分析模式

### 1. Independent 模式（独立分析）

每个 JSON 文件单独分析，生成独立的指标和图表。

**适用场景**：

- 对比不同配置（如 STM-3 vs STM-5）
- 分析单个任务的性能
- 快速查看每个实验的结果

**输出**：

```
analysis_output/
├── report.txt                  # 文本报告
├── conv-26_F1.png             # 任务 conv-26 的 F1 折线图
├── conv-26_multiple_metrics.png  # 多指标对比图
└── ...
```

### 2. Aggregate 模式（聚合分析，待实现）

将所有 JSON 文件汇总分析，生成整体统计。

**适用场景**：

- 跨任务的平均性能
- 整体趋势分析
- 数据集级别的评估

## 🎯 核心组件说明

### 1. ResultLoader（结果加载器）

负责扫描和加载实验结果文件。

```python
from sage.benchmark.benchmark_memory.evaluation.core import ResultLoader

loader = ResultLoader(".sage/benchmarks/benchmark_memory/locomo/251121")
results = loader.get_all_results()
```

**功能**：

- 递归扫描目录下所有 JSON 文件
- 解析并验证 JSON 格式
- 提供统一的数据访问接口

### 2. BaseMetric（指标基类）

所有指标必须继承此接口。

```python
from sage.benchmark.benchmark_memory.evaluation.core import BaseMetric

class MyMetric(BaseMetric):
    def compute_single_question(self, predicted, reference, metadata=None):
        # 实现单个问题的指标计算
        return score
```

**关键方法**：

- `compute_single_question()`: 计算单个问题的指标值
- `compute_test_round()`: 计算单轮测试的平均值
- `compute_all_rounds()`: 计算所有轮次的指标值
- `compute_overall()`: 计算整体统计信息

### 3. Analyzer（分析器）

协调加载、计算和可视化的核心组件。

```python
from sage.benchmark.benchmark_memory.evaluation.core import Analyzer
from sage.benchmark.benchmark_memory.evaluation.accuracy import F1Score

analyzer = Analyzer(output_dir="./analysis_output")
analyzer.load_results(".sage/benchmarks/benchmark_memory/locomo/251121")
analyzer.register_metric(F1Score())
analyzer.compute_metrics(mode="independent")
analyzer.generate_report()
analyzer.plot_metrics()
```

## 📈 添加新指标

### 步骤 1: 创建指标类

在 `accuracy/` 或 `efficiency/` 目录下创建新文件：

```python
# accuracy/precision.py
from sage.benchmark.benchmark_memory.evaluation.core import BaseMetric

class PrecisionScore(BaseMetric):
    def __init__(self):
        super().__init__(
            name="Precision",
            description="精确率 - 预测正确的比例"
        )

    def compute_single_question(self, predicted_answer, reference_answer, metadata=None):
        # 实现精确率计算逻辑
        pred_tokens = set(predicted_answer.lower().split())
        ref_tokens = set(reference_answer.lower().split())

        if not pred_tokens:
            return 0.0

        common = pred_tokens & ref_tokens
        return len(common) / len(pred_tokens)
```

### 步骤 2: 注册到 `__init__.py`

```python
# accuracy/__init__.py
from .f1_score import F1Score
from .precision import PrecisionScore

__all__ = ["F1Score", "PrecisionScore"]
```

### 步骤 3: 在 `data_analyze.py` 中添加映射

```python
def get_metric_by_name(metric_name: str):
    metric_map = {
        "F1": F1Score,
        "Precision": PrecisionScore,  # 新增
    }
    # ...
```

## 🎨 添加新的可视化方法

### 步骤 1: 创建绘图类

在 `draw_method/` 目录下创建新文件：

```python
# draw_method/bar_chart.py
class BarChart:
    def __init__(self, output_dir="./output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def plot_comparison(self, data, title, save_name):
        # 实现柱状图绘制逻辑
        pass
```

### 步骤 2: 在 Analyzer 中使用

```python
analyzer.plot_metrics(drawer_class=BarChart)
```

## 📝 输出格式

### 文本报告 (report.txt)

```
============================================================
Memory Benchmark Analysis Report
============================================================

任务: conv-26
------------------------------------------------------------

F1:
  平均值: 0.8523
  最大值: 0.9100
  最小值: 0.6500
  标准差: 0.0821
  各轮得分: 0.6500, 0.7200, 0.7800, 0.8200, ...
```

### 图表

1. **单指标折线图** (`{task_id}_{metric_name}.png`)

   - 横坐标：测试轮次
   - 纵坐标：指标值

1. **多指标对比图** (`{task_id}_multiple_metrics.png`)

   - 多条折线对比不同指标

1. **实验对比图** (`experiment_comparison.png`)

   - 对比不同配置的性能

## 🔧 扩展点

### 1. 新的分析模式

在 `Analyzer` 类中添加新方法：

```python
def _compute_aggregate(self):
    """聚合模式：汇总所有文件"""
    # 实现聚合逻辑
    pass
```

### 2. 自定义指标权重

```python
class WeightedF1(BaseMetric):
    def __init__(self, weights):
        self.weights = weights
        # ...
```

### 3. 分类别分析

```python
def compute_by_category(self, test_results, category):
    """按问题类别计算指标"""
    # 过滤特定类别的问题
    # 计算指标
    pass
```

## 📋 TODO

### 高优先级

- [ ] 实现 Precision 指标
- [ ] 实现 Recall 指标
- [ ] 实现 Exact Match 指标
- [ ] 添加 aggregate 模式支持

### 中优先级

- [ ] 实现柱状图绘制
- [ ] 实现热力图绘制（问题难度 vs 准确率）
- [ ] 添加配置文件支持（YAML）
- [ ] 支持按问题类别分析

### 低优先级

- [ ] 实现雷达图绘制
- [ ] 添加延迟和吞吐量指标
- [ ] 生成 HTML 报告
- [ ] 支持导出到 Excel

## 🤝 贡献指南

1. 遵循现有代码风格
1. 新指标必须继承 `BaseMetric`
1. 添加单元测试（在 `__main__` 块）
1. 更新 `__init__.py` 和 `data_analyze.py`
1. 更新本 README

## 📞 联系方式

如有问题或建议，请联系团队。
