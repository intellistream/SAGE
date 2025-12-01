# ICML 2025 投稿工作路线图

## 📊 当前状态总览

### ✅ 已完成 (Ready)

| 模块 | 状态 | 说明 |
|------|------|------|
| 框架结构 | ✅ | `benchmark_refiner/` 模块完整，含 experiments, config, implementations |
| 基础算法 | ✅ | LongRefiner, REFORM, Provence, Baseline 实现完成 |
| 新算法原型 | ✅ | AdaptiveCompressor (query_classifier + multi-granularity + MMR) |
| Pipeline模板 | ✅ | 4个 pipeline 文件 (baseline/longrefiner/reform/provence_rag.py) |
| CLI工具 | ✅ | `sage-refiner-bench` 命令已实现 |
| 评测指标 | ✅ | F1, Recall, ROUGE-L, BRS, Accuracy, TokenCount, Latency, CompressionRate |
| 单元测试 | ✅ | 35个测试全部通过 |

### ❌ 未完成 (Critical Blockers)

| 优先级 | 模块 | 问题 | 影响 |
|--------|------|------|------|
| **P0** | 实验执行 | `_process_sample_placeholder()` 使用模拟数据 | 无法进行真实实验 |
| **P0** | 数据集 | 仅配置了 NQ，缺少多数据集支持 | 实验覆盖不足 |
| **P1** | SOTA算法 | 缺少 LLMLingua, RECOMP, xRAG, ECoRAG | 对比不全面 |
| **P1** | 统计检验 | 无显著性检验 (t-test, bootstrap) | 结果不可靠 |
| **P2** | 可视化 | 无图表生成功能 | 论文呈现困难 |
| **P2** | AdaptiveCompressor | 未集成到benchmark框架 | 无法评测新算法 |

---

## 🎯 ICML 投稿必需工作项

### Phase 1: 实验基础设施修复 (预计 3-5 天)

#### 1.1 修复真实 Pipeline 执行 [P0]

**问题**: `comparison_experiment.py` 中的 `_process_sample_placeholder()` 生成随机模拟数据

**文件**: `experiments/comparison_experiment.py`

**修复方案**:
```python
def _execute_pipeline(self, algorithm: str) -> list[dict[str, Any]]:
    """执行真实 Pipeline 并收集结果"""
    # 1. 加载对应配置
    config = self._load_algorithm_config(algorithm)
    
    # 2. 创建 Pipeline 环境
    env = LocalEnvironment()
    results_collector = ResultsCollector()  # 新增：结果收集器
    
    # 3. 构建 Pipeline
    pipeline = self._build_pipeline(env, algorithm, config, results_collector)
    
    # 4. 运行并等待完成
    env.submit()
    env.wait_for_completion()
    
    # 5. 返回收集的结果
    return results_collector.get_results()
```

**需要新增**:
- `ResultsCollector` 类：收集每个样本的评测结果
- `_build_pipeline()` 方法：根据算法类型构建对应 Pipeline
- 修改评测 Operators 以支持结果导出

#### 1.2 多数据集支持 [P0]

**当前状态**: 所有配置文件仅使用 `hf_dataset_config: "nq"`

**FlashRAG 可用数据集 (35个)**:
- Single-hop QA: NQ, TriviaQA, PopQA, WebQ
- Multi-hop QA: HotpotQA, 2WikiMultiHopQA, Musique, Bamboogle
- Long-form QA: ASQA, ELI5
- 其他: Arc-c, MMLU, PubHealth, StrategyQA 等

**ICML 推荐数据集组合**:
| 类型 | 数据集 | 样本数(dev) | 说明 |
|------|--------|-------------|------|
| Single-hop | NQ | 1k+ | 基础事实问答 |
| Single-hop | TriviaQA | 1k+ | 知识密集型 |
| Multi-hop | HotpotQA | 1k+ | 多文档推理 |
| Multi-hop | 2WikiMultiHopQA | 1k+ | 跨文档推理 |
| Long-form | ASQA | 1k+ | 长答案生成 |

**修改文件**:
- `config/*.yaml`: 添加 `datasets` 字段支持多数据集
- `experiments/base_experiment.py`: 添加数据集配置
- `cli.py`: 添加 `--datasets` 参数

**配置示例**:
```yaml
source:
  datasets:
    - name: "nq"
      split: "dev"
      max_samples: 500
    - name: "hotpotqa"
      split: "dev"
      max_samples: 500
    - name: "2wikimultihopqa"
      split: "dev"
      max_samples: 500
```

