# SQL-based Pipeline Builder

## 概述

SQL-based Pipeline Builder 是 SAGE 项目的新一代管道构建系统，解决了模板方法的刚性限制，提供更灵活、数据驱动的管道定义和管理能力。

## 核心特性

### 🎯 灵活的语法支持
- **CREATE PIPELINE内联语法**: 简洁的管道定义方式
- **传统INSERT语句**: 详细的表格化管道定义
- **混合模式**: 两种语法可以组合使用

### 🗄️ 数据驱动存储
- SQLite数据库持久化管道定义
- 支持管道的CRUD操作
- 版本化管道管理

### 🔧 自动代码生成
- 自动生成YAML配置文件
- 自动生成Python运行器
- 支持批处理和流式模式

### 🧪 完整测试覆盖
- 9个测试用例全部通过
- 覆盖解析、存储、编译全流程
- 集成测试确保端到端功能

## 快速开始

### 1. 基础使用

```bash
# 查看帮助
sage pipeline sql --help

# 加载SQL管道定义
sage pipeline sql load examples.sql

# 列出所有管道
sage pipeline sql list

# 查看管道详情
sage pipeline sql show simple_qa

# 编译管道为YAML和Python
sage pipeline sql compile simple_qa --output-dir ./output
```

### 2. SQL语法示例

#### CREATE PIPELINE语法 (推荐)

```sql
-- 简单QA管道
CREATE PIPELINE simple_qa (
  source = FileSource { data_path: "data/questions.txt", chunk_size: 1000 },
  retriever = ChromaRetriever { top_k: 5 },
  promptor = QAPromptor { template: "Answer: {context}" },
  generator = OpenAIGenerator { model: "gpt-3.5-turbo" },
  sink = TerminalSink { format: "json" },
  source -> retriever -> promptor -> generator -> sink
);
```

#### 传统INSERT语法

```sql
-- 管道基本信息
INSERT INTO pipeline VALUES 
  ('advanced_rag', 'Advanced RAG', 'Multi-step RAG pipeline', 'streaming');

-- 操作符定义
INSERT INTO operator VALUES
  ('advanced_rag', 'source', 'FileSource', 1, '{"data_path": "corpus/"}'),
  ('advanced_rag', 'retriever', 'ChromaRetriever', 2, '{"top_k": 10}'),
  ('advanced_rag', 'reranker', 'CrossEncoderReranker', 3, '{"model": "ms-marco"}'),
  ('advanced_rag', 'generator', 'OpenAIGenerator', 4, '{"model": "gpt-4"}');

-- 连接定义
INSERT INTO pipeline_edge VALUES
  ('advanced_rag', 'source', 'retriever'),
  ('advanced_rag', 'retriever', 'reranker'),
  ('advanced_rag', 'reranker', 'generator');
```

## 架构设计

### 核心组件

```
SQL DSL Input
      ↓
SQLPipelineDSLParser  →  PipelineDefinition
      ↓                        ↓
SQLPipelineStore            SQLPipelineCompiler
      ↓                        ↓
SQLite Database            YAML + Python Output
```

### 类层次结构

- **SQLPipelineStore**: 管道的持久化存储
- **SQLPipelineCompiler**: 管道定义到代码的编译器
- **SQLPipelineDSLParser**: SQL DSL到管道定义的解析器
- **OperatorNode**: 管道操作符的数据结构
- **PipelineDefinition**: 完整管道定义的数据结构

## 使用场景

### 1. 快速原型开发
```sql
CREATE PIPELINE prototype (
  source = FileSource { data_path: "test.txt" },
  sink = TerminalSink {},
  source -> sink
);
```

