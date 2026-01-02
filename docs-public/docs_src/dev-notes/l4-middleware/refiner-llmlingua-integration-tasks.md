# LongLLMLingua & LLMLingua2 集成任务清单

> **创建日期**: 2025-12-02\
> **分支**: feature/refiner\
> **目标**: 在 sageRefiner 中复现 LongLLMLingua 和 LLMLingua2，并清理 adaptive 和 llmlingua 旧实现

______________________________________________________________________

## 项目结构概览

```
关键路径:
├── packages/sage-middleware/src/sage/middleware/components/sage_refiner/
│   ├── sageRefiner/sage_refiner/algorithms/
│   │   ├── longllmlingua/          # ✅ 已实现 (使用 pip llmlingua 包)
│   │   │   ├── __init__.py
│   │   │   ├── compressor.py       # LongLLMLinguaCompressor
│   │   │   └── operator.py         # LongLLMLinguaOperator
│   │   ├── llmlingua2/             # ✅ 已实现 (使用 pip llmlingua 包)
│   │   │   ├── __init__.py
│   │   │   ├── compressor.py       # LLMLingua2Compressor
│   │   │   └── operator.py         # LLMLingua2Operator
│   │   ├── llmlingua/              # ✅ 已删除
│   │   ├── adaptive/               # ✅ 已删除
│   │   ├── LongRefiner/            # ✅ 保留
│   │   ├── provence/               # ✅ 保留
│   │   └── reform/                 # ✅ 保留
│   └── __init__.py                 # ✅ 已更新导出
│
└── packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/
    ├── implementations/pipelines/
    │   ├── llmlingua_rag.py        # ✅ 已删除
    │   ├── adaptive_rag.py         # ✅ 已删除
    │   ├── longllmlingua_rag.py    # ✅ 已创建
    │   └── llmlingua2_rag.py       # ✅ 已创建
    ├── config/
    │   ├── config_llmlingua.yaml   # ✅ 已删除
    │   ├── config_adaptive.yaml    # ✅ 已删除
    │   ├── config_longllmlingua.yaml  # ✅ 已创建
    │   └── config_llmlingua2.yaml     # ✅ 已创建
    ├── tests/
    │   ├── test_longllmlingua.py   # ✅ 已创建 (29 tests)
    │   └── test_llmlingua2.py      # ✅ 已创建
    └── experiments/base_experiment.py  # ✅ 已更新 (移除 llmlingua/adaptive, 添加 llmlingua2/longllmlingua)
```

______________________________________________________________________

## 任务拆分 (可并行执行)

### 🔵 任务组 A: 清理旧代码 (独立，可优先执行)

#### Task A1: 删除 sageRefiner 中的 adaptive 和 llmlingua 模块 ✅ 已完成

**负责人**: Copilot 1\
**预计时间**: 15 分钟\
**依赖**: 无\
**状态**: ✅ 已完成

**操作清单**:

1. 删除目录:

   - `packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner/sage_refiner/algorithms/adaptive/`
   - `packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner/sage_refiner/algorithms/llmlingua/`

1. 更新 `sageRefiner/sage_refiner/algorithms/__init__.py`:

   - 移除 adaptive 相关导入和导出
   - 移除 llmlingua 相关导入和导出 (旧版)

1. 更新 `sage_refiner/__init__.py` (如果存在相关导出)

**验证**:

```bash
# 确保删除后不影响其他模块
python -c "from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms import LongRefinerCompressor, ProvenceCompressor, REFORMCompressor"
```

______________________________________________________________________

#### Task A2: 删除 benchmark_refiner 中的 adaptive 和 llmlingua Pipeline ✅ 已完成

**负责人**: Copilot 1 (接续 A1)\
**预计时间**: 15 分钟\
**依赖**: 无\
**状态**: ✅ 已完成

**操作清单**:

1. 删除 Pipeline 文件:

   - `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/implementations/pipelines/adaptive_rag.py`
   - `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/implementations/pipelines/llmlingua_rag.py`

1. 删除配置文件:

   - `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/config/config_adaptive.yaml`
   - `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/config/config_llmlingua.yaml`

1. 更新 `implementations/pipelines/__init__.py` (如有相关导出)