---

### Phase 2: SOTA 算法实现 (预计 5-7 天)

#### 2.1 必须实现的算法

| 算法 | 类型 | 论文 | 预计工作量 |
|------|------|------|------------|
| **LLMLingua** | Token-level | ACL 2023 | 2天 |
| **LLMLingua-2** | Token-level (BERT) | EMNLP 2024 | 1天 (基于1) |
| **RECOMP** | Abstractive | ACL 2023 | 2天 |
| **Selective-Context** | Sentence-level | EMNLP 2023 | 1天 |

**实现位置**: `sage_refiner/algorithms/`

**接口规范** (参考现有实现):
```python
class BaseCompressor(ABC):
    """压缩器基类"""
    
    @abstractmethod
    def compress(
        self, 
        documents: list[str], 
        query: str,
        budget: int = 2048
    ) -> str:
        """压缩文档到指定token预算"""
        pass
```

#### 2.2 已有算法完善

| 算法 | 当前状态 | 需要完善 |
|------|---------|---------|
| LongRefiner | ✅ 完整 | - |
| REFORM | ✅ 完整 | 添加更多注意力头选择策略 |
| Provence | ✅ 完整 | - |
| **AdaptiveCompressor** | ⚠️ 原型 | 集成到benchmark，完善训练逻辑 |

---

### Phase 3: 实验完整性 (预计 3-4 天)

#### 3.1 统计显著性检验 [P1]

**需要实现**:
```python
# experiments/statistical_analysis.py
class StatisticalAnalyzer:
    """统计分析器"""
    
    def paired_t_test(self, baseline_scores, method_scores) -> dict:
        """配对t检验"""
        pass
    
    def bootstrap_confidence_interval(
        self, scores, n_bootstrap=1000, ci=0.95
    ) -> tuple[float, float]:
        """Bootstrap置信区间"""
        pass
    
    def effect_size_cohens_d(self, baseline_scores, method_scores) -> float:
        """Cohen's d 效应量"""
        pass
```

**报告格式**:
```
Method     | F1↑          | Compression↑  | Latency↓     | p-value
-----------|--------------|---------------|--------------|--------
Baseline   | 0.35 ± 0.02  | 1.0x          | 2.5s         | -
REFORM     | 0.36 ± 0.02  | 2.5x          | 2.8s         | 0.023*
LongRefiner| 0.38 ± 0.02  | 3.0x          | 3.5s         | 0.001**
Adaptive   | 0.40 ± 0.02  | 3.5x          | 3.0s         | <0.001***
```

#### 3.2 可视化模块 [P2]

**需要实现**:
```python
# analysis/visualization.py
class BenchmarkVisualizer:
    """基准测试可视化"""
    
    def plot_performance_comparison(self, results: ExperimentResult) -> Figure:
        """算法性能对比柱状图"""
        pass
    
    def plot_pareto_frontier(self, results: ExperimentResult) -> Figure:
        """F1 vs Compression Pareto前沿"""
        pass
    
    def plot_latency_breakdown(self, results: ExperimentResult) -> Figure:
        """延迟分解堆叠图"""
        pass
    
    def plot_dataset_heatmap(self, results: ExperimentResult) -> Figure:
        """跨数据集性能热力图"""
        pass
```

---

### Phase 4: AdaptiveCompressor 完善 (预计 2-3 天)

#### 4.1 集成到 Benchmark

**需要创建**:
- `config/config_adaptive.yaml`: 配置文件
- `implementations/pipelines/adaptive_rag.py`: Pipeline 实现

#### 4.2 完善训练/推理逻辑

**当前状态**:
- ✅ QueryClassifier: 5种查询类型分类
- ✅ MultiGranularityCompressor: 段落→句子→短语压缩
- ✅ DensityCalculator: MMR多样性 + 信息密度

**需要完善**:
- [ ] 查询分类器微调（当前使用规则）
- [ ] 信息密度模型训练
- [ ] 超参数搜索实验

---

## 📋 详细任务检查清单

### 第一周 (Day 1-7): 基础设施

- [ ] **Day 1-2**: 修复 `_execute_pipeline()` 实现真实 Pipeline 调用
  - [ ] 实现 `ResultsCollector` 类
  - [ ] 修改评测 Operators 支持结果导出
  - [ ] 测试单算法运行
  
- [ ] **Day 3-4**: 多数据集支持
  - [ ] 修改配置文件格式支持多数据集
  - [ ] 实现数据集循环执行逻辑
  - [ ] 添加 CLI `--datasets` 参数

