# 配置文件 (Configuration Files)

本目录包含SAGE框架示例的所有配置文件，这些配置文件定义了各种示例应用的运行参数。

## 📁 配置文件分类

### 🔧 基础配置
- `config.yaml` - 默认基础配置，适用于大多数RAG应用
- `config_batch.yaml` - 批量处理配置

### 🧠 RAG专用配置
#### 检索配置
- `config_bm25s.yaml` - BM25稀疏检索配置
- `config_mixed.yaml` - 混合检索策略配置
- `config_enhanced.yaml` - 增强检索配置

#### 生成配置
- `config_hf.yaml` - HuggingFace模型生成配置
- `config_openai.yaml` - OpenAI生成配置

#### 高级RAG功能
- `config_refiner.yaml` - 答案精炼配置
- `config_rerank.yaml` - 检索结果重排配置
- `config_multiplex.yaml` - 多路复用配置

### 🤖 智能体配置
- `multiagent_config.yaml` - 多智能体系统配置

### 🌊 流处理配置
- `config_for_qa.yaml` - 问答流处理配置
- `config_for_ingest.yaml` - 数据摄取流配置

### 📊 评估配置
- `config_evaluate.yaml` - 系统评估配置

### 🚀 分布式配置
- `config_ray.yaml` - Ray分布式处理配置

### 🔬 实验配置
- `config_adaptive.yaml` - 自适应配置
- `new_adaptive.yaml` - 新自适应配置

## 🎯 配置文件使用

### 基本用法
```python
from sage.utils.config_loader import load_config

# 加载配置文件
config = load_config("../config/config.yaml")

# 在管道中使用配置
env.from_source(FileSource, config["source"])
   .map(DenseRetriever, config["retriever"])
   .map(QAPromptor, config["promptor"])
```

### 配置文件结构
```yaml
# 数据源配置
source:
  data_path: "../data/sample/question.txt"
  batch_size: 10

# 检索器配置
retriever:
  collection_name: "knowledge_base"
  top_k: 5
  similarity_threshold: 0.7

# 生成器配置
generator:
  model: "gpt-3.5-turbo"
  temperature: 0.7
  max_tokens: 500
```

## 📂 数据路径说明

所有配置文件中的数据路径都已调整为相对于示例脚本的路径：
- 原来: `"data/sample/question.txt"`
- 现在: `"../data/sample/question.txt"`

这样确保从任何示例目录（如`rag/`, `agents/`等）运行脚本时都能正确找到数据文件。

## 🔧 自定义配置

### 复制并修改
```bash
# 复制基础配置
cp config.yaml my_config.yaml

# 修改参数
vim my_config.yaml

# 在代码中使用
config = load_config("../config/my_config.yaml")
```

### 环境变量支持
配置文件支持环境变量：
```yaml
generator:
  api_key: "${OPENAI_API_KEY}"
  base_url: "${OPENAI_BASE_URL:-https://api.openai.com/v1}"
```

## 🔗 相关资源

- [示例数据说明](../data/README.md)
- [SAGE配置系统文档](../../docs/configuration.md)
- [示例运行指南](../README.md)
