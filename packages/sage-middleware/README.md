# SAGE Middleware - 中间件组件

SAGE Middleware提供中间件服务，包含LLM中间件、API服务、任务队列等企业级功能。

## 主要功能

### LLM中间件服务
- **多模型支持**: OpenAI、Ollama、智谱AI、Cohere等
- **统一API**: 标准化的LLM调用接口
- **高性能推理**: 基于vLLM的优化推理服务
- **模型管理**: 动态模型加载和卸载

### API服务
- **RESTful API**: 基于FastAPI的高性能API服务
- **认证授权**: JWT令牌和密码加密支持
- **服务发现**: 自动服务注册和发现

### 任务队列
- **异步处理**: 基于Celery的分布式任务队列
- **监控界面**: Flower监控和管理界面
- **容错机制**: 任务重试和错误处理

### 向量检索
- **FAISS集成**: 高性能向量相似度搜索
- **BM25搜索**: 传统文本检索算法
- **混合检索**: 向量和关键词混合检索

## 安装

```bash
pip install sage-middleware
```

## 基本使用

### 启动LLM服务

```python
from sage.middleware.llm import LLMService

# 创建LLM服务
service = LLMService()

# 注册模型
service.register_model("gpt-3.5-turbo", provider="openai")
service.register_model("llama2", provider="ollama")

# 启动服务
service.start()
```

### API调用

```python
import requests

# 文本生成
response = requests.post("http://localhost:8000/generate", json={
    "model": "gpt-3.5-turbo",
    "prompt": "Hello, how are you?",
    "max_tokens": 100
})

result = response.json()
print(result["text"])
```

### 向量检索

```python
from sage.middleware.retrieval import VectorStore

# 创建向量存储
store = VectorStore()

# 添加文档
store.add_documents([
    "This is document 1",
    "This is document 2"
])

# 搜索
results = store.search("document", top_k=5)
for result in results:
    print(f"Score: {result.score}, Text: {result.text}")
```

## 配置

中间件服务可以通过环境变量或配置文件进行配置：

```yaml
# config.yaml
llm:
  providers:
    openai:
      api_key: "your-api-key"
    ollama:
      base_url: "http://localhost:11434"

api:
  host: "0.0.0.0"
  port: 8000
  
queue:
  broker: "redis://localhost:6379"
  backend: "redis://localhost:6379"
```

## 许可证

MIT License
