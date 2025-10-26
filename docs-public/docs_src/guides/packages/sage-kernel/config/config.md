# SAGE 配置文档

本文档详细说明了 SAGE 项目中各种配置文件的结构和配置项的作用。

## 配置文件概览

SAGE 项目目前包含以下主要配置文件：

- `config.yaml` - 基础配置文件
- `config_adaptive.yaml` - 自适应配置
- `config_bm25s.yaml` - BM25搜索配置
- `config_for_ingest.yaml` - 数据摄取配置
- `config_for_qa.yaml` - 问答系统配置
- `config_ray.yaml` - Ray分布式计算配置
- `config_hf.yaml` - HuggingFace模型配置
- `config_mixed.yaml` - 混合模式配置
- `config_evaluate.yaml` - 评估配置
- `multiagent_config.yaml` - 多智能体配置
- 其他专用配置文件

## 配置项

### 1. Pipeline 配置

```yaml
pipeline:
  name: "sage-api-operator-operator_test"    # 管道名称
  description: "Test pipeline for Sage API Operator"  # 管道描述
  version: "1.0.0"                          # 版本号
  type: "local"                             # 运行类型：local/remote
```

**配置说明：**

- `name`: 定义管道的唯一标识名称
- `description`: 管道功能的文字描述
- `version`: 配置版本号，用于版本管理
- `type`: 指定运行模式，可选 `local`（本地）或 `remote`（远程）

### 2. Source 配置

```yaml
source:
  data_path: "data/sample/question.txt"     # 数据文件路径
  platform: "local"                        # 平台类型
```

**配置说明：**

- `data_path`: 指定输入数据文件的路径
- `platform`: 数据源平台，通常为 `local`

### 3. Retriever 配置

```yaml
retriever:
  platform: "local"                        # 检索平台
  ltm:                                      # 长期记忆配置
    topk: 3                                 # 检索返回的top-k结果数
  kv_collection:                            # 键值集合配置（可选）
    bm25s: True                             # 启用BM25搜索
    topk: 3                                 # BM25检索的top-k数量
```

**配置说明：**

- `platform`: 检索器运行平台，可选 `local` 或 `remote`
- `ltm.topk`: 长期记忆检索返回的结果数量
- `kv_collection.bm25s`: 是否启用BM25搜索算法
- `kv_collection.topk`: BM25搜索返回的结果数量

### 4. Reranker 配置

```yaml
reranker:
  platform: "local"                        # 重排序平台
  model_name: "BAAI/bge-reranker-v2-m3"    # 重排序模型名称
  top_k: 3                                  # 重排序后保留的结果数
```

**配置说明：**

- `platform`: 重排序器运行平台
- `model_name`: 使用的重排序模型，通常为BGE系列模型
- `top_k`: 重排序后保留的文档数量

### 5. Refiner 配置

```yaml
refiner:
  platform: "local"                        # 精炼器平台
  method: "openai"                          # API方法类型
  model_name: "qwen-turbo-0919"            # 模型名称
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"  # API基础URL
  api_key: ""                               # API密钥
  seed: 42                                  # 随机种子
```

**配置说明：**

- `platform`: 精炼器运行平台
- `method`: API调用方法，通常为 `openai`
- `model_name`: 使用的语言模型名称
- `base_url`: API服务的基础URL
- `api_key`: 访问API所需的密钥

### 6. Sink 配置

```yaml
sink:
  platform: "local"                        # Sink平台
  drain_timeout: 10.0                       # 排空超时时间（秒）
  drain_quiet_period: 0.3                   # 静默期（秒）
```

**配置说明：**

- `platform`: Sink操作器运行平台
- `drain_timeout`: 系统关闭时等待队列排空的最大时间
- `drain_quiet_period`: 检查队列是否为空的间隔时间

### 7. LLM Generator 配置

```yaml
generator:
  type: "remote"                            # 生成器类型
  url: "http://localhost:11434/v1/chat/completions"  # API服务URL
  model: "llama2"                           # 模型名称
  api_key: "${OPENAI_API_KEY}"             # API密钥
  temperature: 0.7                          # 温度参数
  max_tokens: 2000                          # 最大token数
```

**配置说明：**

- `type`: 生成器类型，可选 `local` 或 `remote`
- `url`: 远程API服务的完整URL
- `model`: 使用的语言模型名称
- `api_key`: API访问密钥，支持环境变量
- `temperature`: 生成随机性控制，范围0-1
- `max_tokens`: 单次生成的最大token数量

