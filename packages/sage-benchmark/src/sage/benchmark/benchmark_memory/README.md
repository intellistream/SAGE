# Memory Test Pipeline - 数据流分析

## 概述

本文档详细分析不同 YAML 配置下，Pipeline 中算子级别的数据流转换过程。

## Pipeline 架构

### 三层 Pipeline 结构

```
主 Pipeline (Main)
├── MemorySource → PipelineCaller → MemorySink
│
├── 记忆插入 Pipeline (Insert)
│   └── PreInsert → MemoryInsert → PostInsert
│
└── 记忆测试 Pipeline (Test)
    └── PreRetrieval → MemoryRetrieval → PostRetrieval → MemoryTest
```

### Pipeline 调用流程

```
MemorySource (批量数据源)
    ↓ 产生数据包
PipelineCaller (协调器)
    ├→ 调用 memory_insert_service (插入 Pipeline)
    └→ 调用 memory_test_service (测试 Pipeline，问题驱动)
    ↓ 返回测试结果
MemorySink (收集结果)
```

---

## 配置模式对比

### 模式 1: Short-Term Memory (STM)
**配置文件**: `locomo_short_term_memory_pipeline.yaml`

**核心配置**:
```yaml
services:
  register_memory_service: "short_term_memory"
  memory_insert_adapter: "to_dialogs"
  
operators:
  pre_insert:
    action: "none"
  pre_retrieval:
    action: "none"
```

### 模式 2: Vector Hash Memory with TiM (三元组)
**配置文件**: `locomo_tim_pipeline.yaml`

**核心配置**:
```yaml
runtime:
  embedding_base_url: "http://localhost:8091/v1"
  embedding_model: "BAAI/bge-m3"

services:
  register_memory_service: "vector_hash_memory"
  memory_insert_adapter: "to_refactor"
  
operators:
  pre_insert:
    action: "tri_embed"  # 三元组提取 + Embedding
  pre_retrieval:
    action: "embedding"  # 问题 Embedding
```

---

## 数据流详解

## 1. 主 Pipeline 数据流

### MemorySource → PipelineCaller

**MemorySource 输出** (所有模式相同):
```python
{
    "task_id": "conv-26",
    "session_id": 12,
    "dialog_id": 0,  # 或 2, 4, 6... (偶数)
    "dialogs": [
        {
            "speaker": "Alice",
            "text": "Hello, how are you?",
            "date_time": "2023-08-01"
        },
        {
            "speaker": "Bob", 
            "text": "I'm fine, thanks!",
            "date_time": "2023-08-01"
        }
    ],
    "dialog_len": 2,  # 1 或 2
    "packet_idx": 15,
    "total_packets": 50
}
```

**说明**:
- 每个数据包包含 1-2 条对话
- `dialog_id` 为偶数索引 (0, 2, 4, ...)
- `dialog_len=1`: 单条对话
- `dialog_len=2`: 一问一答对话

---

## 2. 记忆插入 Pipeline (Insert Pipeline)

### 模式 1: STM (Short-Term Memory)

#### 2.1.1 PreInsert (action="none")

**输入** (from PipelineCaller):
```python
{
    "task_id": "conv-26",
    "session_id": 12,
    "dialog_id": 0,
    "dialogs": [
        {"speaker": "Alice", "text": "Hello", "date_time": "2023-08-01"},
        {"speaker": "Bob", "text": "Hi", "date_time": "2023-08-01"}
    ]
}
```

**处理**: 
- `action="none"`: 不做任何预处理
- 将输入包装为长度为 1 的列表

**输出**:
```python
[
    {
        "data": {
            "task_id": "conv-26",
            "session_id": 12,
            "dialog_id": 0,
            "dialogs": [
                {"speaker": "Alice", "text": "Hello", "date_time": "2023-08-01"},
                {"speaker": "Bob", "text": "Hi", "date_time": "2023-08-01"}
            ]
        }
    }
]
```

#### 2.1.2 MemoryInsert (adapter="to_dialogs")

**输入**: PreInsert 的输出列表

**处理**:
1. 遍历列表中的每个 `entry_dict`
2. 调用 `DataParser.extract(entry_dict)` (adapter="to_dialogs")
   - 从 `data.dialogs` 提取对话列表
   - 格式化为单个字符串 (多条对话用 `\n` 合并)
3. 调用 `call_service(service_name, entry=str, vector=None, metadata=None)`

