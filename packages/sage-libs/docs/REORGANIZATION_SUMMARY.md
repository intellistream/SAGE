# sage-libs 重组总结

## 🚨 核心问题发现

### 问题 1：逻辑不一致

**逻辑不一致**：

- ✅ Agent 工具（agentic/）已外迁 → `isage-agentic`
- ❌ RAG 工具（rag/）计划保留 → 留在 `sage-libs`

### 问题 2：外迁方式不一致

**方式 A：完全删除 + 单文件兼容层**（推荐）

- ✅ `agentic/` → 删除目录，保留 `agentic.py`
- ✅ `finetune/` → 删除目录，保留 `finetune.py`

**方式 B：保留接口目录**（不推荐，需要清理）

- ⚠️ `anns/` → 仍保留 `anns/interface/` 目录
- ⚠️ `amms/` → 仍保留 `amms/interface/` 目录

### 问题 3：RAG 有完整实现（不只是接口）

RAG 模块包含完整实现代码（不像 anns/amms 只保留接口），更应该外迁

**为什么这是问题**？

| 对比维度  | Agent 工具           | RAG 工具             | 是否相同 |
| --------- | -------------------- | -------------------- | -------- |
| 应用层级  | L3/L4 应用层         | L3/L4 应用层         | ✅ 相同  |
| LLM 依赖  | 强依赖 LLM/Embedding | 强依赖 LLM/Embedding | ✅ 相同  |
| SAGE 耦合 | 松耦合（可独立）     | 松耦合（可独立）     | ✅ 相同  |
| 可复用性  | 可被其他项目使用     | 可被其他项目使用     | ✅ 相同  |
| 独立性    | 不强依赖 kernel      | 不强依赖 kernel      | ✅ 相同  |

**结论**：Agent 和 RAG 应该使用**相同的划分策略**！

## 🎯 推荐方案：方案 A（两者都外迁）

### 为什么选择方案 A？

1. **逻辑一致性**：应用层工具统一处理
1. **按需安装**：用户可选择安装 `isage-agentic` 或 `isage-rag`
1. **独立迭代**：两者可独立发版，不受 SAGE 主版本约束
1. **清晰边界**：sage-libs 只保留真正的基础工具
1. **更好复用**：其他项目可以单独使用 `isage-rag`（不需要依赖整个 sage-libs）

### 最终包结构

```
应用层工具（独立 PyPI 包）：
├── isage-agentic/      # Agent 框架（已完成）
│   ├── planning/
│   ├── tool_selection/
│   ├── runtime/
│   └── bots/
│
├── isage-rag/          # RAG 工具（建议新建）
│   ├── document_loaders/
│   ├── chunk/
│   ├── types/
│   └── pipeline/
│
├── isage-anns/         # ANN 算法（已完成）
├── isage-amms/         # 近似矩阵乘（已完成）
└── isage-finetune/     # 模型微调（已完成）

基础工具层（保留在 sage-libs）：
└── sage-libs/
    ├── dataops/        # 数据操作
    ├── safety/         # 安全检查
    ├── privacy/        # 隐私保护
    ├── foundation/     # 基础工具类
    ├── integrations/   # 第三方集成适配器
    └── ann/            # ANN 接口抽象层
```

### 用户安装体验

```bash
# 最小安装（只要基础工具）
pip install isage-libs

# 需要 Agent 功能
pip install isage-libs[agentic]
# 等同于: pip install isage-libs isage-agentic

# 需要 RAG 功能
pip install isage-libs[rag]
# 等同于: pip install isage-libs isage-rag

# 全部安装
pip install isage-libs[all]
# 等同于: pip install isage-libs isage-agentic isage-rag ...
```

## 📋 具体实施步骤

### 🔥 优先级 0：清理已外迁模块（立即执行，1-2 小时）

**问题**：`anns/` 和 `amms/` 保留了接口目录，应该统一改为单文件兼容层

#### 0.1 清理 ANNS

```bash
# 删除接口目录
rm -rf packages/sage-libs/src/sage/libs/anns/

# 创建单文件兼容层
cat > packages/sage-libs/src/sage/libs/anns.py << 'EOF'
"""ANNS compatibility layer - use isage-anns package."""
import warnings
warnings.warn(
    "sage.libs.anns is deprecated. Install 'isage-anns' instead.",
    DeprecationWarning,
    stacklevel=2,
)
try:
    from isage_anns import *  # noqa: F401, F403
except ImportError as e:
    raise ImportError(
        "Install: pip install isage-anns"
    ) from e
EOF
```

