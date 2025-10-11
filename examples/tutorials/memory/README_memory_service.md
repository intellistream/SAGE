# MemoryService 示例指南

本目录提供了两个可以直接运行的内存服务示例，展示如何在 SAGE 中使用 `MemoryManager` 和 MemoryService 生态来构建检索增强应用。

## 示例概览

- `rag_memory_service.py`：最小化示例，演示如何加载/创建本地记忆集合并完成插入与检索。
- `rag_memory_pipeline.py`：基于 LocalEnvironment 的完整流水线示例，结合 RAG Promptor 与大模型生成能力。

> 过去的内存服务 demo 脚本已下线，推荐改用以上两个脚本来体验 MemoryService 特性。

## 环境准备

1. 确保已经按照仓库根目录的 `README.md` 配置好 Python 环境。
2. 如果要运行流水线示例，请准备可用的 LLM Key，并在 `examples/config/config_rag_memory_pipeline.yaml` 中填写。

## 快速体验

### 1. 本地内存集合演示

```bash
cd examples/memory
python rag_memory_service.py
```

脚本默认会：

1. 通过 `MemoryManager` 加载或创建名为 `RAGMemoryCollection` 的集合；
2. 使用本地 mock 嵌入初始化 FAISS 索引；
3. 写入一条示例问答并立即执行检索；
4. 在控制台打印格式化后的检索结果。

> 该脚本仅依赖 SAGE 自带模块，无需额外安装第三方库。

### 2. RAG 流水线演示

```bash
cd examples/memory
python rag_memory_pipeline.py
```

流水线将：

1. 读取 `examples/config/config_rag_memory_pipeline.yaml`；
2. 通过 `LocalEnvironment` 注册 `RAGMemoryService`；
3. 根据配置中的问题集合构造批处理源 (`QuestionSource`)；
4. 调用注册服务完成历史检索；
5. 使用 `QAPromptor` 构建提示词并通过 `OpenAIGenerator` 调用模型生成回答；
6. 将回答写回记忆集合，并在控制台打印问答结果。

> 如果生成部分使用的是兼容 OpenAI 的推理服务，请在配置里设置好 `api_key`、`base_url` 等字段。

## 配置说明

示例读取的核心配置位于 `examples/config/config_rag_memory_pipeline.yaml`：

- `rag_config`：控制记忆集合路径、索引维度及后端类型；
- `source`：定义流水线批处理输入，包括问题列表与最大轮数；
- `promptor`：自定义提示词模板，可根据领域需求调整；
- `generator`：配置调用的大模型服务及参数。

可以根据业务需要修改这几个部分，例如变更集合存储位置、替换向量维度、或配置不同的推理服务。

## 代码结构速览

- `RAGMemoryService` (`rag_memory_service.py`)
    - 负责初始化/加载记忆集合；
    - `insert(data, metadata)`：写入新的记忆片段；
    - `retrieve(data)`：根据查询检索历史，并重排为问答友好的格式。
- `rag_memory_pipeline.py`
    - `QuestionSource`：批量产出待回答的问题；
    - `Retriever`：通过环境调用 `RAGMemoryService.retrieve` 获取上下文；
    - `Writer`：将模型回复写回记忆集合；
    - `PrintSink`：统一输出最终问答。

## 常见问题

| 问题 | 说明 |
| --- | --- |
| 检索为空 | 确认集合中已经插入数据，或降低检索阈值 `threshold` |
| 无法调用模型 | 检查 `config_rag_memory_pipeline.yaml` 中的 `api_key`、`base_url` 是否正确 |
| 路径不存在 | 默认集合保存在 `.sage/examples/memory/rag_memory_service`，确保脚本有写入权限 |

## 后续扩展建议

- 将 `rag_memory_service.py` 中的 mock 嵌入替换为正式的模型（例如 sentence-transformers）；
- 将流水线示例接入真实的 MemoryService 微服务集群；
- 配合 `examples/memory/rag_memory_manager.py` 构建更复杂的记忆管理策略。

## 相关链接

- [MemoryService 源码](../../packages/sage-middleware/sage/middleware/services/memory/)
- [流水线配置示例](../config/config_rag_memory_pipeline.yaml)
- [更多内存相关脚本](./rag_memory_pipeline.py)
