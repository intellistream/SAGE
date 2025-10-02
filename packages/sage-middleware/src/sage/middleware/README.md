# SAGE Middleware 模块

该包提供 SAGE 框架的中间件组件，当前主要聚焦在 Neuromem 记忆栈及其配套工具。历史文档中提到的独立微服务、注册中心和网络协议尚未在此仓库中实现；本 README 仅覆盖现有代码。

## 目录结构

```
sage/middleware/
├── components/
│   ├── neuromem/               # 记忆栈核心实现
│   ├── sage_db/                # C++ 扩展（可选，默认未启用）
│   └── sage_flow/              # C++ 扩展（可选，默认未启用）
├── utils/                      # 嵌入等通用工具
└── README.md
```

### Neuromem 组件概览

- `memory_manager.py`：负责集合生命周期、懒加载、落盘。
- `memory_collection/`：定义 `BaseMemoryCollection` 及 VDB/KV/Graph 集合实现，其中 VDB 为主流可用组件。
- `search_engine/` 与 `storage_engine/`：分别负责索引与文本/元数据存储，默认通过 FAISS 和本地文件实现。
- `micro_service/`: 提供 `NeuroMemVDB`（脚本友好封装）与 `NeuroMemVDBService`（`BaseService` 接口示例）。

### 嵌入工具

`utils/embedding/embedding_model.py` 为统一入口，支持：

- HuggingFace (`method="hf"`)
- OpenAI / Cohere / Bedrock / Jina / Nvidia OpenAI / SiliconCloud
- `mockembedder`（用于测试）

默认将 `HF_ENDPOINT` 指向 `https://hf-mirror.com`，并在模型加载失败时抛出异常，提醒手动切换为 mock 或其他提供商。

### 可选 C++ 扩展

`components/extensions_compat.py` 会在导入时尝试加载 `sage_db` 与 `sage_flow` 扩展：

- 若可用，自动暴露 Python 绑定。
- 若缺失，打印提示并回退到纯 Python 实现。

扩展默认未编译，需要额外安装依赖并运行 `pip install --force-reinstall isage-middleware` 或手动构建。

## 快速体验 Neuromem

```python
from sage.middleware.components.neuromem.micro_service.neuromem_vdb import NeuroMemVDB

vdb = NeuroMemVDB()
vdb.register_collection(
    "demo",
    {
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "dim": 384,
        "description": "Demo collection",
    },
)

vdb.insert("SAGE uses a Python-based memory stack", {"tag": "doc"})
vdb.build_index()
print(vdb.retrieve("What is SAGE memory?", topk=3, with_metadata=True))
```

更多文档请参考 `docs-public/docs_src/middleware/`。