**DataParser 转换**:
```python
# 输入 entry_dict
{
    "data": {
        "dialogs": [
            {"speaker": "Alice", "text": "Hello", "date_time": "2023-08-01"},
            {"speaker": "Bob", "text": "Hi", "date_time": "2023-08-01"}
        ]
    }
}

# DataParser.extract() 输出 (to_dialogs)
"(2023-08-01)Alice: Hello\n(2023-08-01)Bob: Hi"  # 单个字符串
```

**调用服务**:
```python
call_service(
    "short_term_memory",
    entry="(2023-08-01)Alice: Hello\n(2023-08-01)Bob: Hi",
    vector=None,
    metadata=None,
    method="insert"
)
```

**ShortTermMemoryService 存储**:
```python
# 存储格式
{
    "text": "(2023-08-01)Alice: Hello\n(2023-08-01)Bob: Hi"
}
```

#### 2.1.3 PostInsert (action="none")

**输入**: MemoryInsert 的透传数据

**处理**: 
- `action="none"`: 直接透传
- 不做任何后处理

**输出**: 原数据透传

---

### 模式 2: TiM (三元组 + Embedding)

#### 2.2.1 PreInsert (action="tri_embed")

**输入** (同模式 1):
```python
{
    "task_id": "conv-26",
    "session_id": 12,
    "dialog_id": 0,
    "dialogs": [
        {"speaker": "Alice", "text": "I work at Google", "date_time": "2023-08-01"}
    ]
}
```

**处理**:
1. 使用 `PreInsertParser.format_dialogue(dialogs)` 格式化对话为字符串
2. 使用 LLM 提取三元组 (基于 `triple_extraction_prompt`)
3. 解析三元组文本
4. 重构为自然语言描述
5. 对每个重构描述进行 Embedding
6. 构建记忆条目列表

**内部转换流程**:

```python
# 1. 格式化对话
dialogue = "(2023-08-01)Alice: I work at Google"

# 2. LLM 提取三元组
llm_output = """
(Alice, works at, Google)
"""

# 3. 解析三元组
triples = [("Alice", "works at", "Google")]

# 4. 重构为自然语言
refactor_descriptions = ["Alice works at Google"]

# 5. 生成 Embedding
embeddings = [[0.12, 0.34, 0.56, ...]]  # 1024 维向量

# 6. 构建条目
memory_entries = [
    {
        "dialogs": [{"speaker": "Alice", "text": "I work at Google", "date_time": "2023-08-01"}],
        "triple": ("Alice", "works at", "Google"),
        "refactor": "Alice works at Google",
        "embedding": [0.12, 0.34, 0.56, ...]
    }
]
```

**输出**:
```python
[
    {
        "dialogs": [...],
        "triple": ("Alice", "works at", "Google"),
        "refactor": "Alice works at Google",
        "embedding": [0.12, 0.34, 0.56, ...]  # numpy array
    },
    # ... 可能有多个三元组
]
```

**注意**: 如果没有提取到三元组，返回 `None`

#### 2.2.2 MemoryInsert (adapter="to_refactor")

**输入**: PreInsert 的输出列表 (或 None)

**处理**:
1. 如果输入为 `None` 或空列表，直接返回
2. 遍历列表中的每个 `entry_dict`
3. 调用 `DataParser.extract(entry_dict)` (adapter="to_refactor")
   - 从 `refactor` 字段提取字符串
4. 提取 `embedding` 和 `metadata`
5. 调用 `call_service(service_name, entry=str, vector=array, metadata=dict)`

**DataParser 转换**:
```python
# 输入 entry_dict
{
    "dialogs": [...],
    "triple": ("Alice", "works at", "Google"),
    "refactor": "Alice works at Google",
    "embedding": [0.12, 0.34, ...]
}

# DataParser.extract() 输出 (to_refactor)
"Alice works at Google"  # 字符串
```

**调用服务**:
```python
call_service(
    "vector_hash_memory",
    entry="Alice works at Google",
    vector=[0.12, 0.34, ...],  # numpy array
    metadata=None,
    method="insert"
)
```

**VectorHashMemoryService 存储**:
```python
# 使用 LSH 索引存储
collection.insert(
    index="lsh_index",
    text="Alice works at Google",
    vector=[0.12, 0.34, ...],
    metadata=None
)
```

#### 2.2.3 PostInsert (action="none")

**处理**: 同模式 1，直接透传

---

## 3. 记忆测试 Pipeline (Test Pipeline)

### 模式 1: STM (Short-Term Memory)

#### 3.1.1 PreRetrieval (action="none")

