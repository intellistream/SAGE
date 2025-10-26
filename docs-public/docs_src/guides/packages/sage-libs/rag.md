# RAG 核心组件 (Core RAG Components)

本文档详细介绍了 SAGE 系统中用于构建检索增强生成 (RAG) 流程的核心组件。这些组件涵盖了从数据分块、检索、重排到生成和评估的全过程。

______________________________________________________________________

## 1. 数据准备与触发 (Data Preparation & Trigger)

### 1.1 分块 (Chunking)

分块是将长文本分割成小块，以便于后续的检索和处理。

#### `CharacterSplitter`

基于字符进行文本分割。

- **核心功能**: 将输入文本按指定的字符数 `chunk_size` 和重叠数 `overlap` 进行切分。
- **输入**: `str` - 待切分的文本。
- **输出**: `List[str]` - 文本块列表。
- **用例**: 适用于处理不方便按词或句子分割的文本，或在需要快速、简单切分的场景。
- **配置要求**:
  - `chunk_size` (int): 每个块的字符数 (默认: 512)。
  - `overlap` (int): 相邻块之间的重叠字符数 (默认: 128)。

#### `SentenceTransformersTokenTextSplitter`

使用 SentenceTransformer 的分词器进行文本分割，更符合模型处理习惯。

- **核心功能**: 基于模型的分词器将文本切分为 token 块。
- **输入**: `str` - 待切分的文本。
- **输出**: `List[str]` - 文本块列表。
- **用例**: RAG 应用的首选分块方法。因为它遵循下游模型的 tokenization 逻辑，能更好地保留语义完整性，提高检索和生成的质量。
- **配置要求**:
  - `model_name` (str): SentenceTransformer 模型名称 (默认: "sentence-transformers/all-mpnet-base-v2")。
  - `chunk_size` (int): 每个块的 token 数 (默认: 512)。
  - `chunk_overlap` (int): 相邻块之间的重叠 token 数 (默认: 50)。

### 1.2 触发器 (Trigger)

触发器是启动数据流的外部接口。

#### `TriggerableSource`

一个通用的、可由外部事件触发的数据源。

- **核心功能**: 维护一个内部队列，外部调用 `trigger(data)` 方法将数据放入队列，`execute()` 方法从队列中取出数据并送入数据流。
- **用例**: 构建交互式应用，例如，数据流由 Web 界面的用户提交、或消息队列中新消息的到达等外部事件启动。
- **方法**:
  - `trigger(data)`: 向队列中添加数据。
  - `stop()`: 停止数据源。
  - `is_empty()`: 检查队列是否为空。
- **配置要求**:
  - `wait_timeout` (float): 轮询模式下等待新输入的超时时间（秒）(默认: 1.0)。
  - `enable_polling` (bool): 是否启用轮询模式 (默认: True)。若为 `False`，则 `execute` 方法会一直阻塞直到有数据进入。

#### `RESTApiSource`

专门用于处理 REST API 请求的触发器，继承自 `TriggerableSource`。

- **核心功能**: 封装了处理 API 请求的逻辑，如请求ID管理、队列大小限制等。
- **用例**: 为 SAGE 流水线创建一个 Web Service 终端。前端应用可以通过调用此终端来触发 RAG 流程。
- **方法**:
  - `trigger_request(request_data)`: 触发一个 API 请求。
- **配置要求**:
  - `request_timeout` (float): 请求处理的超时时间 (默认: 30.0)。
  - `max_queue_size` (int): 最大允许的排队请求数 (默认: 100)。

______________________________________________________________________

## 2. 信息检索 (Information Retrieval)

### 2.1 搜索引擎 (Searcher)

#### `BochaWebSearch`

调用博查智能的 Web Search API 进行在线搜索。

- **核心功能**: 将输入查询发送到博查 API，并返回搜索结果。
- **输入**: `str` - 查询语句。
- **输出**: `Dict[str, Any]` - API 返回的 JSON 对象。
- **用例**: 解答需要从互联网获取最新信息的问题，而这些信息在本地知识库中不存在。
- **配置要求**:
  - `api_key` (str): 博查 API 的密钥 (必需)。
  - `count` (int): 返回结果数量 (默认: 10)。
  - `page` (int): 查询页码 (默认: 1)。
  - `summary` (bool): 是否请求返回摘要 (默认: True)。

### 2.2 检索器 (Retriever)

从本地或内存知识库中检索信息。

#### `DenseRetriever`

使用向量化模型进行密集检索。

- **核心功能**: 根据输入查询，从配置的长期记忆 (LTM) 知识库中检索最相关的文本块。
- **输入**: `str` - 查询语句。
- **输出**: `Tuple[str, List[str]]` - (原始查询, 检索到的文本块列表)。
- **用例**: 从大规模、预先索引好的知识库中查找语义上相似的文档（例如，为员工的问题找到相关的内部政策文件）。
- **配置要求**:
  - `ltm` (bool): 是否启用长期记忆检索 (必需)。
  - `ltm_config` (dict): LTM 的具体配置，如集合名称、向量模型等。