#### 0.2 清理 AMMS（同理）

### 1. 创建 isage-rag 仓库

```bash
gh repo create intellistream/sage-rag --public --description "RAG tools for SAGE and beyond"
cd ../sage-rag
mkdir -p src/sagerag tests docs
```

### 2. 迁移代码

```bash
# 复制 RAG 代码
cp -r ../SAGE/packages/sage-libs/src/sage/libs/rag/* src/sagerag/

# 更新 imports（批量替换）
find src/sagerag -name "*.py" -exec sed -i 's/from sage\.libs\.rag/from sagerag/g' {} \;
find src/sagerag -name "*.py" -exec sed -i 's/import sage\.libs\.rag/import sagerag/g' {} \;
```

### 3. 创建 pyproject.toml

```toml
[project]
name = "isage-rag"
version = "0.1.0"
description = "RAG (Retrieval-Augmented Generation) tools from SAGE"
dependencies = [
    "sentence-transformers>=2.0.0",
    "transformers>=4.30.0",
]

[project.optional-dependencies]
retrieval = ["chromadb>=0.4.0", "pymilvus>=2.3.0"]
generation = ["openai>=1.0.0"]
evaluation = ["rouge-score>=0.1.0", "bert-score>=0.3.0"]
all = ["isage-rag[retrieval,generation,evaluation]"]
```

### 4. 更新 SAGE 主仓库

**删除原目录**：

```bash
cd ../SAGE
rm -rf packages/sage-libs/src/sage/libs/rag/
```

**添加兼容层**（可选）：

```python
# packages/sage-libs/src/sage/libs/rag.py
import warnings
warnings.warn(
    "sage.libs.rag is deprecated. Use 'isage-rag' package instead:\n"
    "  pip install isage-rag\n"
    "  from sagerag import TextLoader, CharacterSplitter",
    DeprecationWarning,
    stacklevel=2
)
```

**更新 sage-libs pyproject.toml**：

```toml
[project.optional-dependencies]
rag = ["isage-rag>=0.1.0"]
agentic = ["isage-agentic>=0.1.0"]
all = ["isage-rag>=0.1.0", "isage-agentic>=0.1.0"]
```

**更新 middleware 导入**：

```python
# packages/sage-middleware/src/sage/middleware/operators/rag/__init__.py
# 从新包导入
try:
    from sagerag import (
        TextLoader, PDFLoader, DocxLoader, MarkdownLoader,
        CharacterSplitter, SentenceTransformersTokenTextSplitter,
        RAGDocument, RAGQuery, RAGResponse,
        RAGPipeline,
    )
except ImportError as e:
    raise ImportError(
        "RAG operators require isage-rag package. Install with:\n"
        "  pip install isage-rag\n"
        "or: pip install isage-libs[rag]"
    ) from e
```

### 5. 更新文档

- `packages/sage-libs/README.md` - 说明 RAG 已外迁
- `docs-public/docs_src/tutorials/advanced/advanced-rag.md` - 更新导入路径
- `examples/tutorials/L4-middleware/rag/examples.py` - 更新示例代码

### 6. 测试验证

```bash
# 测试 isage-rag 独立包
cd ../sage-rag
pytest tests/

# 测试 SAGE 集成
cd ../SAGE
pip install -e packages/sage-libs[rag]
pytest packages/sage-middleware/tests/operators/rag/
```

## 🕒 时间估算

- 创建仓库 + 迁移代码：0.5 天
- 更新 SAGE 导入：0.5 天
- 更新文档 + 示例：0.5 天
- 测试验证：0.5 天

**总计**：2 天完成

## ❓ 备选方案 B（不推荐）

**如果选择保留 RAG**：

- 需要撤销 agentic 的外迁（把代码移回 sage-libs）
- 理由必须是"两者都是核心功能，不应外迁"
- 缺点：包体积大，用户无法按需安装

## �� 下一步决策

请选择：

- **A. 外迁 RAG（推荐）** → 执行上述实施步骤
- **B. 保留 RAG** → 需要撤销 agentic 外迁

如果选择 A，我可以立即开始执行步骤 1-6。
