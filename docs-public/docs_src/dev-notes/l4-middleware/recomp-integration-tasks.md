# RECOMP 算法集成任务拆分

## 概述

本文档将 RECOMP (Retrieval-Oriented Compression) 算法集成到 SAGE 框架的任务拆分为多个可并行执行的子任务。

**RECOMP 论文**:
[RECOMP: Improving Retrieval-Augmented LMs with Compression and Selective Augmentation](https://arxiv.org/pdf/2310.04408.pdf)

**RECOMP 核心算法**:

1. **Extractive Compressor (recomp_extr)**: 基于双编码器的句子级抽取压缩，选择与 query 最相关的句子
1. **Abstractive Compressor (recomp_abst)**: 基于 T5 的摘要生成，将检索文档压缩为简洁的摘要

**源码位置**:
`packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner/sage_refiner/algorithms/recomp-main/`

______________________________________________________________________

## 任务依赖图

```
                    ┌─────────────────┐
                    │   Task 1 (基础)  │
                    │ recomp_extr 算法 │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌─────────────────┐  ┌────────────────┐  ┌──────────────────┐
    │   Task 2 (算法)  │  │  Task 3 (算法) │  │   Task 4 (评测)   │
    │ recomp_abst 算法 │  │ benchmark管道  │  │   evaluate 修复   │
    └─────────────────┘  └────────┬───────┘  └──────────────────┘
                                  │
                                  ▼
                         ┌───────────────────┐
                         │   Task 5 (集成)    │
                         │ __init__ + config │
                         └───────────────────┘
```

**并行性说明**:

- Task 1 必须最先完成（其他任务依赖其基础结构）
- Task 2, Task 3, Task 4 可在 Task 1 完成后并行执行
- Task 5 需要在 Task 1-3 完成后执行

______________________________________________________________________

## Task 1: Extractive Compressor 实现 (recomp_extr)

**优先级**: 🔴 最高（其他任务的基础）

**目标**: 实现基于 Contriever/DPR 的句子级抽取压缩器

### 1.1 创建目录结构

```bash
packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner/sage_refiner/algorithms/recomp_extr/
├── __init__.py
├── compressor.py      # 核心压缩逻辑
└── operator.py        # SAGE MapOperator 封装
```

### 1.2 compressor.py 实现要点

**核心算法** (参考 `recomp-main/run_extractive_compressor.py`):

```python
class RECOMPExtractiveCompressor:
    """RECOMP Extractive Compressor

    使用预训练的双编码器（Contriever/DPR）对检索文档进行句子级打分，
    选择与 query 最相关的 top-k 句子作为压缩后的上下文。

    支持的模型:
    - fangyuan/nq_extractive_compressor (NQ 数据集微调)
    - fangyuan/tqa_extractive_compressor (TriviaQA 微调)
    - fangyuan/hotpotqa_extractive_compressor (HotpotQA 微调)
    - facebook/contriever-msmarco (通用检索模型)
    """

    def __init__(
        self,
        model_path: str = "fangyuan/nq_extractive_compressor",
        device: str = "cuda",
        top_k: int = 5,           # 选择的句子数
        score_threshold: float = 0.0,  # 分数阈值
    ):
        pass

    def compress(self, context: str, question: str) -> dict:
        """压缩上下文

        步骤:
        1. 将 context 分割为句子
        2. 计算每个句子与 question 的相似度分数
        3. 选择 top-k 高分句子
        4. 按原文顺序拼接选中的句子

        Returns:
            {
                "compressed_context": str,
                "original_tokens": int,
                "compressed_tokens": int,
                "compression_rate": float,
                "num_selected_sentences": int,
                "sentence_scores": List[float],
            }
        """
        pass

    def _split_sentences(self, text: str) -> List[str]:
        """分割句子（使用 NLTK 或简单规则）"""
        pass

    def _compute_scores(self, sentences: List[str], query: str) -> List[float]:
        """计算句子与 query 的相似度分数

        使用 mean pooling + cosine similarity
        """
        pass
```

**关键实现细节**:

1. 使用 `AutoTokenizer` + `AutoModel` 加载 Contriever 模型
1. 使用 `mean_pooling` 获取句子嵌入（参考源码 `mean_pooling` 函数）
1. 支持 batch 处理以提高效率
1. 句子分割使用 NLTK 的 `sent_tokenize`

### 1.3 operator.py 实现要点

```python
class RECOMPExtractiveOperator(MapOperator):
    """RECOMP Extractive Refiner 算子

    输入格式:
        {
            "query": str,
            "retrieval_results": List[str or dict],
        }

    输出格式:
        {
            "query": str,
            "retrieval_results": List[str],  # 保留原始
            "refining_results": List[str],   # 压缩后的句子列表
            "compressed_context": str,
            "original_tokens": int,
            "compressed_tokens": int,
            "compression_rate": float,
        }
    """
    pass
```

### 1.4 验收标准

- [x] 能够加载 `fangyuan/nq_extractive_compressor` 模型
- [x] 能够正确分割句子并计算相似度分数
- [x] 压缩后的文本保持原文句子顺序
- [x] 与现有 pipeline 评测指标兼容

**完成状态**: ✅ 已完成

______________________________________________________________________

## Task 2: Abstractive Compressor 实现 (recomp_abst)

**优先级**: 🟡 中等（可与 Task 3, 4 并行）

**依赖**: Task 1 完成

**目标**: 实现基于 T5 的摘要生成压缩器

### 2.1 创建目录结构

```bash
packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner/sage_refiner/algorithms/recomp_abst/
├── __init__.py
├── compressor.py      # 核心压缩逻辑
└── operator.py        # SAGE MapOperator 封装
```

### 2.2 compressor.py 实现要点

**核心算法** (参考 `recomp-main/train_hf_summarization_model.py`):

```python
class RECOMPAbstractiveCompressor:
    """RECOMP Abstractive Compressor

    使用微调的 T5 模型生成检索文档的摘要。
    输入格式: "Question: {question}\n Document: {passages}\n Summary: "

    支持的模型:
    - fangyuan/nq_abstractive_compressor (NQ 数据集微调)
    - fangyuan/tqa_abstractive_compressor (TriviaQA 微调)
    - fangyuan/hotpotqa_abstractive (HotpotQA 微调)
    - t5-large (通用摘要模型)
    """

    def __init__(
        self,
        model_path: str = "fangyuan/nq_abstractive_compressor",
        device: str = "cuda",
        max_source_length: int = 1024,
        max_target_length: int = 512,
        num_beams: int = 4,
    ):
        pass

    def compress(self, context: str, question: str) -> dict:
        """生成摘要压缩

        步骤:
        1. 构造输入: "Question: {question}\n Document: {context}\n Summary: "
        2. 使用 T5 模型生成摘要
        3. 返回压缩结果

        Returns:
            {
                "compressed_context": str,
                "original_tokens": int,
                "compressed_tokens": int,
                "compression_rate": float,
            }
        """
        pass
```

**关键实现细节**:

1. 使用 `AutoModelForSeq2SeqLM` + `AutoTokenizer` 加载 T5 模型
1. 输入格式必须严格匹配训练时的格式（见 `preprocess_summary_function`）
1. 使用 `model.generate()` 进行推理
1. 处理长文档时需要 truncation

### 2.3 operator.py 实现要点

```python
class RECOMPAbstractiveOperator(MapOperator):
    """RECOMP Abstractive Refiner 算子

    输入/输出格式与 RECOMPExtractiveOperator 相同
    """
    pass
```

### 2.4 验收标准

- [x] 能够加载 `fangyuan/nq_abstractive_compressor` 模型
- [x] 正确构造 T5 输入格式
- [x] 生成的摘要质量合理（人工抽查）
- [x] 与现有 pipeline 评测指标兼容

**完成状态**: ✅ 已完成

______________________________________________________________________

## Task 3: Benchmark Pipeline 实现

**优先级**: 🟡 中等（可与 Task 2, 4 并行）

**依赖**: Task 1 完成

**目标**: 创建 RECOMP 的 benchmark pipeline 和配置文件

### 3.1 创建 Pipeline 文件

```bash
packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/
├── implementations/pipelines/
│   ├── recomp_extr_rag.py    # Extractive pipeline
│   └── recomp_abst_rag.py    # Abstractive pipeline
└── config/
    ├── config_recomp_extr.yaml
    └── config_recomp_abst.yaml
```

### 3.2 recomp_extr_rag.py 实现要点

参考 `reform_rag.py` 结构:

```python
"""
RECOMP Extractive RAG Pipeline
==============================

使用 RECOMP Extractive Compressor 的 RAG pipeline。
"""

def pipeline_run(config):
    env = LocalEnvironment()
    enable_profile = True

    (
        env.from_batch(HFDatasetBatch, config["source"])
        .map(Wiki18FAISSRetriever, config["retriever"], enable_profile=enable_profile)
        .map(RECOMPExtractiveOperator, config["recomp_extr"])  # RECOMP Extractive
        .map(QAPromptor, config["promptor"], enable_profile=enable_profile)
        .map(OpenAIGenerator, config["generator"]["vllm"], enable_profile=enable_profile)
        .map(F1Evaluate, config["evaluate"])
        .map(TokenCountEvaluate, config["evaluate"])
        .map(LatencyEvaluate, config["evaluate"])
        .map(CompressionRateEvaluate, config["evaluate"])
    )

    env.submit()
```

### 3.3 config_recomp_extr.yaml 配置要点

```yaml
pipeline:
  name: "sage-benchmark-recomp-extr-rag"
  description: "RECOMP Extractive RAG Pipeline"

recomp_extr:
  enabled: true
  model_path: "fangyuan/nq_extractive_compressor"
  device: "cuda"
  top_k: 5                    # 选择的句子数
  score_threshold: 0.0        # 分数阈值

# 其他配置参考 config_reform.yaml
```

### 3.4 验收标准

- [x] Pipeline 能够正常运行
- [x] 配置文件格式与现有配置一致
- [x] 支持与 baseline/reform 相同的评测指标

**完成状态**: ✅ 已完成 (2025-12-03)

**已创建的文件**:

- `implementations/pipelines/recomp_extr_rag.py` - RECOMP Extractive RAG pipeline
- `implementations/pipelines/recomp_abst_rag.py` - RECOMP Abstractive RAG pipeline
- `config/config_recomp_extr.yaml` - Extractive 配置文件
- `config/config_recomp_abst.yaml` - Abstractive 配置文件

**注意**: `recomp_abst_rag.py` 需要等待 Task 2 完成（RECOMPAbstractiveOperator 创建）才能正常运行。

______________________________________________________________________

## Task 4: Evaluate 模块检查与修复

**优先级**: 🟡 中等（可与 Task 2, 3 并行）

**依赖**: Task 1 完成（需要理解数据格式）

**目标**: 检查现有评测指标是否与 RECOMP 论文一致，必要时进行修复

### 4.1 RECOMP 论文使用的评测指标

参考 `recomp-main/eval_qa.py` 和 `recomp-main/eval_utils.py`:

1. **Exact Match (EM)**: 标准化后的精确匹配
1. **F1 Score**: Token 级别的 F1 分数

**关键实现细节** (来自 `eval_utils.py`):

```python
def normalize_answer(s):
    """标准化答案文本

    步骤:
    1. 转小写
    2. 移除标点符号
    3. 移除冠词 (a, an, the)
    4. 修复空白字符
    """
    def remove_articles(text):
        return re.sub(r'\b(a|an|the)\b', ' ', text)
    def white_space_fix(text):
        return ' '.join(text.split())
    def remove_punc(text):
        exclude = set(string.punctuation)
        return ''.join(ch for ch in text if ch not in exclude)
    def lower(text):
        return text.lower()
    return white_space_fix(remove_articles(remove_punc(lower(s))))

def compute_f1(a_gold, a_pred):
    """计算 F1 分数"""
    gold_toks = get_tokens(a_gold)
    pred_toks = get_tokens(a_pred)
    common = Counter(gold_toks) & Counter(pred_toks)
    num_same = sum(common.values())
    if len(gold_toks) == 0 or len(pred_toks) == 0:
        return int(gold_toks == pred_toks)
    if num_same == 0:
        return 0
    precision = 1.0 * num_same / len(pred_toks)
    recall = 1.0 * num_same / len(gold_toks)
    f1 = (2 * precision * recall) / (precision + recall)
    return f1
```

### 4.2 与现有 evaluate.py 的对比

**现有实现** (`sage/middleware/operators/rag/evaluate.py`):

```python
class F1Evaluate(MapOperator):
    def _get_tokens(self, text: str):
        return text.lower().split()  # 仅转小写，未移除标点和冠词

    def _f1_score(self, pred: str, ref: str):
        # 使用 Counter 计算 F1，逻辑正确但标准化不完整
```

### 4.3 需要修复的问题

| 问题       | 现状     | RECOMP 标准            | 修复方案                |
| ---------- | -------- | ---------------------- | ----------------------- |
| 文本标准化 | 仅转小写 | 移除标点+冠词+空白修复 | 添加 `normalize_answer` |
| EM 指标    | 未实现   | 有 `single_ans_em`     | 添加 `EMEvaluate` 类    |
| 答案提取   | 直接使用 | 支持 "answer is" 前缀  | 添加 `answer_extract`   |

### 4.4 修复实现

在 `evaluate.py` 中添加:

```python
import re
import string

def normalize_answer(s: str) -> str:
    """RECOMP 风格的答案标准化"""
    def remove_articles(text):
        return re.sub(r'\b(a|an|the)\b', ' ', text)
    def white_space_fix(text):
        return ' '.join(text.split())
    def remove_punc(text):
        exclude = set(string.punctuation)
        return ''.join(ch for ch in text if ch not in exclude)
    def lower(text):
        return text.lower()
    return white_space_fix(remove_articles(remove_punc(lower(s))))

class EMEvaluate(MapOperator):
    """Exact Match 评估器（RECOMP 标准）"""

    def _exact_match(self, pred: str, gold: str) -> int:
        return int(normalize_answer(pred) == normalize_answer(gold))

    def execute(self, data):
        golds = data.get("references", [])
        pred = data.get("generated", "")
        best = max(self._exact_match(pred, g) for g in golds) if golds else 0
        print(f"\033[93m[EM] : {best}\033[0m")
        self.aggregator.add_em(best)  # 需要在 MetricsAggregator 中添加
        return data
```

### 4.5 验收标准

- [x] `normalize_answer` 函数实现与 RECOMP 一致
- [x] F1Evaluate 使用标准化后的文本
- [x] 新增 EMEvaluate 类
- [x] MetricsAggregator 支持 EM 指标汇总
- [x] EMEvaluate 在 `rag/__init__.py` 中导出 (2025-12-03 补充修复)
- [x] 功能测试通过

**完成状态**: ✅ 已完成 (2025-12-03)

**Review 记录** (2025-12-03):

- 发现 EMEvaluate 未在 `sage.middleware.operators.rag.__init__.py` 中导出
- 已修复：添加 `"EMEvaluate": ("sage.middleware.operators.rag.evaluate", "EMEvaluate")` 到 `_IMPORTS`

______________________________________________________________________

## Task 5: 集成与导出

**优先级**: 🟢 最后（需要 Task 1-3 完成）

**依赖**: Task 1, 2, 3 完成

**目标**: 更新 `__init__.py` 和相关导出，确保新算法可被正确导入

### 5.1 更新 algorithms/__init__.py

```python
# 在 algorithms/__init__.py 中添加:

# RECOMP Extractive
from .recomp_extr import RECOMPExtractiveCompressor
__all__.append("RECOMPExtractiveCompressor")

# RECOMP Abstractive  
from .recomp_abst import RECOMPAbstractiveCompressor
__all__.append("RECOMPAbstractiveCompressor")

# SAGE Operators (if available)
try:
    from .recomp_extr import RECOMPExtractiveOperator
    from .recomp_abst import RECOMPAbstractiveOperator
    __all__.extend(["RECOMPExtractiveOperator", "RECOMPAbstractiveOperator"])
except ImportError:
    RECOMPExtractiveOperator = None
    RECOMPAbstractiveOperator = None
```

### 5.2 更新 sage_refiner/__init__.py

```python
# 确保 RECOMPExtractiveOperator 和 RECOMPAbstractiveOperator 可从顶层导入
```

### 5.3 验收标准

- [x] `from sage.middleware.components.sage_refiner import RECOMPExtractiveOperator` 可用
- [x] `from sage.middleware.components.sage_refiner import RECOMPAbstractiveOperator` 可用
- [x] 运行 `ruff check` 无错误
- [x] 功能测试通过

**完成状态**: ✅ 已完成 (2025-12-03)

**验收记录**:

- `algorithms/__init__.py` 正确导出 4 个 RECOMP 类
- `sage_refiner/__init__.py` 顶层导入全部可用
- `EMEvaluate` 已添加到 `sage.middleware.operators.rag` 导出
- 代码质量检查 (ruff) 通过
- Operator 实例化测试通过
- evaluate.py 功能验证通过 (normalize_answer, F1, EM)

______________________________________________________________________

## 开发顺序建议

### 单人开发顺序

```
Day 1: Task 1 (recomp_extr)
Day 2: Task 2 (recomp_abst) + Task 4 (evaluate 修复)
Day 3: Task 3 (benchmark pipeline) + Task 5 (集成)
```

### 多人并行开发 (3 人)

```
Person A: Task 1 → Task 5
Person B: 等待 Task 1 → Task 2
Person C: 等待 Task 1 → Task 3 + Task 4
```

______________________________________________________________________

## 参考文件

| 文件                                          | 用途                 |
| --------------------------------------------- | -------------------- |
| `recomp-main/run_extractive_compressor.py`    | Extractive 核心算法  |
| `recomp-main/train_hf_summarization_model.py` | Abstractive 核心算法 |
| `recomp-main/eval_utils.py`                   | 评测指标实现         |
| `reform/compressor.py`                        | 现有压缩器参考       |
| `reform/operator.py`                          | 现有算子参考         |
| `config_reform.yaml`                          | 现有配置参考         |
| `reform_rag.py`                               | 现有 pipeline 参考   |

______________________________________________________________________

## 测试命令

```bash
# 运行单元测试
pytest packages/sage-middleware/tests/components/sage_refiner/ -v

# 运行 RECOMP Extractive pipeline
python -m sage.benchmark.benchmark_refiner.implementations.pipelines.recomp_extr_rag

# 代码质量检查
sage-dev quality --check-only
```
