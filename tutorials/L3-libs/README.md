# L3: Libs - 算法库层示例

> 对应 SAGE 包：`sage-libs`

## 📖 层级说明

**Libs** 层提供算法库和工具（与 Kernel 同层）：

- RAG - 检索增强生成
- Agents - 智能体框架
- Embeddings - 向量嵌入
- LLM - 大语言模型集成
- Unlearning - 机器遗忘

## 📚 目录结构

```
L3-libs/
├── rag/            # RAG 应用
├── agents/         # 智能体应用
├── embeddings/     # 嵌入应用
├── llm/            # LLM 应用
└── unlearning/     # 机器遗忘
```

## 🎯 学习路径

### 1️⃣ RAG 应用 (`rag/`)

从简单到完整的 RAG 系统：

- `simple_rag.py` - 简单 RAG 示例
- `qa_local_llm.py` - 本地 LLM 问答
- `qa_no_retrieval.py` - 无检索问答
- `usage_1_direct_library.py` - 直接使用库
- `usage_2_sage_function.py` - SAGE 函数集成
- `usage_3_memory_service.py` - 内存服务集成
- `usage_4_complete_rag.py` - 完整 RAG 系统

### 2️⃣ Agents 应用 (`agents/`)

构建智能体系统：

- `basic_agent.py` - 基础智能体
- `workflow_demo.py` - 工作流演示
- `arxiv_search_tool.py` - arXiv 搜索工具
- `demo_arxiv_search.py` - 搜索演示

### 3️⃣ Embeddings 应用 (`embeddings/`)

向量嵌入和相似度搜索：

- `embedding_demo.py` - 嵌入演示
- `embedding_service_demo.py` - 嵌入服务
- `pipeline_builder_embedding_demo.py` - 管道构建器
- `cross_modal_search.py` - 跨模态搜索

### 4️⃣ LLM 应用 (`llm/`)

大语言模型集成：

- `pipeline_builder_llm_demo.py` - LLM 管道
- `templates_to_llm_demo.py` - 模板演示
- `demo_new_templates.py` - 新模板演示
- `test_real_llm.py` - 真实 LLM 测试

### 5️⃣ Unlearning 应用 (`unlearning/`)

机器遗忘技术：

- `basic_unlearning_demo.py` - 基础演示

## 🎯 学习目标

完成本层示例后，你将掌握：

1. 如何构建 RAG 系统
1. 如何设计智能体
1. 向量嵌入的应用
1. LLM 集成的最佳实践
1. 机器遗忘的基本原理

## ⏭️ 下一步

学完算法库层后，继续学习：

- **L4-middleware/** - 中间件和领域算子
