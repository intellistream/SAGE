# SAGE L3 独立库 Copilot Instructions 索引

本目录包含 SAGE L3 层级独立 PyPI 库的 Copilot 指令文件。

## 库概览

| 内部包名      | PyPI 包名        | 导入名                    | 文档                                                                             | 描述                                     |
| ------------- | ---------------- | ------------------------- | -------------------------------------------------------------------------------- | ---------------------------------------- |
| sage-rag      | `isage-rag`      | `sage_libs.sage_rag`      | [COPILOT_INSTRUCTIONS_isage-rag.md](COPILOT_INSTRUCTIONS_isage-rag.md)           | RAG 实现 (Loaders, Chunkers, Retrievers) |
| sage-agentic  | `isage-agentic`  | `sage_libs.sage_agentic`  | [COPILOT_INSTRUCTIONS_isage-agentic.md](COPILOT_INSTRUCTIONS_isage-agentic.md)   | Agent 实现 (ReAct, PlanExecute, Reflex)  |
| sage-privacy  | `isage-privacy`  | `sage_libs.sage_privacy`  | [COPILOT_INSTRUCTIONS_isage-privacy.md](COPILOT_INSTRUCTIONS_isage-privacy.md)   | 隐私保护 (DP, 联邦学习, 机器遗忘, PII)   |
| sage-eval     | `isage-eval`     | `sage_libs.sage_eval`     | [COPILOT_INSTRUCTIONS_isage-eval.md](COPILOT_INSTRUCTIONS_isage-eval.md)         | 评估指标/Profiler/Judge                  |
| sage-finetune | `isage-finetune` | `sage_libs.sage_finetune` | [COPILOT_INSTRUCTIONS_isage-finetune.md](COPILOT_INSTRUCTIONS_isage-finetune.md) | 微调训练器和数据加载器                   |
| sage-safety   | `isage-safety`   | `sage_libs.sage_safety`   | [COPILOT_INSTRUCTIONS_isage-safety.md](COPILOT_INSTRUCTIONS_isage-safety.md)     | 安全护栏和检测器                         |

## 版本格式

所有 L3 独立库使用四段式版本号：`0.1.x.y`

- `0` - 主版本（API 不兼容变更）
- `1` - 次版本（功能新增）
- `x` - 修订版本（Bug 修复）
- `y` - 构建版本（小调整）

## 架构原则

### SAGE 侧接口层 (`sage.libs.xxx`)

- 提供抽象基类 (ABC)
- 提供工厂函数 (`create_xxx()`)
- 提供类型定义和数据类
- 提供注册函数 (`register_xxx()`)

### 独立库实现层 (`sage_libs.sage_xxx`)

- 提供具体实现类
- 通过 `_register.py` 自动注册到 SAGE 工厂
- 遵循 L3 层级约束（纯算法，无网络服务）

### L3 层级约束

✅ **允许**:

- sage-common (L1)
- sage-platform (L2)
- Python 标准库
- 纯算法库 (numpy, scipy, torch 等)

❌ **禁止**:

- sage-middleware (L4)
- VDB/Memory 服务 (isage-vdb, isage-neuromem)
- 网络服务 (FastAPI, uvicorn)
- LLM 推理引擎 (vLLM, isagellm) - 通过依赖注入使用

## 使用示例

```python
# 1. 使用接口层（推荐）
from sage.libs.rag import create_loader, create_retriever
from sage.libs.agentic import create_agent
from sage.libs.eval import create_metric

# 2. 直接导入实现（如果需要）
from sage_libs.sage_rag.loaders import PDFLoader
from sage_libs.sage_agentic.agents import ReActAgent
from sage_libs.sage_eval.metrics import BLEUMetric
```

## 安装

```bash
# 安装单个库
pip install isage-rag
pip install isage-agentic
pip install isage-privacy
pip install isage-eval
pip install isage-finetune
pip install isage-safety

# 或安装 sage-libs 并选择可选依赖
pip install isage-libs[rag,agentic,eval]
```

## 相关文档

- [SAGE 主仓库 Copilot Instructions](../../../../.github/copilot-instructions.md)
- [接口层使用指南](../INTERFACE_LAYER_USAGE_GUIDE.md)
- [包架构文档](../../../../docs-public/docs_src/dev-notes/package-architecture.md)
