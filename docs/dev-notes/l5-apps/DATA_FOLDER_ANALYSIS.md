# examples/data 目录使用分析报告

**Date**: 2024-10-18  
**Author**: SAGE Team  
**Summary**: Data 文件夹分析

---


## 引用统计

### Python 文件引用 (2处)

1. **examples/tutorials/agents/basic_agent.py**
   - 引用: `examples/data/agent_queries_test.jsonl`
   - 用途: Agent 示例的测试查询数据

2. **examples/rag/build_chroma_index.py**
   - 引用: `qa_knowledge_base.txt`, `qa_knowledge_base.pdf`, `qa_knowledge_base.md`, `qa_knowledge_base.docx`
   - 用途: 构建 ChromaDB 索引的示例文档

### 配置文件引用 (15个配置文件，18+处引用)

#### 高频使用的数据文件:

**`examples/data/sample/question.txt`** (5处)
- config.yaml
- config_bm25s.yaml
- config_multiplex.yaml
- config_mixed.yaml
- config_ray.yaml

**`examples/data/queries.jsonl`** (5处)
- config_dense_milvus.yaml
- config_sparse_milvus.yaml
- config_qa_chroma.yaml
- config_rerank.yaml
- config_hf.yaml

**`examples/data/qa_knowledge_base.txt`** (3处)
- config_sparse_milvus.yaml (preload_knowledge_file)
- config_dense_milvus.yaml (注释)
- config_sparse_milvus.yaml (注释)

**Agent 相关:**
- `examples/data/agent_queries.jsonl` - config_agent_min.yaml
- `examples/data/agent_queries_test.jsonl` - basic_agent.py

**其他数据:**
- `qa_knowledge_chromaDB.txt` - config_dense_milvus.yaml
- `qa_knowledge_rag.md` - config_dense_milvus.yaml
- `sample/evaluate.json` - config_refiner.yaml
- `biology_knowledge.txt` - config.yaml (文件不存在!)

## 文件使用状态

### ✅ 活跃使用 (必须保留)
```
examples/data/
├── agent_queries.jsonl          ✅ config_agent_min.yaml
├── agent_queries_test.jsonl     ✅ basic_agent.py
├── queries.jsonl                ✅ 5个配置文件
├── qa_knowledge_base.txt        ✅ 多个配置文件
├── qa_knowledge_base.pdf        ✅ build_chroma_index.py
├── qa_knowledge_base.md         ✅ build_chroma_index.py
├── qa_knowledge_base.docx       ✅ build_chroma_index.py
├── qa_knowledge_chromaDB.txt    ✅ config_dense_milvus.yaml
├── qa_knowledge_rag.md          ✅ config_dense_milvus.yaml
└── sample/
    ├── question.txt             ✅ 5个配置文件
    └── evaluate.json            ✅ config_refiner.yaml
```

### ❓ 可能未使用
```
├── hubei.txt                    ❓ 未找到引用
├── q.txt                        ❓ 未找到引用
└── sample/
    ├── one_question.txt         ❓ 未找到引用
    └── question1.txt            ❓ 未找到引用
```

### 🗂️ 特殊目录

**neuromem_datasets/**
- 包含 `locomo_dataloader.py` 和 `locomo_download.py`
- 这些是数据下载工具，不是数据文件
- 建议: 移动到 `examples/data/` 目录外（如 `tools/` 或单独的示例）

**neuromem_vdb/**
- NeuroMem 向量数据库的持久化数据
- 包含索引、元数据、向量存储等
- 建议: 这是运行时生成的数据，应该在 `.gitignore` 中

## 问题和建议

### 问题 1: 缺失文件
❌ **biology_knowledge.txt** - config.yaml 引用但不存在

### 问题 2: 运行时数据混入
⚠️ **neuromem_vdb/** 目录包含运行时生成的数据库文件
- 应该添加到 `.gitignore`
- 或移动到 `.sage/` 目录

### 问题 3: 工具脚本混入
⚠️ **neuromem_datasets/locomo_*.py** 是工具脚本，不是数据
- 建议移动到 `examples/tutorials/data/` 或独立的工具目录

## 清理建议

### 方案 A: 最小改动
1. 删除未使用的文件: `hubei.txt`, `q.txt`, `sample/one_question.txt`, `sample/question1.txt`
2. 创建缺失文件: `biology_knowledge.txt` (或移除 config.yaml 中的引用)
3. 添加 `.gitignore`: `examples/data/neuromem_vdb/`

### 方案 B: 彻底整理（推荐）
1. 保留核心数据文件在 `examples/data/`
2. 移动工具脚本:
   ```
   neuromem_datasets/locomo_*.py → examples/tutorials/data/loaders/
   ```
3. 移除运行时数据:
   ```
   rm -rf examples/data/neuromem_vdb/
   echo "examples/data/neuromem_vdb/" >> .gitignore
   ```
4. 删除未引用文件
5. 创建 `examples/data/README.md` 说明每个文件的用途

## 目录结构建议

```
examples/data/
├── README.md                    # 数据文件说明
├── agent_queries.jsonl
├── agent_queries_test.jsonl
├── queries.jsonl
├── qa_knowledge_base.txt
├── qa_knowledge_base.pdf
├── qa_knowledge_base.md
├── qa_knowledge_base.docx
├── qa_knowledge_chromaDB.txt
├── qa_knowledge_rag.md
└── sample/
    ├── question.txt
    └── evaluate.json

examples/tutorials/data/
└── loaders/                     # 数据加载工具
    ├── locomo_dataloader.py
    └── locomo_download.py

.sage/                           # 运行时数据（不提交到git）
└── neuromem_vdb/
```

## 总结

**保留文件数**: 12个核心数据文件
**删除建议**: 4个未使用文件 + 1个运行时目录
**移动建议**: 2个工具脚本

`examples/data/` 目录主要为 RAG 和 Agent 示例提供测试数据，是 examples 的重要组成部分，**应该保留**但需要清理。
