# sage-libs Refiner Cleanup (2026-01-10)

## 问题发现

**isage-refiner 已经作为独立 PyPI 包发布**，但 sage-libs 中仍保留着旧的 Long-Refiner 实现。

### 发现的冗余代码

```
packages/sage-libs/src/sage/libs/foundation/context/compression/
├── refiner.py                          # 旧接口
├── algorithms/
│   ├── long_refiner.py                 # Long-Refiner 实现（应删除）
│   ├── refiner_template.py             # Refiner 模板（应删除）
│   ├── long_refiner_impl/              # 实现细节（应删除）
│   │   └── refiner.py
│   └── simple.py                       # 简单压缩器（可能保留）
└── __pycache__/                        # 编译缓存（应删除）
```

### isage-refiner 状态

**已发布**: `isage-refiner>=0.1.0` (PyPI) **依赖位置**: `packages/sage-middleware/pyproject.toml` **使用位置**:
`packages/sage-middleware/src/sage/middleware/components/sage_refiner/`

### 建议清理操作

#### 1. 删除冗余实现

```bash
cd packages/sage-libs/src/sage/libs/foundation/context/compression

# 删除 Long-Refiner 相关文件
rm -rf algorithms/long_refiner.py
rm -rf algorithms/long_refiner_impl/
rm -rf algorithms/refiner_template.py

# 删除编译缓存
rm -rf algorithms/__pycache__/
rm -rf __pycache__/
```

#### 2. 保留或重构的文件

**保留** (如果是基础工具):

- `algorithms/simple.py` - 如果是简单的文本压缩工具，可以保留

**重构** (如果是接口层):

- `refiner.py` - 如果是 Refiner 抽象接口，应该：
  - 保留基类定义
  - 添加工厂函数指向 isage-refiner
  - 或者完全移除，让用户直接使用 isage-refiner

#### 3. 更新文档

在 `REORGANIZATION_PROPOSAL.md` 中补充：

```markdown
### 已外迁的 Context Compression 组件

- `foundation/context/compression/algorithms/long_refiner.py` → `isage-refiner`
- `foundation/context/compression/algorithms/refiner_template.py` → `isage-refiner`
- 用户应直接使用: `pip install isage-refiner`
```

## 迁移影响评估

### sage-middleware 已适配

✅ sage-middleware 已经依赖 isage-refiner ✅ sage-middleware 通过 `sage_refiner` 模块重导出

### sage-libs 清理后

✅ 减少代码冗余 ✅ 避免维护两份相同的代码 ✅ 用户明确知道应该使用 isage-refiner

### 潜在风险

⚠️ 如果有代码直接从 sage-libs 导入 Long-Refiner，需要更新导入路径：

```python
# ❌ 旧代码
from sage.libs.foundation.context.compression.algorithms.long_refiner import LongRefiner

# ✅ 新代码（通过 sage-middleware）
from sage.middleware.components.sage_refiner import LongRefinerAdapter

# ✅ 或直接使用 isage-refiner
from sage_refiner import LongRefiner  # pip install isage-refiner
```

## 执行计划

1. **搜索依赖** - 查找是否有代码引用这些旧文件
1. **更新引用** - 将所有引用改为 isage-refiner
1. **删除文件** - 移除冗余实现
1. **测试验证** - 运行测试确保功能正常
1. **更新文档** - 记录变更

## 执行时间

建议在 agentic/rag 外迁完成后立即执行，作为 sage-libs 清理的一部分。