> 💡 **提示**: 可以使用 `sage config llm auto` 命令自动检测和配置本地LLM服务。详见
> [CLI参考](../../tools/cli_reference.md#llm-%E6%9C%8D%E5%8A%A1%E8%87%AA%E5%8A%A8%E9%85%8D%E7%BD%AE)。

- `seed`: 随机种子，用于保证结果的可重现性

### 6. Generator 配置

生成器支持多种运行模式：

#### 本地模式 (Local)

```yaml
generator:
  local:
    method: "hf"                            # 使用HuggingFace
    model_name: "meta-llama/Llama-2-13b-chat-hf"  # 模型名称
    seed: 42                                # 随机种子
```

#### VLLM模式

```yaml
generator:
  vllm:
    api_key: "token-abc123"                 # VLLM访问令牌
    method: "openai"                        # API方法
    model_name: "meta-llama/Llama-2-13b-chat-hf"  # 模型名称
    base_url: "http://localhost:8000/v1"    # VLLM服务URL
    seed: 42                                # 随机种子
```

#### 远程模式 (Remote)

```yaml
generator:
  remote:
    api_key: ""                             # 远程API密钥
    method: "openai"                        # API方法
    model_name: "qwen-turbo-0919"          # 远程模型名称
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"  # 远程API URL
    seed: 42                                # 随机种子
```

**配置说明：**

- `method`: 生成方法，可选 `hf`（HuggingFace）、`openai`（OpenAI API）
- `model_name`: 使用的语言模型名称
- `base_url`: API服务地址
- `api_key`: API访问密钥
- `seed`: 随机种子

### 7. Chunk (分块配置)

```yaml
chunk:
  chunk_size: 512                           # 文本块大小
  overlap: 128                              # 重叠字符数
```

**配置说明：**

- `chunk_size`: 文本分块的大小（字符数）
- `overlap`: 相邻文本块之间的重叠字符数

### 8. Writer (写入器配置)

```yaml
writer:
  platform: "local"                        # 写入平台
  stm: True                                 # 启用短期记忆
  ltm: False                                # 禁用长期记忆
```

**配置说明：**

- `platform`: 写入器运行平台
- `stm`: 是否启用短期记忆存储
- `ltm`: 是否启用长期记忆存储

### 9. Sink 配置

```yaml
sink:
  platform: "local"                        # 输出平台
  file_path: "output.txt"                   # 输出文件路径
```

**配置说明：**

- `platform`: 输出处理平台
- `file_path`: 结果输出文件的路径

### 10. Prompter 配置

```yaml
promptor:
  platform: "local"                        # 提示器平台
```

**配置说明：**

- `platform`: 提示器运行平台

### 11. Evaluate 配置

```yaml
evaluate:
  platform: "local"                        # 评估平台
```

**配置说明：**

- `platform`: 评估器运行平台

## 多智能体配置 (multiagent_config.yaml)

### Question Bot (问题机器人)

```yaml
question_bot:
  method: "openai"                          # API方法
  model_name: "qwen-turbo"                 # 模型名称
  api_key: "sk-xxx"                        # API密钥
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"  # API URL

question_bot_sink:
  stage_directory: "question_bot"           # 阶段目录
```

### Chief Bot (主控机器人)

```yaml
chief_bot:
  llm:
    method: "openai"                        # LLM方法
    model_name: "qwen-turbo"               # 模型名称
    api_key: "sk-xxx"                      # API密钥
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"  # API URL

chief_bot_sink:
  stage_directory: "chief_bot"              # 阶段目录
```

### Searcher Bot (搜索机器人)

```yaml
searcher_filter:
  tools: ["web_search"]                     # 可用工具列表

searcher_bot:
  method: "openai"                          # API方法
  model_name: "qwen-turbo"                 # 模型名称
  api_key: "sk-xxx"                        # API密钥
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"  # API URL

searcher_tool:
  url: "https://api.bochaai.com/v1/web-search"  # 搜索工具API
  api_key: "sk-xxx"                        # 搜索工具API密钥

searcher_tool_sink:
  stage_directory: "searcher_tool"          # 搜索工具输出目录
```

### Answer Bot (回答机器人)

```yaml
answer_bot:
  method: "openai"                          # API方法
  model_name: "qwen-turbo"                 # 模型名称
  api_key: "sk-xxx"                        # API密钥
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"  # API URL
```

## 配置文件使用场景

### 1. 基础问答系统 (`config.yaml`)

- 适用于简单的问答场景
- 使用本地平台和基础组件

### 2. 数据摄取 (`config_for_ingest.yaml`)

- 专门用于数据摄取和预处理
- 配置文本分块和内存写入

### 3. 问答系统 (`config_for_qa.yaml`)

- 完整的问答流程配置
- 包含检索、重排序、精炼和生成

### 4. BM25搜索 (`config_bm25s.yaml`)

- 启用BM25搜索算法的配置
- 适用于基于关键词的检索场景

### 5. 分布式集群 (`config_ray.yaml`)

- 使用Ray进行分布式处理
- 适用于大规模数据处理

### 6. HuggingFace模型 (`config_hf.yaml`)

- 专门使用HuggingFace模型的配置
- 适用于本地模型推理

### 7. 混合模式 (`config_mixed.yaml`)

- 结合本地和远程组件
- 灵活的部署配置

### 8. 评估模式 (`config_evaluate.yaml`)

- 专门用于模型评估
- 配置评估数据和指标

### 9. 多智能体系统 (`multiagent_config.yaml`)

- 配置多个智能体协作
- 支持复杂的任务分解和协作

## 配置最佳实践

1. **API密钥管理**: 建议将API密钥存储在环境变量中，避免在配置文件中硬编码
1. **平台选择**: 根据实际部署环境选择合适的平台（local/remote）
1. **资源配置**: 根据硬件资源调整模型选择和参数设置
1. **版本管理**: 保持配置文件的版本号更新
1. **路径配置**: 使用相对路径以提高配置的可移植性

## 注意事项

- 所有API密钥应妥善保管，不要提交到版本控制系统
- 模型名称需要与实际可用的模型匹配
- 文件路径需要确保存在且有相应的读写权限
- 远程API的base_url需要网络可访问
- seed参数用于保证结果的可重现性，建议在生产环境中固定设置