#### `BM25sRetriever`

使用 BM25s 算法进行稀疏检索。

- **核心功能**: 利用 BM25s 算法从指定集合中检索文本。
- **输入**: `str` - 查询语句。
- **输出**: `Tuple[str, List[str]]` - (原始查询, 检索到的文本块列表)。
- **用例**: 进行关键词搜索，对包含特定术语、名称或代码的查询非常有效。常与 `DenseRetriever` 结合使用以实现混合搜索。
- **配置要求**:
  - `bm25s_collection` (str): BM25s 集合的名称 (必需)。
  - `bm25s_config` (dict): BM25s 的具体配置。

### 2.3 重排器 (Reranker)

对检索到的结果进行重新排序，以提高最相关文档的排名。

#### `BGEReranker`

使用 `BAAI/bge-reranker-v2-m3` 模型进行重排。

- **核心功能**: 计算查询与每个文档的相关性分数，并按分数降序排列。
- **输入**: `Tuple[str, List[str]]` - (查询, 文档列表)。
- **输出**: `Tuple[str, List[str]]` - (查询, 重排后的文档列表)。
- **用例**: 精炼检索器的返回结果。例如，在检索器召回 20-50 个文档后，使用重排器精确地找出最相关的 3-5 个文档送入生成器，从而提高效率和答案的准确性。
- **配置要求**:
  - `model_name` (str): 模型名称 (默认: "BAAI/bge-reranker-v2-m3")。
  - `top_k` (int): 返回排名最高的 k 个文档。

#### `LLMbased_Reranker`

使用 `BAAI/bge-reranker-v2-gemma` 模型进行重排。

- **核心功能**: 基于一个生成式 LLM 判断每个文档是否包含查询的答案（"Yes" 或 "No"），并据此排序。
- **输入**: `Tuple[str, List[str]]` - (查询, 文档列表)。
- **输出**: `Tuple[str, List[str]]` - (查询, 重排后的文档列表)。
- **用例**: 与 `BGEReranker` 类似，但使用更强大（也可能更慢）的生成式模型进行重排。适用于简单相关性分数不足以判断的复杂查询。
- **配置要求**:
  - `model_name` (str): 模型名称 (默认: "BAAI/bge-reranker-v2-gemma")。
  - `top_k` (int): 返回排名最高的 k 个文档。

______________________________________________________________________

## 3. 查询理解与生成 (Query Understanding & Generation)

### 3.1 查询分析器 (Query Profiler)

#### `Query_Profiler`

分析用户查询的复杂性，以决定后续的处理策略。

- **核心功能**: 解析大模型返回的关于查询的 JSON 分析结果，并输出处理策略。
- **输入**: `str` - 包含查询分析的 JSON 字符串。
- **输出**: `List` - `[synthesis_method, num_chunks, intermediate_length_range]`，例如
  `["map_reduce", [3, 9], 100]`。
- **用例**: 在高级 RAG 系统中充当“路由器”。通过分析用户问题，决定采用哪种 RAG 策略（如简单检索 vs. 多步推理），使系统更具适应性。
- **配置要求**: 此组件通常没有自己的配置，因为它处理的是上游 LLM 调用的输出。

### 3.2 提示词工程 (Prompting)

#### `QAPromptor`

构建用于问答任务的提示词。

- **核心功能**: 将查询和可选的上下文（corpus）格式化为大模型所需的 `system` 和 `user` 消息列表。
- **输入**: `str` (查询) 或 `Tuple[str, List[str]]` (查询, 上下文)。
- **输出**: `List[str, List[dict]]` - `[query, prompt_list]`。
- **用例**: 任何需要根据检索到的上下文来回答问题的 RAG 流水线的标准组件。
- **配置要求**: 无，其模板是为通用问答任务硬编码的。

#### `SummarizationPromptor`

构建用于摘要任务的提示词。

- **核心功能**: 将查询和上下文格式化为摘要模型的提示词。
- **输入**: `Tuple[str, List[str]]` - (查询, 上下文)。
- **输出**: `List[dict]` - 提示词列表。
- **用例**: 在 "map-reduce" 等 RAG 策略中使用，先将多个独立的文档块进行摘要，然后将摘要内容合并以回答最终问题。
- **配置要求**: 无。

#### `QueryProfilerPromptor`

构建用于查询分析的提示词。

- **核心功能**: 将用户查询包装成一个请求，让大模型分析其特性。
- **输入**: `str` - 用户查询。
- **输出**: `List[dict]` - 发送给大模型的提示词。
- **用例**: `Query_Profiler` 的上游组件，它定义了*如何*请求大模型来分析一个查询。
- **配置要求**:
  - `metadata` (dict): 描述知识库的元数据，帮助模型更好地理解查询背景。
  - `chunk_size` (int): 知识库的分块大小。