**输入** (from PipelineCaller):
```python
{
    "question": "Where does Alice work?",
    "answer": "Google",
    "task_id": "conv-26",
    "session_id": 12,
    "question_id": 5
}
```

**处理**: 
- `action="none"`: 不做任何预处理
- 直接透传

**输出**: 原数据不变

#### 3.1.2 MemoryRetrieval

**输入**: PreRetrieval 的输出

**处理**:
1. 提取 `question`
2. 调用 `call_service(service_name, query=question, vector=None, metadata=None, method="retrieve")`
3. 将检索结果添加到 `memory_data` 字段

**调用服务**:
```python
result = call_service(
    "short_term_memory",
    query="Where does Alice work?",
    vector=None,
    metadata=None,
    method="retrieve"
)
```

**ShortTermMemoryService 返回**:
```python
[
    {"text": "(2023-08-01)Alice: I work at Google"},
    {"text": "(2023-08-01)Bob: That's a great company!"},
    {"text": "(2023-08-01)Alice: Yes, I love it there"}
]
# 返回最近的 max_dialog=3 条记忆
```

**输出**:
```python
{
    "question": "Where does Alice work?",
    "answer": "Google",
    "task_id": "conv-26",
    "session_id": 12,
    "question_id": 5,
    "memory_data": [
        {"text": "(2023-08-01)Alice: I work at Google"},
        {"text": "(2023-08-01)Bob: That's a great company!"},
        {"text": "(2023-08-01)Alice: Yes, I love it there"}
    ]
}
```

#### 3.1.3 PostRetrieval (action="none")

**输入**: MemoryRetrieval 的输出

**处理**:
1. 添加 `conversation_format_prompt` 前缀
2. 将 `memory_data` 中的所有 `text` 字段拼接
3. 添加到 `history_text` 字段

**转换**:
```python
# 输入 memory_data
[
    {"text": "(2023-08-01)Alice: I work at Google"},
    {"text": "(2023-08-01)Bob: That's a great company!"},
    {"text": "(2023-08-01)Alice: Yes, I love it there"}
]

# 输出 history_text
"""
The following is some history information.
(2023-08-01)Alice: I work at Google
(2023-08-01)Bob: That's a great company!
(2023-08-01)Alice: Yes, I love it there
"""
```

**输出**:
```python
{
    "question": "Where does Alice work?",
    "answer": "Google",
    "task_id": "conv-26",
    "session_id": 12,
    "question_id": 5,
    "memory_data": [...],
    "history_text": "The following is some history information.\n..."
}
```

#### 3.1.4 MemoryTest

**输入**: PostRetrieval 的输出

**处理**:
1. 构建完整 prompt: `history_text` + `prompt_template.format(question=question)`
2. 调用 LLM 生成答案
3. 评估答案准确性
4. 构建测试结果

**Prompt 构建**:
```
The following is some history information.
(2023-08-01)Alice: I work at Google
(2023-08-01)Bob: That's a great company!
(2023-08-01)Alice: Yes, I love it there

Based on the above context, answer the following question concisely using exact words from the context whenever possible. If the information is not mentioned in the conversation, respond with "Not mentioned in the conversation".

Question: Where does Alice work?
Answer:
```

**LLM 生成**: `"Google"`

**输出**:
```python
{
    "question": "Where does Alice work?",
    "predicted_answer": "Google",
    "ground_truth": "Google",
    "is_correct": True,
    "task_id": "conv-26",
    "session_id": 12,
    "question_id": 5
}
```

---

### 模式 2: TiM (Vector Hash Memory)

#### 3.2.1 PreRetrieval (action="embedding")

**输入** (同模式 1):
```python
{
    "question": "Where does Alice work?",
    "answer": "Google",
    ...
}
```

**处理**:
1. 提取 `question` 字段
2. 调用 `EmbeddingGenerator.embed(question)` 生成查询向量
3. 将向量添加到 `query_embedding` 字段

**内部转换**:
```python
# 1. 提取问题
question = "Where does Alice work?"

# 2. 生成 Embedding
query_embedding = embedding_model.embed(question)
# 输出: [0.23, 0.45, 0.67, ...]  # 1024 维向量
```

**输出**:
```python
{
    "question": "Where does Alice work?",
    "answer": "Google",
    "query_embedding": [0.23, 0.45, 0.67, ...],  # numpy array
    ...
}
```

#### 3.2.2 MemoryRetrieval

**输入**: PreRetrieval 的输出

**处理**:
1. 提取 `question` 和 `query_embedding`
2. 调用 `call_service(service_name, query=question, vector=query_embedding, metadata=None, method="retrieve")`

