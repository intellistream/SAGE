# Self-RAG 实现位置问题分析

## 问题发现

在重构 `sage-benchmark` 时，发现 **Self-RAG 的实现混在了 `evaluation/pipeline_experiment.py` 中**，而不是作为独立的 pipeline 放在 `implementations/pipelines/` 中。

## 当前情况

### `evaluation/pipeline_experiment.py` 包含：

1. **BatchFileSource** - 批量数据加载
2. **Generator** - Self-RAG 的生成逻辑（使用预检索文档）
3. **PostProcessor** - 后处理
4. **Sink** - 结果保存

**问题**：这个文件既是 **Self-RAG 的实现**，又是 **benchmark 框架**，职责混淆。

## 应该如何组织

### 方案 A：完全分离（推荐）

```
implementations/pipelines/
└── selfrag.py                  # Self-RAG pipeline 实现
    ├── SelfRAGRetriever       # 从数据提取预检索文档
    ├── SelfRAGPromptor        # 构建 Self-RAG 格式 prompt
    └── SelfRAGGenerator       # 生成答案

evaluation/
└── benchmark_runner.py         # 通用 benchmark 运行器
    ├── BatchFileSource        # 批量数据加载
    ├── BenchmarkRunner        # 运行任意 pipeline 并收集结果
    └── ResultsSaver           # 保存结果
```

### 方案 B：保持现状但重命名（不推荐）

将 `pipeline_experiment.py` 重命名为 `selfrag_benchmark.py`，承认它就是 Self-RAG 的 benchmark 实现。

但这样：
- ❌ 不一致：其他 pipelines 在 implementations/，只有 Self-RAG 在 evaluation/
- ❌ 难扩展：每个新 pipeline 都要复制一遍批量处理逻辑

## 推荐的重构步骤

### 1. 提取 Self-RAG Pipeline

创建 `implementations/pipelines/selfrag.py`：
```python
class SelfRAGRetriever(MapFunction):
    """从 Self-RAG 数据集提取预检索文档"""
    
class SelfRAGPromptor(MapFunction):
    """构建 Self-RAG 格式的 prompt"""
    
class SelfRAGGenerator(MapFunction):
    """使用 vLLM 生成答案"""
```

### 2. 创建通用 Benchmark Runner

重构 `evaluation/pipeline_experiment.py` → `evaluation/benchmark_runner.py`：
```python
class BenchmarkRunner:
    """
    通用 benchmark 运行器
    
    可以运行任何 RAG pipeline 实现并收集评测数据
    """
    
    def run_pipeline(self, pipeline_module, config):
        """运行指定的 pipeline 并收集结果"""
        # 批量处理
        # 调用 pipeline
        # 收集结果
        # 保存到文件
```

### 3. 使用方式

```bash
# 运行 Self-RAG benchmark
python -m sage.benchmark.benchmark_rag.evaluation.benchmark_runner \
    --pipeline selfrag \
    --config config_selfrag_benchmark.yaml

# 运行其他 pipeline benchmark
python -m sage.benchmark.benchmark_rag.evaluation.benchmark_runner \
    --pipeline qa_dense_retrieval_milvus \
    --config config_dense_benchmark.yaml
```

## 当前已完成

✅ 创建了 `implementations/pipelines/selfrag.py` - 独立的 Self-RAG pipeline 实现
✅ 创建了 `config/config_selfrag.yaml` - Self-RAG 配置

## 待完成

⏳ 重构 `evaluation/pipeline_experiment.py` 为通用 benchmark runner
⏳ 更新文档说明 Self-RAG 的使用方式
⏳ 添加其他 pipelines 的 benchmark 支持

## 优势

**分离后的优势**：

1. **职责清晰**：
   - `implementations/pipelines/selfrag.py` - 实现 Self-RAG
   - `evaluation/benchmark_runner.py` - 运行 benchmark

2. **易于扩展**：
   - 新增 pipeline 只需在 `implementations/pipelines/` 添加
   - Benchmark runner 通用，支持所有 pipelines

3. **符合结构**：
   - 与其他 12 个 pipelines 放在同一目录
   - 统一的使用方式

4. **便于对比**：
   - Self-RAG vs Dense Retrieval vs Sparse Retrieval
   - 所有实现都可以用同一个 benchmark runner 测试