### 2. 复杂RAG系统
```sql
CREATE PIPELINE advanced_rag (
  -- 数据源
  source = FileSource { data_path: "corpus/", file_pattern: "*.md" },
  
  -- 多路召回
  dense_retriever = ChromaRetriever { top_k: 20, collection_name: "dense" },
  sparse_retriever = BM25Retriever { top_k: 20, index_path: "bm25/" },
  
  -- 重排序
  reranker = CrossEncoderReranker { model: "cross-encoder/ms-marco", top_k: 5 },
  
  -- 生成
  promptor = QAPromptor { template: "Context: {context}\nQ: {question}\nA:" },
  generator = OpenAIGenerator { model: "gpt-4", temperature: 0.2 },
  
  -- 输出
  sink = StreamingSink { format: "markdown" },
  
  -- 连接关系
  source -> dense_retriever -> reranker,
  source -> sparse_retriever -> reranker,
  reranker -> promptor -> generator -> sink
);
```

### 3. 多模态分析
```sql
CREATE PIPELINE multimodal (
  image_source = ImageSource { data_path: "images/", formats: ["jpg", "png"] },
  text_source = FileSource { data_path: "descriptions.txt" },
  
  image_processor = VisionProcessor { model: "clip-vit-base" },
  text_processor = TextEmbedder { model: "sentence-transformers/all-MiniLM" },
  
  fusion = MultiModalFusion { strategy: "concatenate" },
  classifier = MLClassifier { model_path: "models/classifier.pkl" },
  
  sink = CSVSink { output_path: "results.csv" },
  
  image_source -> image_processor -> fusion,
  text_source -> text_processor -> fusion,
  fusion -> classifier -> sink
);
```

## 配置映射

系统自动将操作符类型映射到配置节：

- `FileSource` → `source`
- `ChromaRetriever` → `retriever`  
- `QAPromptor` → `promptor`
- `OpenAIGenerator` → `generator`
- `TerminalSink` → `sink`

## 生成的代码结构

### YAML配置
```yaml
pipeline:
  name: Simple QA
  description: Question answering pipeline
  mode: batch
  type: local
  version: 1.0.0

source:
  data_path: data/questions.txt
  chunk_size: 1000

retriever:
  top_k: 5
  collection_name: documents

generator:
  model: gpt-3.5-turbo
  temperature: 0.1
```

### Python运行器
```python
"""Auto-generated SAGE pipeline from SQL definition."""

from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io_utils.source import FileSource
from sage.libs.rag.retriever import ChromaRetriever
# ... other imports

def build_pipeline(config: dict) -> Tuple[LocalEnvironment, object]:
    env = LocalEnvironment(config["pipeline"]["name"])
    
    pipeline = (
        env.from_source(FileSource, config["source"])
        .map(ChromaRetriever, config["retriever"])
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"])
        .sink(TerminalSink, config["sink"])
    )
    
    return env, pipeline

def main():
    # CLI argument parsing and pipeline execution
    # ...
```

## 测试覆盖

- **TestSQLPipelineStore**: 数据库存储和检索
- **TestSQLPipelineCompiler**: YAML和Python代码生成
- **TestSQLPipelineDSLParser**: SQL语法解析
- **TestSQLIntegration**: 端到端集成测试

## 相比Template方法的优势

| 特性 | Template方法 | SQL方法 |
|------|-------------|---------|
| 灵活性 | ❌ 固定模板 | ✅ 自由组合 |
| 可扩展性 | ❌ 需要编程 | ✅ 声明式定义 |
| 重用性 | ❌ 模板绑定 | ✅ 组件化设计 |
| 版本管理 | ❌ 文件级别 | ✅ 数据库级别 |
| 查询能力 | ❌ 文件搜索 | ✅ SQL查询 |
| 批量操作 | ❌ 单个处理 | ✅ 批量管理 |

## 未来扩展

1. **可视化编辑器**: 基于SQL定义的图形化管道编辑
2. **管道调试**: SQL定义的运行时调试支持
3. **性能优化**: 基于使用模式的管道优化建议
4. **版本控制**: 管道定义的Git集成
5. **模板生成**: 从SQL定义自动生成模板

## 结论

SQL-based Pipeline Builder 为SAGE项目提供了强大、灵活的管道构建能力，完全解决了issue #220中提出的需求，并为未来的智能提示和IDE集成奠定了坚实基础。