- [ ] **Day 5-7**: 集成测试
  - [ ] 在 NQ 上完整测试 4 种算法
  - [ ] 验证指标收集正确性
  - [ ] 性能基线记录

### 第二周 (Day 8-14): SOTA 算法

- [ ] **Day 8-9**: LLMLingua 实现
  - [ ] 研究论文和官方代码
  - [ ] 实现 `LLMLinguaCompressor`
  - [ ] 单元测试

- [ ] **Day 10-11**: RECOMP 实现
  - [ ] 实现抽象式压缩逻辑
  - [ ] 集成到 benchmark

- [ ] **Day 12**: Selective-Context 实现
  - [ ] 句子级选择逻辑

- [ ] **Day 13-14**: AdaptiveCompressor 集成
  - [ ] 创建配置和 Pipeline
  - [ ] 测试验证

### 第三周 (Day 15-21): 实验运行

- [ ] **Day 15-17**: 主实验
  - [ ] 在 5 个数据集上运行所有算法
  - [ ] 收集原始结果

- [ ] **Day 18-19**: 统计分析
  - [ ] 实现统计检验模块
  - [ ] 计算所有 p-value 和置信区间

- [ ] **Day 20-21**: 可视化和报告
  - [ ] 生成所有图表
  - [ ] 撰写实验结果章节

---

## 📁 文件修改清单

### 需要修改的现有文件

```
benchmark_refiner/
├── experiments/
│   ├── comparison_experiment.py    # 修复 _execute_pipeline()
│   └── base_experiment.py          # 添加数据集配置
├── config/
│   ├── config_*.yaml               # 添加多数据集支持
│   └── __init__.py                 # 导出配置加载函数
├── cli.py                          # 添加 --datasets 参数
└── README.md                       # 更新文档
```

### 需要新增的文件

```
benchmark_refiner/
├── experiments/
│   ├── statistical_analysis.py     # 统计检验模块
│   └── results_collector.py        # 结果收集器
├── analysis/
│   ├── __init__.py
│   └── visualization.py            # 可视化模块
├── algorithms/                     # 新增 SOTA 算法
│   ├── llmlingua/
│   │   ├── __init__.py
│   │   └── compressor.py
│   ├── recomp/
│   │   ├── __init__.py
│   │   └── compressor.py
│   └── selective_context/
│       ├── __init__.py
│       └── compressor.py
├── config/
│   └── config_adaptive.yaml        # AdaptiveCompressor 配置
└── implementations/pipelines/
    └── adaptive_rag.py             # AdaptiveCompressor Pipeline
```

---

## ⏰ 时间估算

| 阶段 | 工作项 | 预计时间 | 依赖 |
|------|--------|----------|------|
| Phase 1 | 基础设施修复 | 3-5 天 | 无 |
| Phase 2 | SOTA 算法实现 | 5-7 天 | Phase 1 |
| Phase 3 | 统计分析+可视化 | 3-4 天 | Phase 2 |
| Phase 4 | AdaptiveCompressor | 2-3 天 | Phase 1 |
| Phase 5 | 实验运行 | 3-5 天 | Phase 2-4 |
| Phase 6 | 论文撰写 | 5-7 天 | Phase 5 |

**总计**: 约 21-31 天（3-4.5 周）

---

## 🚀 快速启动命令

```bash
# 1. 运行当前测试确保基线正常
sage-dev project test --coverage

# 2. 单算法测试 (修复后)
sage-refiner-bench run baseline --dataset nq --samples 10

# 3. 多算法对比 (修复后)
sage-refiner-bench compare \
    --algorithms baseline,longrefiner,reform,provence \
    --datasets nq,hotpotqa,2wikimultihopqa \
    --samples 500 \
    --output results/icml_main.json

# 4. 生成报告
sage-refiner-bench report results/icml_main.json --format latex
```

---

## 📚 参考资源

### 论文
- LLMLingua: https://arxiv.org/abs/2310.05736
- RECOMP: https://arxiv.org/abs/2310.04408
- Selective-Context: https://arxiv.org/abs/2310.06201
- LongRefiner: (内部实现)
- REFORM: (内部实现)

### 代码库
- FlashRAG: https://github.com/RUC-NLPIR/FlashRAG
- LLMLingua Official: https://github.com/microsoft/LLMLingua

### 数据集
- FlashRAG Datasets: https://huggingface.co/datasets/RUC-NLPIR/FlashRAG_datasets

---

*最后更新: 2025-01*