### 3.3 生成器 (Generator)

调用大模型生成最终答案。

#### `OpenAIGenerator`

调用与 OpenAI API 兼容的端点（如 VLLM, DashScope）进行文本生成。

- **核心功能**: 向指定模型端点发送提示词并返回生成结果。
- **输入**: `List` - `[user_query, prompt]` 或 `[prompt]`。
- **输出**: `Tuple[str, str]` - `(user_query, generated_text)`。
- **用例**: RAG 流水线的最后一步，整合精炼后的上下文和原始查询，生成用户可读的答案。可以连接到 OpenAI, VLLM, DashScope 等服务。
- **配置要求**:
  - `method` (str): 调用方法，如 "openai"。
  - `model_name` (str): 模型名称，如 "gpt-4o-mini"。
  - `base_url` (str): API 的基础 URL。
  - `api_key` (str): API 密钥。
  - `seed` (int): 随机种子 (可选)。

#### `OpenAIGeneratorWithHistory`

带滚动对话历史的生成器。

- **核心功能**: 在 `OpenAIGenerator` 的基础上维护一个对话历史队列，每次请求时自动带上最近的对话历史。
- **输入**: `List` - `[user_query, prompt_list]`。
- **输出**: `Tuple[str, str]` - `(user_query, generated_text)`。
- **用例**: 构建对话式聊天机器人。它能记住之前的对话，允许用户提出追问，使交互更自然。
- **配置要求**:
  - 与 `OpenAIGenerator` 相同。
  - `max_history_turns` (int): 最大保留的对话轮数 (默认: 5)。

#### `HFGenerator`

调用本地 Hugging Face 模型进行生成。

- **核心功能**: 加载并运行本地的 Hugging Face 模型。
- **输入**: `List` - `[user_query, prompt]` 或 `[prompt]`。
- **输出**: `Tuple[str, str]` - `(user_query, generated_text)`。
- **用例**: 出于数据隐私、成本或自定义的需求，使用本地部署的开源模型。
- **配置要求**:
  - `method` (str): 调用方法，如 "hf"。
  - `model_name` (str): Hugging Face 上的模型名称或本地路径。

### 3.4 写入器 (Writer)

#### `MemoryWriter`

将处理过程中的数据写入到 SAGE 的记忆模块中。

- **核心功能**: 将输入数据写入到配置的短期记忆 (STM)、长期记忆 (LTM) 或文档化认知记忆 (DCM) 中。
- **输入**: `Union[str, List[str], Tuple[str, str]]` - 任意格式的数据。
- **用例**: 创建一个能自我完善的 RAG 系统。例如，在一次用户交互后，可将生成的答案或用户反馈写回 LTM，使系统能从交互中学习。
- **配置要求**:
  - `stm`, `ltm`, `dcm` (bool): 是否启用相应的记忆模块。
  - `stm_collection`, `ltm_collection`, `dcm_collection` (str): 相应记忆模块的集合名称。
  - `stm_config`, `ltm_config`, `dcm_config` (dict): 具体配置。

______________________________________________________________________

## 4. 评估 (Evaluation)

评估模块用于衡量 RAG 流程各个环节和最终输出的质量。

- **通用用例**: 在开发或测试环境中，将这些评估组件串联在生成器之后，可以为每个问答对自动计算质量和性能指标，从而实现快速实验和回归测试。
- **通用输入**: 所有评估组件都接收一个 `dict`，通常包含 `references` (标准答案列表) 和 `generated` (模型生成答案)。
- **通用输出**: 在控制台打印评估分数，并透传输入的 `dict` 以便链式调用。
- **通用配置**: 通常无需配置，因为它们操作的是流程中传递的标准化字典。

### 4.1 文本相似度评估

- **`F1Evaluate`**: 计算生成答案和标准答案之间的 F1 分数。
- **`RecallEvaluate`**: 计算召回率。
- **`BertRecallEvaluate`**: 使用 BERT 模型计算语义相似度作为召回率。
- **`RougeLEvaluate`**: 计算 ROUGE-L 分数，衡量最长公共子序列。
- **`BRSEvaluate`**: 计算基于词袋的召回率 (Bag-of-Words Recall Score)。
- **`AccuracyEvaluate`**: 计算精确匹配准确率。

### 4.2 性能与指标评估

- **`TokenCountEvaluate`**: 计算生成答案的 token 数量。
- **`LatencyEvaluate`**: 计算生成延迟。
- **`ContextRecallEvaluate`**: 评估检索阶段的上下文召回率。
- **`CompressionRateEvaluate`**: 评估信息压缩率（原始文档与精炼后文档的长度比）。
