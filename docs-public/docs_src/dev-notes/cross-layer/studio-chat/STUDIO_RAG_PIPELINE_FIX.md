# SAGE Studio RAG Pipeline 生成格式修复

## 问题描述

用户通过 SAGE Studio 的聊天界面创建 RAG pipeline 时，虽然界面显示运行正常，但生成的 pipeline **不符合 SAGE 的 dataflow 范式**。

### 具体表现

1. **Visual Pipeline 格式错误**：LLM/规则生成器生成的节点格式使用了 React Flow 的格式（`type: "custom"`, `data: {...}`），而非
   SAGE Studio 的 VisualNode 格式
1. **聊天回复的代码示例错误**：返回的是命令式编程代码，而非 SAGE dataflow API

## 根本原因

### 问题 1：Visual Pipeline 格式不匹配

**错误格式（React Flow 风格）**：

```python
{
    "id": "source-0",
    "type": "custom",  # ❌ 错误：应该是具体的操作符类型
    "position": {"x": 100, "y": 100},
    "data": {
        "label": "数据源",
        "nodeId": "FileSource",  # ❌ 真正的类型在这里
        "config": {...}          # ❌ 配置嵌套在 data 中
    }
}
```

**正确格式（SAGE Studio VisualNode）**：

```python
{
    "id": "source-0",
    "type": "file_source",  # ✅ 直接使用操作符类型（snake_case）
    "label": "数据源",      # ✅ label 在顶层
    "position": {"x": 100, "y": 100},
    "config": {...}         # ✅ config 在顶层
}
```

### 问题 2：Dataflow 范式理解错误

**错误代码示例（命令式）**：

```python
# ❌ 不符合 SAGE dataflow 范式
texts = ['文档1', '文档2']
vectors = embedding.encode_batch(texts)
query_vector = embedding.encode(user_query)
retrieved_docs = retriever.search(query_vector)
response = generator.generate(prompt)
```

**正确代码示例（SAGE Dataflow）**：

```python
# ✅ 符合 SAGE dataflow 范式
env.from_source(QuestionSource)
   .map(Retriever)
   .map(Promptor)
   .map(Generator)
   .sink(TerminalSink)
```

## 修复方案

### 1. 修复 LLMWorkflowGenerator 格式转换

**文件**：`packages/sage-libs/src/sage/libs/agentic/workflow/generators/llm_generator.py`

**关键修改**：

- `_convert_to_visual_format()` 方法
- 使用 `_class_to_node_type()` 将类名转换为 snake_case
- 节点类型直接使用操作符类型（如 `"file_source"`）
- 配置放在顶层 `config` 字段
- 连接包含 `sourcePort` 和 `targetPort`

```python
def _class_to_node_type(class_name: str) -> str:
    """将类名转换为节点类型
    例: SimpleRetriever -> simple_retriever
        OpenAIGenerator -> openai_generator
    """
    if not class_name:
        return "unknown"

    # 移除包路径，只保留类名
    class_name = class_name.split(".")[-1]

    # 将 CamelCase 转换为 snake_case
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)
    result = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    return result
```

### 2. 修复 RuleBasedWorkflowGenerator 格式

**文件**：`packages/sage-libs/src/sage/libs/agentic/workflow/generators/rule_based_generator.py`

**关键修改**：

- `_build_visual_pipeline()` 方法的 `add_node()` 函数
- 节点类型直接使用注册的操作符名称（如 `"character_splitter"` 而非 `"simple_splitter"`）
- 移除 `type: "custom"` 和 `data` 嵌套结构
- 添加端口信息到连接

### 3. 节点类型对照表

| 生成器使用的名称                       | 注册表中的名称       | 说明      |
| -------------------------------------- | -------------------- | --------- |
| `SimpleSplitter` → `simple_splitter`   | `character_splitter` | ❌ 需修正 |
| `ChromaRetriever` → `chroma_retriever` | `chroma_retriever`   | ✅ 正确   |
| `QAPromptor` → `qa_promptor`           | `qa_promptor`        | ✅ 正确   |
| `OpenAIGenerator` → `openai_generator` | `openai_generator`   | ✅ 正确   |
| `TerminalSink` → `terminal_sink`       | `terminal_sink`      | ✅ 正确   |
| `FileSource` → `file_source`           | `file_source`        | ✅ 正确   |

## 验证测试

创建了 `/home/shuhao/SAGE/test_rag_pipeline_fix.py` 进行验证：

### 测试结果

```
✅ 格式检查: 通过
  - 6 个节点
  - 5 个连接
  - 所有节点类型正确
  - 所有连接包含端口信息
  - 遵循 Source -> Map -> Sink 范式

✅ 集成测试: 通过
  - 成功转换为 VisualPipeline 对象
  - PipelineBuilder 成功构建 SAGE Pipeline
```

## 后续改进建议

### 1. 完善 RAG 文档内容

检查 `~/.sage/cache/chat/` 索引中的文档，确保：

- 所有 RAG 示例代码使用 dataflow API
- 移除命令式编程的示例
- 强调 `env.from_source().map().sink()` 模式

### 2. 改进 RAG System Prompt

在 `packages/sage-llm-gateway/src/sage/gateway/rag_pipeline.py` 的 `_perform_rag_chat()` 方法中，添加明确指令：

```python
system_instructions = textwrap.dedent(
    """
    You are SAGE 内嵌编程助手。回答用户关于 SAGE 的问题，依据提供的上下文进行解释。

    **重要**：当用户询问如何创建 RAG 或 Pipeline 时：
    - 必须使用 SAGE Dataflow API（env.from_source().map().sink()）
    - 不要使用命令式编程代码
    - 参考 examples/tutorials/L3-libs/rag/simple_rag.py
    """
).strip()
```

### 3. 添加格式验证

在 `WorkflowGenerator.generate()` 方法中添加格式验证：

```python
# 验证生成的 visual_pipeline 格式
for node in result.visual_pipeline.get("nodes", []):
    if node.get("type") == "custom":
        logger.warning("节点类型不应该是 'custom'，应该是具体的操作符类型")
    if "data" in node:
        logger.warning("节点不应该有 'data' 字段，配置应该在顶层 'config' 中")
```

## 相关文件

- `packages/sage-libs/src/sage/libs/agentic/workflow/generators/llm_generator.py`
- `packages/sage-libs/src/sage/libs/agentic/workflow/generators/rule_based_generator.py`
- `packages/sage-studio/src/sage/studio/models/__init__.py` (VisualNode, VisualPipeline)
- `packages/sage-studio/src/sage/studio/services/pipeline_builder.py`
- `packages/sage-studio/src/sage/studio/services/node_registry.py`
- `examples/tutorials/L3-libs/rag/simple_rag.py` (正确示例)

## 参考

- SAGE Dataflow 范式：`docs/dev-notes/package-architecture.md`
- VisualNode 模型：`packages/sage-studio/src/sage/studio/models/__init__.py`
- Node Registry：`packages/sage-studio/src/sage/studio/services/node_registry.py`

## 修复日期

2024-11-22

## 修复人员

GitHub Copilot
