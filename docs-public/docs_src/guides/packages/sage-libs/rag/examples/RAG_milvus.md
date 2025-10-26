
# RAG系统完整实现示例 (Complete RAG System Implementation)

本文档提供使用SAGE基于milvus的RAG问答系统的完整实现示例。如果对RAG相关知识以及SAGE pipeline相关知识不了解，建议先阅读[使用SAGE基于chroma构建RAG](RAG.md)。

## 使用Milvus向量库进行向量检索
SAGE提供了基于Milvus向量库的稠密向量检索和稀疏向量检索算子，可以先执行离线向量知识库构建，创建知识库，然后执行RAG流水线，调用创建的知识库，对其中的知识进行查询。

### 基于Milvus向量库的稠密向量检索
#### 离线稠密向量知识库构建
基于Milvus的稠密向量数据库构建示例如下：
```python
import os
import sys
from sage.libs.rag.chunk import CharacterSplitter
from sage.libs.rag.document_loaders import TextLoader
from sage.libs.rag.retriever import MilvusDenseRetriever
import yaml
from sage.common.utils.config.loader import load_config

def load_config(path):
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def load_knowledge_to_milvus(config):
    """
    加载知识库到 Milvus
    """
    knowledge_file = config.get('preload_knowledge_file')
    persistence_path = config.get('milvus_dense').get('persistence_path')
    collection_name = config.get('milvus_dense').get('collection_name')

    print(f"=== 预加载知识库到 ChromaDB ===")
    print(f"文件: {knowledge_file} | DB: {persistence_path} | 集合: {collection_name}")

    loader = TextLoader(knowledge_file)
    document = loader.load()
    print(f"已加载文本，长度: {len(document['content'])}")

    splitter = CharacterSplitter({"separator": "\n\n"})
    chunks = splitter.execute(document)
    print(f"分块数: {len(chunks)}")
    
    print("初始化Milvus...")
    milvus_backend = MilvusDenseRetriever(config)
    milvus_backend.add_documents(chunks)
    print(f"✓ 已添加 {len(chunks)} 个文本块")
    print(f"✓ 数据库信息: {milvus_backend.get_collection_info()}")
    text_query = "什么是RAG？"
    results = milvus_backend.execute(text_query)
    print(f"检索结果: {results}")
    return True

if __name__ == "__main__":
    config_path = 'config_dense_milvus.yaml'
    if not os.path.exists(config_path):
        print(f"配置文件不存在: {config_path}")
    
    config = load_config(config_path)
    result = load_knowledge_to_milvus(config["retriever"])
    if result:
        print("知识库已成功加载，可运行检索/问答脚本")
    else:
        print("知识库加载失败")
        sys.exit(1)

```

config_dense_milvus.yaml配置文件如下：
```yaml
retriever:
  preload_knowledge_file: "知识库文件路径（.txt）"

  # 通用参数
  dimension: 384            # 向量维度，应与 embedding 模型一致
  top_k: 2                 # 返回文档数量

  # 嵌入模型配置（用于对文档和查询编码）
  embedding:
    method: "hf"
    model: "sentence-transformers/all-MiniLM-L6-v2"

  # Milvus 后端（稠密检索）
  milvus_dense:
    # 本地 Milvus Lite（推荐用于快速试用）
    persistence_path: "./milvus_qa_dense.db"

    # 远程 Milvus（如需远程，请注释上面的 persistence_path，改为如下配置）
    # host: "127.0.0.1"
    # port: 19530
    # force_http: true

    collection_name: "qa_dense_collection"
    dim: 384
    metric_type: "COSINE"   # 只允许: IP / COSINE / L2
    search_type: "dense"     # 稠密检索

    # 可选项
    dense_insert_batch_size: 128
    # 知识文件（可选）：提供后将自动按段落读取并入库
    # knowledge_file: "./examples/data/qa_knowledge_base.txt"
```

