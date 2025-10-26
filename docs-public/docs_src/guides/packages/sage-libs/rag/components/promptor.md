# 提示词生成组件 (Prompt Generation Components)

本文档详细介绍SAGE框架中`sage.libs.rag.promptor`模块的提示词生成组件。提示词组件是RAG系统的认知接口层，负责将检索上下文与用户查询有效融合，为生成模型提供结构化输入。

## 组件概述

### 核心功能
提示词生成组件在RAG系统中承担以下关键职责：

- **上下文整合**：将检索到的相关文档与用户查询进行智能融合
- **任务适配**：针对不同任务类型（问答、摘要、分析）提供专门的模板
- **格式标准化**：确保生成模型输入的一致性和有效性
- **语义增强**：通过结构化提示提升模型理解和生成质量

### 设计架构
所有提示词生成器继承自`MapFunction`基类，支持流水线处理：

```python
# 标准处理流程
input_data → 模板渲染 → 结构化提示 → 输出传递
```

### 模板引擎
采用Jinja2模板引擎，支持：
- 条件渲染
- 循环结构
- 变量替换
- 自定义过滤器

## 核心提示词生成器

### QAPromptor

#### 组件描述
`QAPromptor`是专门用于问答任务的提示词生成器，将用户问题与检索到的上下文文档组织成适合问答的结构化提示。

#### 技术规格

**输入格式**：
```python
input_data = (query, retrieved_documents)
# query: str - 用户查询
# retrieved_documents: List[str] - 检索到的相关文档
```

**输出格式**：
```python
output = (query, structured_prompt)
# query: str - 原始用户查询
# structured_prompt: str - 结构化的提示词
```

**内置模板**：
```jinja2
Instruction:
You are an intelligent assistant with access to a knowledge base. 
Answer the question below with reference to the provided context.
Only give me the answer and do not output any other words.

{%- if external_corpus %}
Relevant corpus for the current question:
{{ external_corpus }}
{%- endif %}

Question: {{ query }}
Answer:
```

#### 实现示例

##### 基础问答生成
```python
from sage.libs.rag.promptor import QAPromptor

# 初始化提示词生成器
qa_promptor = QAPromptor()

# 准备输入数据
user_query = "什么是向量数据库？"
retrieved_docs = [
    "向量数据库是专门存储和检索高维向量数据的数据库系统。",
    "ChromaDB是一个开源的向量数据库，支持相似度检索。",
    "向量数据库在RAG系统中用于存储文档的向量表示。"
]

# 生成结构化提示
query, prompt = qa_promptor.execute((user_query, retrieved_docs))

print("生成的提示词:")
print(prompt)
```

##### 自定义模板
```python
# 自定义模板配置
custom_template = """
Context: 您是一个专业的技术文档助手。
Task: 基于以下资料回答用户问题，要求准确、简洁。

参考资料:
{%- for doc in external_corpus %}
{{ loop.index }}. {{ doc }}
{%- endfor %}

用户问题: {{ query }}
您的回答:
"""

qa_promptor_custom = QAPromptor(template=custom_template)
```

### SummarizationPromptor

#### 组件描述
`SummarizationPromptor`专门用于摘要生成任务，将多个文档内容组织成适合摘要的结构化提示。

#### 技术规格

**内置模板**：
```jinja2
Instruction:
You are an intelligent assistant. Summarize the content provided below 
in a concise and clear manner.
Only provide the summary and do not include any additional information.

{%- if external_corpus %}
Content to summarize:
{{ external_corpus }}
{%- endif %}

Summary:
```

#### 实现示例
```python
from sage.libs.rag.promptor import SummarizationPromptor

# 初始化摘要提示词生成器
sum_promptor = SummarizationPromptor()

# 准备文档内容
documents = [
    "RAG技术结合了检索和生成两个步骤。",
    "检索步骤从知识库中找到相关信息。", 
    "生成步骤基于检索结果产生最终答案。"
]

# 生成摘要提示
_, summary_prompt = sum_promptor.execute(("", documents))
print("摘要提示词:", summary_prompt)
```

### QueryProfilerPromptor

#### 组件描述
`QueryProfilerPromptor`用于分析用户查询的特征，判断查询复杂度、所需推理类型等属性，为系统优化提供决策依据。

#### 技术规格

**分析维度**：
- 查询复杂度（简单/中等/复杂）
- 推理类型（事实性/分析性/综合性）
- 文档需求（单文档/多文档）
- 时效性要求（历史/实时）

**输出格式**：
```python
{
    "complexity": str,        # 查询复杂度
    "reasoning_type": str,    # 推理类型
    "document_scope": str,    # 文档范围需求
    "temporal_requirement": str  # 时效性需求
}
```

#### 实现示例
```python
from sage.libs.rag.promptor import QueryProfilerPromptor

# 初始化查询分析器
profiler = QueryProfilerPromptor()

# 分析简单事实查询
simple_query = "什么是Python？"
profile_result = profiler.execute(simple_query)

# 分析复杂推理查询  
complex_query = "对比分析Python和Java在机器学习领域的优缺点"
complex_profile = profiler.execute(complex_query)

print("简单查询分析:", profile_result)
print("复杂查询分析:", complex_profile)
```
### 2. SummarizationPromptor - 摘要提示词生成器

