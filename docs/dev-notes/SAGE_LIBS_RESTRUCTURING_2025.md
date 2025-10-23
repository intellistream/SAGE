# SAGE-Libs 模块重构规范化计划

**日期**: 2025-10-23  
**Issue**: #1040  
**分支**: feature/package-restructuring-1032  
**负责人**: SAGE Team

## 背景

sage-libs 作为 L3 层的算法库和组件集合，当前存在以下问题：

1. **命名不规范**: 
   - `io_utils` 应该改为 `io` (更简洁)
   - `utils` 太通用，应该拆分或重命名

2. **结构混乱**:
   - 各子模块缺少清晰的 `__init__.py` 导出
   - README 文档不完整或缺失
   - 没有统一的模块结构标准

3. **职责不清**:
   - `utils/` 包含杂项功能，没有明确分类
   - `context/` 和 `io/` 有功能重叠
   - `applications/` 似乎是空的或未使用

4. **文档缺失**:
   - 子模块缺少 README.md
   - 缺少使用示例
   - API 文档不完整

## 目标结构

```
sage-libs/
├── src/sage/libs/
│   ├── __init__.py          # 主导出
│   ├── README.md            # 总体说明
│   ├── py.typed
│   │
│   ├── agents/              # ✅ 智能体框架 (Agent Framework)
│   │   ├── __init__.py      # 导出核心类
│   │   ├── README.md        # 子模块文档
│   │   ├── agent.py         # BaseAgent
│   │   ├── runtime/         # 运行时
│   │   ├── planning/        # 规划器
│   │   ├── action/          # 动作执行
│   │   ├── profile/         # 智能体配置
│   │   ├── bots/            # 预定义智能体
│   │   │   ├── answer_bot.py
│   │   │   ├── question_bot.py
│   │   │   ├── searcher_bot.py
│   │   │   └── critic_bot.py
│   │   └── examples.py      # 使用示例
│   │
│   ├── rag/                 # ✅ RAG 系统 (Retrieval-Augmented Generation)
│   │   ├── __init__.py
│   │   ├── README.md
│   │   ├── pipeline.py      # RAG Pipeline
│   │   ├── retrievers/      # 检索器
│   │   ├── generators/      # 生成器
│   │   ├── document_loaders.py
│   │   ├── profiler.py
│   │   └── examples.py
│   │
│   ├── unlearning/          # ✅ 机器遗忘 (Machine Unlearning)
│   │   ├── __init__.py
│   │   ├── README.md
│   │   ├── algorithms/      # 遗忘算法
│   │   │   ├── laplace_unlearning.py
│   │   │   └── gaussian_unlearning.py
│   │   ├── dp_unlearning/   # 差分隐私遗忘
│   │   │   ├── base_mechanism.py
│   │   │   ├── privacy_accountant.py
│   │   │   ├── unlearning_engine.py
│   │   │   └── vector_perturbation.py
│   │   ├── evaluation/      # 评估指标
│   │   └── examples.py
│   │
│   ├── workflow/            # ✨ NEW: 工作流优化 (重命名 workflow_optimizer)
│   │   ├── __init__.py
│   │   ├── README.md
│   │   ├── base.py          # 基础抽象
│   │   ├── constraints.py   # 约束系统
│   │   ├── evaluator.py     # 评估器
│   │   ├── optimizers/      # 优化器实现
│   │   │   ├── __init__.py
│   │   │   ├── greedy.py
│   │   │   ├── parallel.py
│   │   │   └── noop.py
│   │   └── examples.py
│   │
│   ├── io/                  # ✨ RENAME: io_utils → io
│   │   ├── __init__.py
│   │   ├── README.md
│   │   ├── source.py        # 数据源
│   │   ├── sink.py          # 数据接收器
│   │   └── batch.py         # 批处理
│   │
│   ├── context/             # ✅ 上下文管理 (Context Management)
│   │   ├── __init__.py
│   │   ├── README.md
│   │   ├── base.py
│   │   ├── model_context.py
│   │   ├── search_context.py
│   │   └── dialog_context.py
│   │
│   ├── tools/               # ✅ 工具集 (Tools & Utilities)
│   │   ├── __init__.py
│   │   ├── README.md
│   │   ├── base/            # 工具基类
│   │   ├── search/          # 搜索工具
│   │   ├── processing/      # 处理工具
│   │   └── examples.py
│   │
│   ├── integrations/        # ✨ NEW: 第三方集成 (从 utils 迁移)
│   │   ├── __init__.py
│   │   ├── README.md
│   │   ├── openai.py
│   │   ├── milvus.py
│   │   ├── chroma.py
│   │   ├── huggingface.py
│   │   └── openaiclient.py
│   │
│   └── filters/             # ✨ NEW: 过滤器 (从 utils 迁移)
│       ├── __init__.py
│       ├── README.md
│       ├── tool_filter.py
│       ├── evaluate_filter.py
│       ├── context_source.py
│       └── context_sink.py
│
└── tests/                   # 测试目录
    ├── agents/
    ├── rag/
    ├── unlearning/
    ├── workflow/
    ├── io/
    └── ...
```

## 重构步骤

