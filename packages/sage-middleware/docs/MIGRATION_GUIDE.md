# NeuroMem 测试迁移指南

## 背景

NeuroMem 已独立为 PyPI 包 `isage-neuromem`，相关的单元测试应该转移到 NeuroMem 仓库。但从 SAGE 视角的集成测试应该保留。

## 迁移原则

### ✅ 应该转移到 NeuroMem 仓库的测试

**原则**：测试 NeuroMem **内部实现细节**的单元测试

1. **NeuroMem 内部组件单元测试** (`unit/components/sage_mem/neuromem/`)

   - `test_faiss_index.py` - FAISS 索引实现细节
   - `test_graph_index.py` - 图索引实现细节
   - `test_index_factory.py` - 索引工厂内部逻辑
   - `test_memory_manager.py` - MemoryManager 内部实现
   - `test_unified_collection_basic.py` - UnifiedCollection 基础功能
   - `test_unified_collection_indexes.py` - UnifiedCollection 索引管理
   - `indexes/test_*.py` - 各种索引的实现细节
   - `services/test_*.py` - 各种 service 的实现细节

1. **NeuroMem 核心功能测试** (`components/sage_mem/`)

   - `test_vdb.py` - VDB Collection 内部实现
   - `test_vdb_collection.py` - VDB Collection 功能测试
   - `test_vdb_statistics.py` - VDB 统计功能
   - `test_graph_collection.py` - Graph Collection 内部实现
   - `test_kv_collection.py` - KV Collection 内部实现
   - `test_manager.py` - MemoryManager 测试

1. **NeuroMem 性能测试**

   - `performance/test_benchmarks.py` - NeuroMem 性能基准测试
   - `manual/benchmark_vdb_backends.py` - VDB 后端性能对比

1. **NeuroMem 文档测试**

   - `unit/services/test_documentation.py` - NeuroMem 服务文档验证
   - `verification/verify_hierarchical_docs.py` - NeuroMem 文档验证

### ⚠️ 需要评估的测试（可能保留作为集成测试）

**原则**：测试 SAGE 如何**使用** NeuroMem 的集成测试

1. **E2E 工作流测试** (`e2e/`)

   - `test_complete_workflows.py` - **建议保留**作为 SAGE-NeuroMem 集成测试
   - 重命名为 `integration/test_neuromem_integration.py`
   - 测试 SAGE 应用如何使用 NeuroMem

1. **服务集成测试** (`integration/services/`)

   - `test_hierarchical_services_integration.py` - **部分保留**
   - `test_partitional_combination_services.py` - **部分保留**
   - `test_services_integration.py` - **部分保留**
   - 建议：精简为测试 SAGE 如何调用 NeuroMem 服务的集成测试

### ✅ 应该保留在 SAGE 的测试

**原则**：测试 SAGE 与外部包的**兼容性和集成**

1. **兼容层测试**

   - `components/sage_db/test_*.py` - SageVDB 兼容层测试（✅ 保留）
   - `components/sage_refiner/test_*.py` - SageRefiner 兼容层测试（✅ 保留）
   - `unit/components/sage_tsdb/test_*.py` - SageTSDB 兼容层测试（✅ 保留）
   - `components/test_extensions_compat.py` - 扩展兼容性测试（✅ 保留，需修复）

1. **Operator 测试**

   - `operators/rag/test_*.py` - RAG operators（✅ 保留）
   - `operators/agentic/test_*.py` - Agentic operators（✅ 保留）
   - `operators/filters/test_*.py` - Filter operators（✅ 保留）
   - `operators/tools/test_*.py` - Tools（✅ 保留）

1. **集成测试**（重构后）

   - 保留测试 SAGE 如何使用 NeuroMem 的集成测试
   - 移动到 `integration/test_neuromem_integration.py`

## 迁移步骤

### 步骤 1：创建目标目录

在 NeuroMem 仓库创建测试目录结构：

```bash
cd /path/to/isage-neuromem
mkdir -p tests/{unit,integration,performance,e2e,manual}
```

### 步骤 2：批量转移文件

```bash
# 在 SAGE 仓库
SAGE_TESTS="packages/sage-middleware/tests"
NEUROMEM_TESTS="/path/to/isage-neuromem/tests"

# 转移单元测试
rsync -av --remove-source-files \
  "$SAGE_TESTS/unit/components/sage_mem/neuromem/" \
  "$NEUROMEM_TESTS/unit/"

# 转移核心功能测试
rsync -av --remove-source-files \
  "$SAGE_TESTS/components/sage_mem/test_*.py" \
  "$NEUROMEM_TESTS/components/"

# 转移性能测试
rsync -av --remove-source-files \
  "$SAGE_TESTS/performance/test_benchmarks.py" \
  "$NEUROMEM_TESTS/performance/"

# 转移文档验证
rsync -av --remove-source-files \
  "$SAGE_TESTS/unit/services/test_documentation.py" \
  "$NEUROMEM_TESTS/unit/"
```