**调用服务**:
```python
result = call_service(
    "vector_hash_memory",
    query="Where does Alice work?",
    vector=[0.23, 0.45, 0.67, ...],
    metadata=None,
    method="retrieve"
)
```

**VectorHashMemoryService 返回**:
```python
[
    {
        "text": "Alice works at Google",
        "metadata": None
    },
    {
        "text": "Bob lives in New York",
        "metadata": None
    },
    # ... 基于 LSH 相似度的 topk 结果
]
```

**输出**:
```python
{
    "question": "Where does Alice work?",
    "answer": "Google",
    "query_embedding": [0.23, 0.45, ...],
    "memory_data": [
        {"text": "Alice works at Google", "metadata": None},
        {"text": "Bob lives in New York", "metadata": None}
    ],
    ...
}
```

#### 3.2.3 PostRetrieval (action="none")

**处理**: 同模式 1

**转换**:
```python
# 输入 memory_data
[
    {"text": "Alice works at Google"},
    {"text": "Bob lives in New York"}
]

# 输出 history_text
"""
The following is some history information.
Alice works at Google
Bob lives in New York
"""
```

#### 3.2.4 MemoryTest

**处理**: 同模式 1

**Prompt 构建**:
```
The following is some history information.
Alice works at Google
Bob lives in New York

Based on the above context, answer the following question concisely using exact words from the context whenever possible. If the information is not mentioned in the conversation, respond with "Not mentioned in the conversation".

Question: Where does Alice work?
Answer:
```

---

## 4. 数据格式统一规范

### 4.1 所有 Memory Service 的统一接口

#### Insert 方法
```python
def insert(self, text: str, vector=None, metadata: dict | None = None) -> None
```

**参数**:
- `text` (str): 要插入的文本内容（必需）
  - STM: 格式化的对话字符串
  - VectorHash: 三元组重构描述
- `vector` (numpy.ndarray | None): 向量表示（可选）
  - STM: 不使用 (None)
  - VectorHash: Embedding 向量
- `metadata` (dict | None): 元数据（可选）

#### Retrieve 方法
```python
def retrieve(self, query=None, vector=None, metadata=None) -> list[dict[str, Any]]
```

**返回格式** (统一):
```python
[
    {
        "text": "...",      # 记忆文本 (必需)
        "metadata": {...}   # 元数据 (可选)
    },
    ...
]
```

### 4.2 DataParser 统一规范

#### extract 方法
```python
def extract(self, data: dict[str, Any]) -> str
```

**所有 adapter 都返回字符串**:
- `to_dialogs`: 格式化对话字符串（多条用 `\n` 合并）
- `to_refactor`: 三元组重构描述

---

## 5. 关键设计模式

### 5.1 列表封装模式

**PreInsert 输出**: 始终返回 `list[dict]` 或 `None`
```python
# action="none"
[{"data": {...}}]  # 长度为 1

# action="tri_embed"  
[
    {"dialogs": [...], "triple": ..., "refactor": "...", "embedding": [...]},
    {"dialogs": [...], "triple": ..., "refactor": "...", "embedding": [...]}
]  # 长度 >= 0 (可能为空)
```

**好处**:
- 统一处理逻辑
- 支持一对多转换（一个对话 → 多个三元组）
- MemoryInsert 可以用简单的循环处理

### 5.2 字符串统一模式

**DataParser.extract()**: 所有模式都返回 `str`

**好处**:
- MemoryInsert 无需类型判断
- Memory Service 接口简单统一
- 对话合并在 DataParser 内部完成

### 5.3 透传模式

**PostInsert 和某些模式的 PreRetrieval**: 
- `action="none"` 时直接透传
- 保留扩展性，未来可添加功能

---

## 6. 配置切换对比表

| 配置项 | STM 模式 | TiM 模式 |
|--------|----------|----------|
| **Memory Service** | short_term_memory | vector_hash_memory |
| **Insert Adapter** | to_dialogs | to_refactor |
| **PreInsert Action** | none | tri_embed |
| **PreRetrieval Action** | none | embedding |
| **插入数据类型** | 格式化对话字符串 | 三元组重构描述 |
| **检索机制** | 队列（最近 N 条） | LSH 向量相似度 |
| **需要 Embedding** | ❌ | ✅ (需要 embedding server) |
| **需要 LLM** | ❌ (仅测试时) | ✅ (提取三元组 + 测试) |

---

## 7. 运行示例

