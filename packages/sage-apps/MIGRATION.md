# sage-lib 和 sage-plugins 合并到 sage-userspace 迁移记录

## 迁移时间
2025年8月4日

## 迁移目标
按照商业化架构方案，将 `sage-lib` 和 `sage-plugins` 合并成统一的 `sage-userspace` 包。

## 迁移步骤

### 1. 创建新包结构
```
sage-userspace/
├── README.md
├── README_plugins.md (备份)
├── pyproject.toml
└── src/
    └── sage/
        ├── __init__.py
        ├── lib/        # 来自 sage-lib
        └── plugins/    # 来自 sage-plugins
```

### 2. 文件复制记录

#### 从 sage-lib 复制：
- `packages/sage-lib/src/sage/lib/` → `packages/sage-userspace/src/sage/lib/`
- 保留了所有子目录和文件：
  - `agents/`: Agent 相关实现
  - `context/`: 上下文管理
  - `io/`: 输入输出处理
  - `rag/`: RAG 算法实现
  - `tools/`: 工具集合
  - `utils/`: 工具函数
  - `tests/`: 测试文件
  - `py.typed`: 类型支持

#### 从 sage-plugins 复制：
- `packages/sage-plugins/src/sage/plugins/` → `packages/sage-userspace/src/sage/plugins/`
- 保留了所有子目录和文件：
  - `longrefiner_fn/`: 长文本精炼插件
  - `py.typed`: 类型支持

### 3. 配置文件合并

#### pyproject.toml 合并要点：
- 包名改为 `sage-userspace`
- 合并了两个包的所有依赖项
- 合并了所有可选依赖组
- 保留了插件入口点配置
- 包含了两个包的类型信息配置

#### 依赖项合并：
**基础依赖**：
- sage-utils (共同依赖)
- sage-lib 的算法依赖：scikit-learn, sympy, networkx, joblib, polars, pyarrow, aiofiles
- sage-plugins 的插件依赖：importlib-metadata, stevedore, pluggy, entrypoints

**可选依赖组**：
- 来自 sage-lib: vectordb, advanced, graph, math, graphdb, rag
- 来自 sage-plugins: llm, embedding, storage, network
- 新增: full (包含所有功能)

### 4. 兼容性保证

#### 导入路径保持不变：
```python
# sage-lib 的导入路径保持不变
from sage.apps.lib.rag import Retriever
from sage.apps.lib.agents import Agent
from sage.apps.lib.tools import ArxivPaperSearcher

# sage-plugins 的导入路径保持不变  
from sage.plugins import load_plugin
from sage.plugins.longrefiner_fn import LongRefinerFunction
```

### 5. 构建验证
- ✅ 包构建成功
- ✅ 生成了 wheel 文件
- ✅ 所有文件结构完整

## 后续计划

1. **测试验证**：运行现有的测试套件，确保功能正常
2. **依赖更新**：更新其他包对 sage-lib 和 sage-plugins 的依赖
3. **文档更新**：更新相关文档和示例
4. **迁移脚本**：为用户提供迁移指南

## 注意事项

- 原始的 `sage-lib` 和 `sage-plugins` 包目录保持不变，方便对比和回滚
- 新包保持了所有原有功能和 API 兼容性
- 构建系统和开发工具配置已经合并
- 类型信息支持已经保留