### 步骤 3：重构集成测试

保留并重构以下测试为 SAGE-NeuroMem 集成测试：

```bash
# 重命名并移动
mv "$SAGE_TESTS/e2e/test_complete_workflows.py" \
   "$SAGE_TESTS/integration/test_neuromem_integration.py"

# 精简服务集成测试（只保留从 SAGE 视角的测试）
```

### 步骤 4：更新导入路径

在转移到 NeuroMem 仓库后，需要更新导入路径：

```python
# 从:
from sage.middleware.components.sage_mem.neuromem.memory_collection import VDBMemoryCollection

# 改为:
from neuromem.memory_collection import VDBMemoryCollection
```

### 步骤 5：删除手动测试

这些测试有 fixture 错误，应该删除或修复：

```bash
rm "$SAGE_TESTS/manual/test_pypi_packages.py"
```

## 待修复的测试

### `components/test_extensions_compat.py`

问题：测试内部变量 `_sage_db`, `_sage_tsdb`，但这些变量不是公开 API

解决方案：

1. 移除对内部变量的直接测试
1. 只测试公开 API：`is_sage_db_available()`, `require_sage_db()` 等
1. 使用 mock 测试错误处理逻辑

## 检查清单

- [ ] 在 NeuroMem 仓库创建测试目录
- [ ] 转移单元测试（~30 个文件）
- [ ] 转移核心功能测试（6 个文件）
- [ ] 转移性能测试（2 个文件）
- [ ] 转移文档测试（2 个文件）
- [ ] 重构 E2E 测试为集成测试（1 个文件）
- [ ] 精简服务集成测试（3 个文件 → 保留部分）
- [ ] 更新 NeuroMem 仓库的 CI/CD
- [ ] 更新 SAGE 测试配置，排除已迁移的测试
- [ ] 修复 `test_extensions_compat.py`
- [ ] 删除 `test_pypi_packages.py`

## 预期结果

### SAGE 仓库保留的测试

```
packages/sage-middleware/tests/
├── components/
│   ├── sage_db/               # SageVDB 兼容层测试
│   ├── sage_refiner/          # SageRefiner 兼容层测试
│   └── test_extensions_compat.py  # 扩展兼容性测试（已修复）
├── unit/
│   ├── components/
│   │   ├── sage_tsdb/         # SageTSDB 兼容层测试
│   │   └── sage_mem/
│   │       └── test_service_validation.py  # 保留
│   └── agent/                 # Agent 相关测试
├── operators/                 # 所有 operator 测试
└── integration/
    └── test_neuromem_integration.py  # 重构后的集成测试
```

### NeuroMem 仓库新增的测试

```
isage-neuromem/tests/
├── unit/
│   ├── indexes/               # 各种索引的单元测试
│   ├── services/              # 各种服务的单元测试
│   ├── test_faiss_index.py
│   ├── test_graph_index.py
│   ├── test_index_factory.py
│   ├── test_memory_manager.py
│   ├── test_unified_collection_basic.py
│   └── test_unified_collection_indexes.py
├── components/
│   ├── test_vdb.py
│   ├── test_vdb_collection.py
│   ├── test_vdb_statistics.py
│   ├── test_graph_collection.py
│   ├── test_kv_collection.py
│   └── test_manager.py
├── integration/               # NeuroMem 内部集成测试
│   ├── test_hierarchical_services_integration.py
│   ├── test_partitional_combination_services.py
│   └── test_services_integration.py
├── performance/
│   └── test_benchmarks.py
├── manual/
│   └── benchmark_vdb_backends.py
└── e2e/
    └── test_complete_workflows.py  # NeuroMem 内部 E2E
```

## 注意事项

1. **不要直接删除** - 先转移到 NeuroMem 仓库，验证通过后再从 SAGE 仓库删除
1. **保持 Git 历史** - 使用 `git mv` 而不是 `rm + add`
1. **更新 CI/CD** - 两个仓库都需要更新测试配置
1. **文档同步** - 更新 NeuroMem 和 SAGE 的测试文档

## 参考

- NeuroMem 仓库：https://github.com/intellistream/NeuroMem
- SAGE 架构文档：`docs-public/docs_src/dev-notes/package-architecture.md`
- 独立包策略：`docs-public/docs_src/dev-notes/cross-layer/independent-packages.md`