### 启动 STM 模式
```bash
python memory_test_pipeline.py \
    --config config/locomo_short_term_memory_pipeline.yaml \
    --task_id conv-26
```

### 启动 TiM 模式
```bash
# 1. 启动 Embedding Server
python examples/tutorials/embedding_server_example.py

# 2. 运行 Pipeline
python memory_test_pipeline.py \
    --config config/locomo_tim_pipeline.yaml \
    --task_id conv-26
```

---

## 8. 调试技巧

### 查看详细日志
```yaml
runtime:
  memory_insert_verbose: true   # 显示插入过程
  memory_test_verbose: true     # 显示测试过程
```

### 检查数据流
在关键算子中添加打印:
```python
# 在 MemoryInsert._insert_single_entry
print(f"[DEBUG] entry type: {type(entry)}")
print(f"[DEBUG] entry content: {entry}")

# 在 PostRetrieval._format_dialog_history
print(f"[DEBUG] memory_data: {memory_data}")
print(f"[DEBUG] history_text: {history_text}")
```

---

## 附录: 完整数据流图

### STM 模式完整流程
```
MemorySource
  ↓ {task_id, session_id, dialog_id, dialogs: [{speaker, text, date_time}]}
PipelineCaller
  ├→ Insert Pipeline
  │   ├ PreInsert (action=none)
  │   │   ↓ [{"data": {dialogs: [...]}}]
  │   ├ MemoryInsert (adapter=to_dialogs)
  │   │   ↓ extract() → str: "(date)speaker: text\n..."
  │   │   ↓ insert(text, vector=None, metadata=None)
  │   └ PostInsert (action=none)
  │
  └→ Test Pipeline (当问题数达到阈值)
      ├ PreRetrieval (action=none)
      │   ↓ {question, answer, ...}
      ├ MemoryRetrieval
      │   ↓ retrieve() → [{text: "...", metadata: {...}}]
      │   ↓ {question, memory_data: [...]}
      ├ PostRetrieval (action=none)
      │   ↓ {question, history_text: "prompt\ntext1\ntext2\n..."}
      └ MemoryTest
          ↓ LLM generate answer
          ↓ {question, predicted_answer, is_correct}
```

### TiM 模式完整流程
```
MemorySource
  ↓ {task_id, session_id, dialog_id, dialogs: [{speaker, text, date_time}]}
PipelineCaller
  ├→ Insert Pipeline
  │   ├ PreInsert (action=tri_embed)
  │   │   ↓ format_dialogue() → str
  │   │   ↓ LLM extract triples
  │   │   ↓ parse_triples() → [(s, p, o), ...]
  │   │   ↓ refactor_triples() → ["s p o", ...]
  │   │   ↓ embed_batch() → [vector1, vector2, ...]
  │   │   ↓ [{dialogs, triple, refactor, embedding}, ...]
  │   ├ MemoryInsert (adapter=to_refactor)
  │   │   ↓ extract() → str: "s p o"
  │   │   ↓ insert(text="s p o", vector=array, metadata=None)
  │   └ PostInsert (action=none)
  │
  └→ Test Pipeline
      ├ PreRetrieval (action=embedding)
      │   ↓ embed(question) → query_embedding
      │   ↓ {question, query_embedding, ...}
      ├ MemoryRetrieval
      │   ↓ retrieve(query, vector=query_embedding) → [{text, metadata}]
      │   ↓ {question, memory_data: [...]}
      ├ PostRetrieval (action=none)
      │   ↓ {question, history_text: "prompt\ntext1\ntext2\n..."}
      └ MemoryTest
          ↓ LLM generate answer
          ↓ {question, predicted_answer, is_correct}
```

---

## 总结

### 核心设计原则

1. **统一接口**: 所有 Memory Service 使用相同的 insert/retrieve 接口
2. **字符串为王**: DataParser 统一返回字符串，简化类型处理
3. **列表封装**: PreInsert 输出列表，支持一对多转换
4. **透传设计**: 不需要的算子直接透传，保留扩展性
5. **配置驱动**: 通过 YAML 配置切换不同模式，无需修改代码

### 扩展新模式

要添加新的记忆模式，只需：

1. 实现新的 Memory Service (遵循统一接口)
2. 在 MemoryServiceFactory 中注册
3. 配置 YAML:
   - `register_memory_service`: 服务名称
   - `memory_insert_adapter`: 数据提取方式
   - `pre_insert.action`: 预处理方式
   - `pre_retrieval.action`: 检索预处理方式
4. 可选：实现新的 DataParser adapter

**无需修改 Pipeline 代码！**