#### 基于Milvus的稠密向量检索RAG流水线
```python
import os
from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io.batch import JSONLBatch
from sage.libs.io.sink import TerminalSink
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.retriever import MilvusDenseRetriever
from sage.common.utils.config.loader import load_config
import yaml


def load_config(path):
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def pipeline_run():
    """    
    创建并运行 Milvus 专用 RAG 数据处理管道

    Args:
        config (dict): 包含各模块配置的配置字典。
    """

    print("=== 启动基于 Milvus 的 RAG 问答系统 ===")
    print("配置信息:")
    print(f"  - 源文件: {config['source']['data_path']}")
    print(f"  - 检索器: MilvusDenseRetriever (Milvus 专用)")
    print(f"  - 向量维度: {config['retriever']['dimension']}")
    print(f"  - Top-K: {config['retriever']['top_k']}")
    print(f"  - 集合名称: {config['retriever']['milvus_dense']['collection_name']}")
    print(f"  - 嵌入模型: {config['retriever']['embedding']['method']}")

    env = LocalEnvironment()
    # 构建数据处理流程
    # MilvusDenseRetriever 会在初始化时自动加载配置的知识库文件
    print("正在构建数据处理管道...")
    # 构建数据处理流程
    (env
        .from_source(JSONLBatch, config["source"])
        .map(MilvusDenseRetriever, config["retriever"])
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"]["vllm"])
        .sink(TerminalSink, config["sink"])
    )
    print("正在提交并运行管道...")
    env.submit(autostop=True)
    env.close()
    print("=== RAG 问答系统运行完成 ===")


if __name__ == '__main__':
    config_path = './examples/config/config_dense_milvus.yaml'
    if not os.path.exists(config_path):
        print(f"配置文件不存在: {config_path}")
    
    config = load_config(config_path)

    print(config)

    # 检查知识库文件（如果配置了）
    knowledge_file = config["retriever"]["milvus_dense"].get("knowledge_file")
    if knowledge_file:
        if not os.path.exists(knowledge_file):
            print(f"警告：知识库文件不存在: {knowledge_file}")
            print("请确保知识库文件存在于指定路径")
        else:
            print(f"找到知识库文件: {knowledge_file}")
    
    print("开始运行 Milvus 稠密向量检索管道...")
    pipeline_run() 
```
配置文件如下：
```yaml
source:
  data_path: "./queries.jsonl"   # 用户提供的流式问题，格式见首段描述
  platform: "local"

retriever:
  preload_knowledge_file: "知识库文件路径（.txt）"
  # 通用参数
  dimension: 384            # 向量维度，应与 embedding 模型一致
  top_k: 2                 # 返回文档数量

  # 嵌入模型配置（用于对文档和查询编码）
  embedding:
    method: "hf"
    model: "sentence-transformers/all-MiniLM-L6-v2"

  # Milvus 后端（稠密检索）
  milvus_dense:
    # 本地 Milvus Lite（推荐用于快速试用）
    persistence_path: "./milvus_qa_dense.db"

    # 远程 Milvus（如需远程，请注释上面的 persistence_path，改为如下配置）
    # host: "127.0.0.1"
    # port: 19530
    # force_http: true

    collection_name: "qa_dense_collection"
    dim: 384
    metric_type: "COSINE"   # 只允许: IP / COSINE / L2
    search_type: "dense"     # 稠密检索

    # 稠密向量导入数据库的批次数
    dense_insert_batch_size: 128
    # 知识文件（可选）：提供后将自动按段落读取并入库
    # knowledge_file: "./examples/data/qa_knowledge_base.txt"

promptor:
  template: |
    基于以下检索到的相关文档，回答用户问题：

    相关文档：
    {retrieved_documents}

    用户问题：{query}

    请提供准确、有用的回答：

generator:
  vllm:
    api_key: "your-own-api_key"
    method: "openai"
    model_name: "meta-llama/Llama-2-7b-chat-hf"
    base_url: "base_url"
    seed: 42

sink:
  enable_log: true
```
#### 离线稀疏向量知识库构建
基于Milvus的稀疏向量数据库构建示例如下：

```python
import os
import sys
from sage.libs.rag.chunk import CharacterSplitter
from sage.libs.rag.document_loaders import TextLoader
from sage.libs.rag.retriever import MilvusSparseRetriever
import yaml
from sage.common.utils.config.loader import load_config

def load_config(path):
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def load_knowledge_to_milvus(config):
    """
    加载知识库到 Milvus
    """
    knowledge_file = config.get('preload_knowledge_file')
    persistence_path = config.get('milvus_sparse').get('persistence_path')
    collection_name = config.get('milvus_sparse').get('collection_name')

    print(f"=== 预加载知识库到 Milvus ===")
    print(f"文件: {knowledge_file} | DB: {persistence_path} | 集合: {collection_name}")

    loader = TextLoader(knowledge_file)
    document = loader.load()
    print(f"已加载文本，长度: {len(document['content'])}")

    splitter = CharacterSplitter({"separator": "\n\n"})
    chunks = splitter.execute(document)
    print(f"分块数: {len(chunks)}")
    
    print("初始化Milvus...")
    milvus_backend = MilvusSparseRetriever(config)
    milvus_backend.add_documents(chunks)
    print(f"✓ 已添加 {len(chunks)} 个文本块")
    print(f"✓ 数据库信息: {milvus_backend.get_collection_info()}")
    text_query = "什么是RAG？"
    results = milvus_backend.execute(text_query)
    print(f"检索结果: {results}")
    return True

if __name__ == "__main__":
    config_path = 'config_sparse_milvus.yaml'
    if not os.path.exists(config_path):
        print(f"配置文件不存在: {config_path}")
    
    config = load_config(config_path)
    result = load_knowledge_to_milvus(config["retriever"])
    if result:
        print("知识库已成功加载，可运行检索/问答脚本")
    else:
        print("知识库加载失败")
        sys.exit(1)
```