专门用于生成文本摘要任务的提示词。

#### 基本使用

```python
from sage.libs.rag.promptor import SummarizationPromptor

# 初始化
config = {}
sum_promptor = SummarizationPromptor(config)

# 输入：(查询, 要摘要的文本列表)
data = (
    "请总结以下内容",
    [
        "人工智能是计算机科学的一个重要分支...",
        "机器学习是人工智能的核心技术之一...",
        "深度学习近年来取得了突破性进展..."
    ]
)

result = sum_promptor.execute(data)
```

#### 输出格式

```python
# 返回摘要提示词列表
[
    {
        "role": "system",
        "content": "You are an intelligent assistant. Summarize the content provided below..."
    },
    {
        "role": "user",
        "content": "Question: 请总结以下内容"
    }
]
```

### 3. QueryProfilerPromptor - 查询分析器

用于分析查询的复杂度和特征，帮助优化RAG管道。

#### 基本使用

```python
from sage.libs.rag.promptor import QueryProfilerPromptor

# 配置元数据
config = {
    "metadata": "The dataset consists of multiple chunks of information from Fortune 500 companies",
    "chunk_size": 1024
}

profiler = QueryProfilerPromptor(config)

# 分析查询
query = "特朗普是如何赚到第一个100万美元的？"
result = profiler.execute(query)
```

#### 期望的分析结果

```json
{
  "need_joint_reasoning": true,
  "complexity": "High",
  "need_summarization": true, 
  "summarization_length": 150,
  "n_info_items": 3
}
```

## 完整使用示例

### RAG问答流水线

```python
from sage.libs.rag.promptor import QAPromptor, QueryProfilerPromptor

# 1. 初始化组件
config = {}
qa_promptor = QAPromptor(config, enable_profile=True)
profiler = QueryProfilerPromptor({
    "metadata": "企业财务报告数据库",
    "chunk_size": 1024
})

# 2. 查询分析
query = "苹果公司2023年Q4的营收情况如何？"
profile_result = profiler.execute(query)
print("查询分析结果:", profile_result)

# 3. 检索相关文档（模拟）
retrieved_docs = [
    "苹果公司2023年第四季度营收达到895亿美元...",
    "相比2022年同期，苹果Q4营收增长了2.1%...",
    "iPhone销售额在Q4占总营收的52%..."
]

# 4. 生成问答提示词
qa_data = (query, retrieved_docs)
qa_result = qa_promptor.execute(qa_data)

print("生成的提示词:")
for msg in qa_result[1]:
    print(f"{msg['role']}: {msg['content'][:100]}...")
```

### 摘要生成流水线

```python
from sage.libs.rag.promptor import SummarizationPromptor

# 初始化摘要生成器
sum_promptor = SummarizationPromptor({})

# 长文本摘要
long_documents = [
    "2023年人工智能领域取得了重大突破，ChatGPT的发布标志着大语言模型时代的到来...",
    "各大科技公司纷纷投入AI研发，Google发布了Bard，百度推出了文心一言...",
    "AI技术在各行各业都有应用，从医疗诊断到自动驾驶，从金融风控到教育辅导..."
]

sum_data = ("总结2023年AI发展", long_documents)
sum_result = sum_promptor.execute(sum_data)

print("摘要提示词:", sum_result[0]['content'])
```

### 多模式组合使用

```python
class RAGPipeline:
    def __init__(self):
        self.qa_promptor = QAPromptor({}, enable_profile=True)
        self.sum_promptor = SummarizationPromptor({})
        self.profiler = QueryProfilerPromptor({
            "metadata": "综合知识库",
            "chunk_size": 1024
        })
    
    def process_query(self, query, documents, use_summarization=False):
        # 1. 分析查询特征
        profile = self.profiler.execute(query)
        
        # 2. 根据分析结果决定是否需要摘要
        if use_summarization or self._need_summarization(profile):
            # 先生成摘要
            sum_prompt = self.sum_promptor.execute((
                f"请摘要以下与'{query}'相关的内容", 
                documents
            ))
            # 这里可以调用LLM获取摘要结果
            summarized_docs = ["摘要后的内容..."]  # 模拟摘要结果
            final_docs = summarized_docs
        else:
            final_docs = documents
        
        # 3. 生成最终的QA提示词
        qa_prompt = self.qa_promptor.execute((query, final_docs))
        
        return {
            'profile': profile,
            'final_prompt': qa_prompt,
            'used_summarization': use_summarization
        }
    
    def _need_summarization(self, profile):
        # 根据profile结果判断是否需要摘要
        return profile[0].get('content', {}).get('need_summarization', False)

# 使用示例
pipeline = RAGPipeline()
result = pipeline.process_query(
    "什么是量子计算？",
    ["量子计算相关文档1", "量子计算相关文档2"],
    use_summarization=True
)
```

## 配置选项

### QAPromptor配置

```python
config = {
    # 自定义提示词模板
    'template': '''自定义的Jinja2模板内容''',
    
    # 其他配置项...
}

# enable_profile参数控制是否启用数据记录
qa_promptor = QAPromptor(config, enable_profile=True)
```

### QueryProfilerPromptor配置

```python
config = {
    'metadata': '数据集描述信息',
    'chunk_size': 1024,  # 分块大小
    # 其他元数据...
}
```