### Phase 1: 目录重命名和重组 ✅

1. **重命名 io_utils → io**
   ```bash
   git mv packages/sage-libs/src/sage/libs/io_utils packages/sage-libs/src/sage/libs/io
   ```

2. **重命名 workflow_optimizer → workflow**
   ```bash
   git mv packages/sage-libs/src/sage/libs/workflow_optimizer packages/sage-libs/src/sage/libs/workflow
   ```

3. **拆分 utils 模块**
   ```bash
   # 创建新目录
   mkdir -p packages/sage-libs/src/sage/libs/integrations
   mkdir -p packages/sage-libs/src/sage/libs/filters
   
   # 移动文件
   git mv packages/sage-libs/src/sage/libs/utils/openai.py packages/sage-libs/src/sage/libs/integrations/
   git mv packages/sage-libs/src/sage/libs/utils/milvus.py packages/sage-libs/src/sage/libs/integrations/
   # ... (其他文件)
   ```

4. **重组 agents 模块**
   ```bash
   mkdir -p packages/sage-libs/src/sage/libs/agents/bots
   git mv packages/sage-libs/src/sage/libs/agents/*_bot.py packages/sage-libs/src/sage/libs/agents/bots/
   ```

### Phase 2: 标准化每个子模块 🔄

对每个子模块执行：

1. **创建/更新 __init__.py**
   - 明确导出列表 (`__all__`)
   - 导入关键类和函数
   - 添加版本信息和文档字符串

2. **创建 README.md**
   - 模块概述
   - 主要功能
   - 快速开始示例
   - API 参考链接

3. **添加 examples.py**
   - 常见用例
   - 最佳实践
   - 集成示例

4. **添加 Layer 标记**
   ```python
   """
   Module: SAGE Agents Framework
   
   Layer: L3 (Core - Algorithm Library)
   
   This module provides...
   """
   ```

### Phase 3: 更新导入和测试 🔄

1. **更新所有导入语句**
   ```bash
   # 查找并替换
   find packages -name "*.py" -exec sed -i 's/from sage.libs.io_utils/from sage.libs.io/g' {} \;
   find packages -name "*.py" -exec sed -i 's/from sage.libs.workflow_optimizer/from sage.libs.workflow/g' {} \;
   ```

2. **运行测试确保无破坏**
   ```bash
   pytest packages/sage-libs/tests/ -v
   ```

3. **更新文档**
   - 更新 README.md
   - 更新 API 文档
   - 更新示例代码

### Phase 4: 清理和优化 ⏳

1. **删除未使用的模块**
   ```bash
   # 如果 applications/ 为空
   rm -rf packages/sage-libs/src/sage/libs/applications
   ```

2. **整合重复代码**
   - 识别重复功能
   - 提取到共享模块
   - 删除冗余代码

3. **性能优化**
   - 优化导入
   - 添加缓存
   - 减少依赖

## 标准化规范

### 每个子模块必须包含

1. **`__init__.py`**
   ```python
   """
   Module Name
   
   Layer: L3 (Core)
   
   Brief description of the module.
   """
   
   from .core import MainClass
   
   __all__ = ["MainClass", "helper_function"]
   __version__ = "0.1.0"
   ```

2. **`README.md`**
   ```markdown
   # Module Name
   
   ## Overview
   
   ## Features
   
   ## Quick Start
   
   ## API Reference
   
   ## Examples
   ```

3. **`examples.py`** (可选但推荐)
   ```python
   """Examples for Module Name."""
   
   def example_basic():
       """Basic usage example."""
       pass
   
   if __name__ == "__main__":
       example_basic()
   ```

### 命名约定

- **模块名**: 小写，使用下划线分隔 (snake_case)
- **类名**: 大驼峰 (PascalCase)
- **函数名**: 小写，使用下划线 (snake_case)
- **常量**: 全大写，下划线分隔 (UPPER_CASE)

### 文档规范

- 所有公共 API 必须有 docstring
- 使用 Google 或 NumPy 风格
- 包含示例代码
- 标注参数类型和返回值

## 验收标准

- [ ] 所有目录符合新结构
- [ ] 每个子模块有 README.md
- [ ] 每个子模块有正确的 __init__.py
- [ ] 所有测试通过
- [ ] 文档更新完成
- [ ] 无导入错误
- [ ] 性能无回退

## 时间线

- **Phase 1**: 2025-10-23 - 目录重命名 (1天)
- **Phase 2**: 2025-10-24~26 - 标准化模块 (3天)
- **Phase 3**: 2025-10-27 - 测试和验证 (1天)
- **Phase 4**: 2025-10-28 - 清理优化 (1天)

## 风险和缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 破坏现有代码 | 高 | 在分支上操作，全面测试 |
| 导入路径变更 | 中 | 批量查找替换，保留兼容层 |
| 测试失败 | 中 | 逐步验证，及时修复 |
| 文档不同步 | 低 | 同步更新文档和代码 |

## 参考

- Issue #1040: sage-libs下面各个组件目前的实现不够规范
- Issue #1037: 规范化智能体工作流的优化器模块
- [Python Package Structure Best Practices](https://docs.python-guide.org/writing/structure/)