1. 更新 `implementations/__init__.py` (如有相关导出)

**验证**:

```bash
# 确保 benchmark_refiner 仍可导入
python -c "from sage.benchmark.benchmark_refiner import RefinerExperimentRunner"
```

______________________________________________________________________

#### Task A3: 更新 sage_refiner 主 __init__.py ✅ 已完成

**负责人**: Copilot 1 (接续 A2)\
**预计时间**: 10 分钟\
**依赖**: A1\
**状态**: ✅ 已完成

**操作清单**:

1. 编辑 `packages/sage-middleware/src/sage/middleware/components/sage_refiner/__init__.py`:
   - 移除 `AdaptiveCompressor`, `AdaptiveRefinerOperator` 相关代码
   - 移除 `LLMLinguaCompressor`, `LLMLinguaRefinerOperator` 相关代码
   - 更新 `__all__` 列表

**验证**:

```bash
python -c "from sage.middleware.components.sage_refiner import REFORMCompressor, LongRefinerCompressor, ProvenceCompressor"
```

______________________________________________________________________

#### Task A4: 更新 benchmark_refiner 枚举和框架 ✅ 已完成

**负责人**: Copilot 1 (接续 A2)\
**预计时间**: 10 分钟\
**依赖**: A2\
**状态**: ✅ 已完成

**操作清单**:

1. 编辑 `experiments/base_experiment.py`:

   - 从 `RefinerAlgorithm` 枚举中移除 `LLMLINGUA = "llmlingua"` 和 `ADAPTIVE = "adaptive"`
   - 更新 `available()` 方法

1. 删除测试文件 (如存在):

   - `packages/sage-benchmark/tests/benchmark_refiner/test_llmlingua.py`
   - `packages/sage-benchmark/tests/benchmark_refiner/test_adaptive.py`

**验证**:

```bash
python -c "from sage.benchmark.benchmark_refiner.experiments import RefinerAlgorithm; print(RefinerAlgorithm.available())"
```

______________________________________________________________________

### 🟢 任务组 B: 实现 LongLLMLingua (独立)

#### Task B1: 创建 LongLLMLingua Compressor ✅ 已完成

**负责人**: Copilot 2\
**预计时间**: 45 分钟\
**依赖**: 无 (可与 A 并行)\
**状态**: ✅ 已完成

**背景**: LongLLMLingua 是 LLMLingua 的扩展版本，专为长文档场景优化，核心是 `rank_method="longllmlingua"`。

**实现说明**:

- 使用 `pip install llmlingua` 安装的包，而非本地源码
- 默认配置符合论文 baseline (rate=0.55, condition_compare=True)
- 详见 `DEFAULT_LONG_LLMLINGUA_CONFIG`

**操作清单**:

1. 创建目录:

   ```
   packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner/sage_refiner/algorithms/longllmlingua/
   ```

1. 创建文件:

   - `__init__.py`
   - `compressor.py` - LongLLMLinguaCompressor 类
   - `operator.py` - LongLLMLinguaOperator (SAGE 算子封装)

1. `LongLLMLinguaCompressor` 核心实现 (已完成):

   ```python
   from llmlingua import PromptCompressor  # 使用 pip 包

   # 论文 baseline 默认配置
   DEFAULT_LONG_LLMLINGUA_CONFIG = {
       "rate": 0.55,  # 论文 baseline
       "condition_in_question": "after",
       "reorder_context": "sort",
       "dynamic_context_compression_ratio": 0.3,
       "condition_compare": True,  # 关键：启用对比困惑度
       ...
   }

   class LongLLMLinguaCompressor:
       """LongLLMLingua: 针对长文档优化的 Prompt 压缩器"""
       def __init__(self, model_name="NousResearch/Llama-2-7b-hf", device="cuda"):
           from llmlingua import PromptCompressor  # pip 包
           self.compressor = PromptCompressor(model_name=model_name, device_map=device)
   ```

1. 更新 `algorithms/__init__.py` 添加导出

**验证**:

```bash
python -c "from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.longllmlingua import LongLLMLinguaCompressor"
```

______________________________________________________________________

#### Task B2: 创建 LongLLMLingua RAG Pipeline