config_sparse_milvus.yaml配置文件如下：
```yaml
retriever:
  preload_knowledge_file: "./examples/data/qa_knowledge_base.txt"

  # 通用参数
  top_k: 3                 # 返回文档数量

  # Milvus 后端（稠密检索）
  milvus_sparse:
    # 本地 Milvus Lite（推荐用于快速试用）
    persistence_path: "./milvus_qa_sparse.db"

    # 远程 Milvus（如需远程，请注释上面的 persistence_path，改为如下配置）
    # host: "127.0.0.1"
    # port: 19530
    # force_http: true

    collection_name: "qa_sparse_collection"
    search_type: "sparse"     # 稀疏检索
```

#### 基于Milvus的稀疏向量检索RAG流水线
```python
import os
import time
from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io.batch import JSONLBatch
from sage.libs.io.sink import TerminalSink
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.retriever import MilvusSparseRetriever
from sage.common.utils.config.loader import load_config
import yaml


def load_config(path):
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def pipeline_run():
    """    
    创建并运行 Milvus 专用 RAG 数据处理管道

    Args:
        config (dict): 包含各模块配置的配置字典。
    """

    print("=== 启动基于 Milvus 的 RAG 问答系统 ===")
    print("配置信息:")
    print(f"  - 源文件: {config['source']['data_path']}")
    print(f"  - 检索器: MilvusSparseRetriever (Milvus 专用)")
    print(f"  - Top-K: {config['retriever']['top_k']}")
    print(f"  - 集合名称: {config['retriever']['milvus_sparse']['collection_name']}")

    env = LocalEnvironment()
    # 构建数据处理流程
    # MilvusSparseRetriever 会在初始化时自动加载配置的知识库文件
    print("正在构建数据处理管道...")
    # 构建数据处理流程
    (env
        .from_source(JSONLBatch, config["source"])
        .map(MilvusSparseRetriever, config["retriever"])
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"]["vllm"])
        .sink(TerminalSink, config["sink"])
    )
    print("正在提交并运行管道...")
    env.submit(autostop=True)
    env.close()
    print("=== RAG 问答系统运行完成 ===")


if __name__ == '__main__':
    config_path = './config_sparse_milvus.yaml'
    if not os.path.exists(config_path):
        print(f"配置文件不存在: {config_path}")
    
    config = load_config(config_path)

    print(config)

    # 检查知识库文件（如果配置了）
    knowledge_file = config["retriever"]["milvus_sparse"].get("knowledge_file")
    if knowledge_file:
        if not os.path.exists(knowledge_file):
            print(f"警告：知识库文件不存在: {knowledge_file}")
            print("请确保知识库文件存在于指定路径")
        else:
            print(f"找到知识库文件: {knowledge_file}")
    
    print("开始运行 Milvus 稠密向量检索管道...")
    pipeline_run() 
```
config_sparse_milvus.yaml配置文件如下：
```yaml
source:
  data_path: "./queries.jsonl"   # 用户提供的流式问题，格式见首段描述
  platform: "local"

retriever:
  preload_knowledge_file: "./知识库文件.txt"

  # 通用参数
  top_k: 3                 # 返回文档数量

  # Milvus 后端（稠密检索）
  milvus_sparse:
    # 本地 Milvus Lite（推荐用于快速试用）
    persistence_path: "./milvus_qa_sparse.db"

    # 远程 Milvus（如需远程，请注释上面的 persistence_path，改为如下配置）
    # host: "127.0.0.1"
    # port: 19530
    # force_http: true

    collection_name: "qa_sparse_collection"
    search_type: "sparse"     # 稀疏检索

    # # 知识文件（可选）：提供后将自动按段落读取并入库
    # knowledge_file: "./examples/data/qa_knowledge_base.txt"

promptor:
  template: |
    基于以下检索到的相关文档，回答用户问题：

    相关文档：
    {retrieved_documents}

    用户问题：{query}

    请提供准确、有用的回答：

generator:
  vllm:
    api_key: "your-own-api_key"
    method: "openai"
    model_name: "meta-llama/Llama-2-7b-chat-hf"
    base_url: "base_url"
    seed: 42

sink:
  enable_log: true

```

---

## 组件组合使用

### 完整流水线示例

```python
def full_pipeline_run(config: dict) -> None:
    """包含所有组件的完整RAG流水线"""
    env = LocalEnvironment()
    (
        env
        .from_batch(JSONLBatch, config["source"])
        .map(ChromaRetriever, config["retriever"])        # 检索
        .map(BGEReranker, config["reranker"])             # 重排序  
        .map(LongRefinerAdapter, config["refiner"])       # 文档优化
        .map(QAPromptor, config["promptor"])              # 提示组装
        .map(OpenAIGenerator, config["generator"]["vllm"]) # 答案生成
        .sink(TerminalSink, config["sink"])               # 结果输出
    )
    env.submit()
    time.sleep(10)
    env.close()
```