**负责人**: Copilot 2 (接续 B1)\
**预计时间**: 30 分钟\
**依赖**: B1

**操作清单**:

1. 创建配置文件:
   `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/config/config_longllmlingua.yaml`

   ```yaml
   pipeline:
     name: "sage-benchmark-longllmlingua-rag"
     description: "LongLLMLingua RAG Pipeline for Long Documents"

   longllmlingua:
     enabled: true
     model_name: "NousResearch/Llama-2-7b-hf"  # 或 meta-llama/Llama-2-7b-hf
     device: "cuda:0"
     rate: 0.5
     target_token: 2048
     condition_in_question: "after"
     reorder_context: "sort"
     dynamic_context_compression_ratio: 0.3
     use_context_level_filter: true
     use_token_level_filter: true
   ```

1. 创建 Pipeline 文件:
   `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/implementations/pipelines/longllmlingua_rag.py`

**验证**:

```bash
# 测试模式验证
SAGE_TEST_MODE=true python packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/implementations/pipelines/longllmlingua_rag.py
```

______________________________________________________________________

#### Task B3: 更新枚举添加 LONGLLMLINGUA

**负责人**: Copilot 2 (接续 B2)\
**预计时间**: 10 分钟\
**依赖**: B2, A4 完成后

**操作清单**:

1. 编辑 `experiments/base_experiment.py`:

   - 添加 `LONGLLMLINGUA = "longllmlingua"` 到 `RefinerAlgorithm` 枚举
   - 更新 `available()` 方法

1. 更新 `sage_refiner/__init__.py` 导出新的 Compressor 和 Operator

______________________________________________________________________

### 🟡 任务组 C: 实现 LLMLingua2 (独立)

#### Task C1: 创建 LLMLingua2 Compressor

**负责人**: Copilot 3\
**预计时间**: 45 分钟\
**依赖**: 无 (可与 A, B 并行)

**背景**: LLMLingua2 是基于 BERT 的快速 token 分类压缩器，使用 `use_llmlingua2=True`。

**参考**:

- [LLMLingua-2 Paper](https://arxiv.org/abs/2403.12968)
- 默认模型: `microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank`

**操作清单**:

1. 创建目录:

   ```
   packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner/sage_refiner/algorithms/llmlingua2/
   ```

1. 创建文件:

   - `__init__.py`
   - `compressor.py` - LLMLingua2Compressor 类
   - `operator.py` - LLMLingua2Operator (SAGE 算子封装)

1. `LLMLingua2Compressor` 核心实现 (已完成):

   ```python
   from llmlingua import PromptCompressor  # 使用 pip 包

   class LLMLingua2Compressor:
       """LLMLingua-2: 基于 BERT Token 分类的快速 Prompt 压缩器"""
       DEFAULT_MODEL = "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank"

       def __init__(self, model_name=None, device="cuda"):
           from llmlingua import PromptCompressor  # pip 包
           self.compressor = PromptCompressor(
               model_name=model_name or self.DEFAULT_MODEL,
               device_map=device,
               use_llmlingua2=True,
           )
   ```

1. 更新 `algorithms/__init__.py` 添加导出

**验证**:

```bash
python -c "from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.llmlingua2 import LLMLingua2Compressor"
```

______________________________________________________________________

#### Task C2: 创建 LLMLingua2 RAG Pipeline

**负责人**: Copilot 3 (接续 C1)\
**预计时间**: 30 分钟\
**依赖**: C1

**操作清单**:

1. 创建配置文件:
   `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/config/config_llmlingua2.yaml`

   ```yaml
   pipeline:
     name: "sage-benchmark-llmlingua2-rag"
     description: "LLMLingua-2 RAG Pipeline with BERT Token Classification"

   llmlingua2:
     enabled: true
     model_name: "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank"
     device: "cuda:0"
     rate: 0.5
     target_token: 2048
     use_context_level_filter: true
     use_token_level_filter: true
     force_tokens: ["\n", ".", "?", "!"]
     drop_consecutive: false
   ```

1. 创建 Pipeline 文件:
   `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/implementations/pipelines/llmlingua2_rag.py`

**验证**:

```bash
SAGE_TEST_MODE=true python packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/implementations/pipelines/llmlingua2_rag.py
```

______________________________________________________________________

#### Task C3: 更新枚举添加 LLMLINGUA2

**负责人**: Copilot 3 (接续 C2)\
**预计时间**: 10 分钟\
**依赖**: C2, A4 完成后

**操作清单**:

1. 编辑 `experiments/base_experiment.py`:

   - 添加 `LLMLINGUA2 = "llmlingua2"` 到 `RefinerAlgorithm` 枚举
   - 更新 `available()` 方法

1. 更新 `sage_refiner/__init__.py` 导出新的 Compressor 和 Operator

______________________________________________________________________

### 🔴 任务组 D: 集成与测试 (需等待 A, B, C 完成)

#### Task D1: 更新 sage_refiner 主导出 ✅ 已完成

**负责人**: Copilot 4\
**预计时间**: 20 分钟\
**依赖**: A3, B1, C1\
**状态**: ✅ 已完成

**操作清单**:

1. 编辑 `packages/sage-middleware/src/sage/middleware/components/sage_refiner/__init__.py`:
   ```python
   # LongLLMLingua算法
   try:
       from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.longllmlingua import (
           LongLLMLinguaCompressor,
           LongLLMLinguaOperator,
       )
       __all__.extend(["LongLLMLinguaCompressor", "LongLLMLinguaOperator"])
   except ImportError:
       LongLLMLinguaCompressor = None
       LongLLMLinguaOperator = None

   # LLMLingua2算法
   try:
       from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.llmlingua2 import (
           LLMLingua2Compressor,
           LLMLingua2Operator,
       )
       __all__.extend(["LLMLingua2Compressor", "LLMLingua2Operator"])
   except ImportError:
       LLMLingua2Compressor = None
       LLMLingua2Operator = None
   ```

______________________________________________________________________

#### Task D2: 创建集成测试 ✅ 已完成

**负责人**: Copilot 4\
**预计时间**: 30 分钟\
**依赖**: D1\
**状态**: ✅ 已完成

**操作清单**:

1. 创建测试文件: `packages/sage-benchmark/tests/benchmark_refiner/test_longllmlingua.py`
   `packages/sage-benchmark/tests/benchmark_refiner/test_llmlingua2.py`

1. 测试内容:

   - 导入测试
   - 基本压缩功能测试 (lazy init 验证)
   - Pipeline 结构验证

______________________________________________________________________

#### Task D3: 更新 benchmark_refiner __init__.py ✅ 已完成

**负责人**: Copilot 4\
**预计时间**: 10 分钟\
**依赖**: B3, C3\
**状态**: ✅ 已完成

**操作清单**:

1. 确保 `RefinerAlgorithm` 枚举包含:

   - `LONGLLMLINGUA = "longllmlingua"`
   - `LLMLINGUA2 = "llmlingua2"`

1. 更新文档字符串

______________________________________________________________________

#### Task D4: 端到端验证 ✅ 已完成

**负责人**: Copilot 4\
**预计时间**: 15 分钟\
**依赖**: D1, D2, D3\
**状态**: ✅ 已完成

**验证命令**:

```bash
# 1. 验证导入
python -c "
from sage.middleware.components.sage_refiner import (
    LongLLMLinguaCompressor,
    LLMLingua2Compressor,
    REFORMCompressor,
    LongRefinerCompressor,
    ProvenceCompressor,
)
print('All imports successful')
"

# 2. 验证枚举
python -c "
from sage.benchmark.benchmark_refiner.experiments import RefinerAlgorithm
print('Available algorithms:', RefinerAlgorithm.available())
assert 'longllmlingua' in RefinerAlgorithm.available()
assert 'llmlingua2' in RefinerAlgorithm.available()
assert 'llmlingua' not in RefinerAlgorithm.available()
assert 'adaptive' not in RefinerAlgorithm.available()
print('Enum verification passed')
"

# 3. 运行测试
pytest packages/sage-benchmark/tests/benchmark_refiner/ -v
```

______________________________________________________________________

## 执行顺序建议

```
时间线:
────────────────────────────────────────────────────────────────────
T0     T15    T30    T45    T60    T75    T90    T105   T120 (分钟)
│      │      │      │      │      │      │      │      │
├──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┤
│  A1  │  A2  │  A3  │  A4  │      │      │      │      │  Copilot 1
├──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┤
│      B1 (LongLLMLingua Compressor)     │  B2  │  B3  │  Copilot 2
├──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┤
│      C1 (LLMLingua2 Compressor)        │  C2  │  C3  │  Copilot 3
├──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┤
│                                        │  D1  │D2│D3│D4│ Copilot 4
────────────────────────────────────────────────────────────────────
```

**并行策略**:

- **Copilot 1**: 负责所有清理任务 (A1 → A2 → A3 → A4)
- **Copilot 2**: 负责 LongLLMLingua 实现 (B1 → B2 → B3)
- **Copilot 3**: 负责 LLMLingua2 实现 (C1 → C2 → C3)
- **Copilot 4**: 负责集成测试 (D1 → D2 → D3 → D4)

______________________________________________________________________

## 注意事项

1. **依赖管理**: 使用 `pip install llmlingua` 安装，已添加到 `sage-middleware/pyproject.toml`
1. **无本地源码依赖**: 不再依赖 LLMLingua-main 文件夹，已删除
1. **论文 Baseline 配置**: `DEFAULT_LONG_LLMLINGUA_CONFIG` 配置符合 Jiang et al. (2024) 论文
1. **设备兼容**: 确保 `device_map` 参数支持 "cuda", "cpu", "cuda:0" 等格式
1. **测试模式**: Pipeline 需支持 `SAGE_TEST_MODE=true` 环境变量

______________________________________________________________________

## 参考文档

- [LLMLingua Paper](https://arxiv.org/abs/2310.05736): LLMLingua 原始论文
- [LongLLMLingua Paper](https://arxiv.org/abs/2310.06839): LongLLMLingua 扩展
- [LLMLingua-2 Paper](https://arxiv.org/abs/2403.12968): LLMLingua-2 Token 分类方法
- [LLMLingua GitHub](https://github.com/microsoft/LLMLingua): 官方仓库
- [LLMLingua PyPI](https://pypi.org/project/llmlingua/): pip 安装包

______________________________________________________________________

## 附录: 核心 API 参考

### LLMLingua PromptCompressor 核心方法

```python
# 来源: pip install llmlingua (无需本地源码)

class PromptCompressor:
    def __init__(
        self,
        model_name: str = "NousResearch/Llama-2-7b-hf",
        device_map: str = "cuda",
        model_config: dict = {},
        open_api_config: dict = {},
        use_llmlingua2: bool = False,      # ⭐ LLMLingua2 开关
        use_slingua: bool = False,          # SecurityLingua
        llmlingua2_config: dict = {},
    ):
        ...

    def compress_prompt(
        self,
        context: List[str],                 # 待压缩的上下文列表
        instruction: str = "",              # 指令
        question: str = "",                 # 问题 (LongLLMLingua 必需)
        rate: float = 0.5,                  # 压缩率 (0-1)
        target_token: float = -1,           # 目标 token 数
        iterative_size: int = 200,          # 迭代压缩大小
        force_context_ids: List[int] = None,# 强制保留的上下文索引
        force_context_number: int = None,   # 强制保留的上下文数量
        use_sentence_level_filter: bool = False,  # 句子级过滤
        use_context_level_filter: bool = True,    # 上下文级过滤
        use_token_level_filter: bool = True,      # Token 级过滤
        keep_split: bool = False,
        keep_first_sentence: int = 0,
        keep_last_sentence: int = 0,
        keep_sentence_number: int = 0,
        high_priority_bonus: int = 100,
        context_budget: str = "+100",
        token_budget_ratio: float = 1.4,
        condition_in_question: str = "none",      # ⭐ "none"/"before"/"after"
        reorder_context: str = "original",        # ⭐ "original"/"sort"/"two_stage"
        dynamic_context_compression_ratio: float = 0.0,  # ⭐ 动态压缩比
        condition_compare: bool = False,
        add_instruction: bool = False,
        rank_method: str = "llmlingua",           # ⭐ "llmlingua"/"longllmlingua"/...
        concate_question: bool = True,
        ...
    ) -> dict:
        """
        返回:
        {
            "compressed_prompt": str,      # 压缩后的 prompt
            "origin_tokens": int,          # 原始 token 数
            "compressed_tokens": int,      # 压缩后 token 数
            "ratio": str,                  # 压缩比 (如 "2.5x")
            "rate": str,                   # 压缩率 (如 "40.0%")
            "saving": str,                 # 估算节省 (GPT-4)
        }
        """
```

### LongLLMLingua 推荐配置

```python
# LongLLMLingua 核心特性:
# 1. question-aware ranking (rank_method="longllmlingua")
# 2. condition_in_question="after" (在 question 之后评估 PPL)
# 3. reorder_context="sort" (按相关性重排序)
# 4. dynamic_context_compression_ratio > 0 (动态压缩比)

result = compressor.compress_prompt(
    context=documents,
    question=query,
    rank_method="longllmlingua",           # 关键
    condition_in_question="after",         # 关键
    reorder_context="sort",                # 可选
    dynamic_context_compression_ratio=0.3, # 可选
    use_context_level_filter=True,
    use_token_level_filter=True,
    rate=0.5,
)
```

### LLMLingua2 推荐配置

```python
# LLMLingua2 核心特性:
# 1. use_llmlingua2=True (BERT-based token 分类)
# 2. 快速: 不需要 LLM 推理
# 3. 支持多语言
# 4. 可配合 context-level filter 使用

compressor = PromptCompressor(
    model_name="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
    use_llmlingua2=True,  # 关键
    device_map="cuda",
)

result = compressor.compress_prompt(
    context=documents,
    rate=0.5,
    use_context_level_filter=True,
    use_token_level_filter=True,
    force_tokens=["\n", ".", "?"],
    drop_consecutive=False,
)
```

### 支持的 Rank Methods

| rank_method     | 描述               | 适用场景   |
| --------------- | ------------------ | ---------- |
| `llmlingua`     | LLM perplexity     | 通用       |
| `longllmlingua` | Question-aware PPL | 长文档 QA  |
| `bm25`          | BM25               | 关键词匹配 |
| `bge`           | BGE embedding      | 语义相似   |
| `bge_reranker`  | BGE reranker       | 精确排序   |
| `sentbert`      | Sentence-BERT      | 语义相似   |
| `gzip`          | Gzip 压缩距离      | 轻量级     |

______________________________________________________________________

## 快速验证脚本

```python
#!/usr/bin/env python
"""验证 LongLLMLingua 和 LLMLingua2 导入"""

def test_imports():
    """验证所有导入"""
    errors = []

    # 1. 验证 pip llmlingua 包可导入
    try:
        from llmlingua import PromptCompressor
        print("✅ llmlingua pip package import OK")
    except Exception as e:
        errors.append(f"llmlingua package: {e}")

    # 2. 验证 LongLLMLingua Compressor
    try:
        from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.longllmlingua import LongLLMLinguaCompressor
        print("✅ LongLLMLinguaCompressor import OK")
    except Exception as e:
        errors.append(f"LongLLMLinguaCompressor: {e}")

    # 3. 验证 LLMLingua2 Compressor
    try:
        from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.llmlingua2 import LLMLingua2Compressor
        print("✅ LLMLingua2Compressor import OK")
    except Exception as e:
        errors.append(f"LLMLingua2Compressor: {e}")

    # 4. 验证主导出
    try:
        from sage.middleware.components.sage_refiner import (
            LongLLMLinguaCompressor,
            LLMLingua2Compressor,
        )
        print("✅ Main exports OK")
    except Exception as e:
        errors.append(f"Main exports: {e}")

    # 5. 验证枚举
    try:
        from sage.benchmark.benchmark_refiner.experiments import RefinerAlgorithm
        available = RefinerAlgorithm.available()
        assert 'longllmlingua' in available, "longllmlingua not in available"
        assert 'llmlingua2' in available, "llmlingua2 not in available"
        print(f"✅ RefinerAlgorithm OK: {available}")
    except Exception as e:
        errors.append(f"RefinerAlgorithm: {e}")

    if errors:
        print("\n❌ Errors found:")
        for e in errors:
            print(f"  - {e}")
        return False

    print("\n✅ All imports verified successfully")
    return True

if __name__ == "__main__":
    test_imports()
```
