# sage-libs 外迁执行计划（选项 A）

**日期**: 2026-01-10\
**状态**: 🚧 执行中\
**策略**: 完整外迁（保持架构一致性）

## 📋 执行清单

### 阶段 1: SIAS 架构重构 ⚡ **最高优先级**

**背景**：SIAS 被错误地作为独立模块，实际上是工具选择算法的一个实现。

- [ ] **1.1** 检查 SIAS 当前实现位置

  - 位置：`packages/sage-libs/src/sage/libs/sias/`
  - 状态：只有接口层（`interface/`），无实现

- [ ] **1.2** 删除 sage-libs 中的 `sias/` 目录

  - 原因：架构定位错误，应该在 `agentic/agents/action/tool_selection/`
  - 影响：需要检查是否有外部引用

- [ ] **1.3** 在 isage-agentic 中创建正确的 SIAS 实现

  - 文件：`src/sage/libs/agentic/agents/action/tool_selection/sias_selector.py`
  - 类：`SiasToolSelector(BaseToolSelector)`
  - 算法：使用 `CoresetSelector`（loss/diversity/hybrid 策略）

- [ ] **1.4** 注册到工具选择器 registry

  - 在 `__init__.py` 中：`register_selector("sias", SiasToolSelector)`

### 阶段 2: 外迁 agentic → isage-agentic

**目标**：将 sage-libs/agentic 完全迁移到独立包

- [ ] **2.1** 检查 sage-agentic 仓库状态

  - 仓库：`/home/shuhao/sage-agentic`
  - 当前状态：空骨架（只有目录结构）

- [ ] **2.2** 从 SAGE 主仓库复制接口层

  - 源：`packages/sage-libs/src/sage/libs/agentic/interface/`
  - 目标：`sage-agentic/src/sage/libs/agentic/interface/`

- [ ] **2.3** 检查是否有实现代码需要迁移

  - 检查：`packages/sage-libs/src/sage/libs/agentic/` 除 `interface/` 外的内容
  - 如有：一并迁移到 sage-agentic

- [ ] **2.4** 更新 sage-agentic 的 pyproject.toml

  - 包名：`isage-agentic`（PyPI 名称）
  - 版本：`0.1.0`
  - 依赖：添加必要的依赖（如 `sage-libs`）

- [ ] **2.5** 在 sage-agentic 中添加 SIAS 实现（阶段 1.3）

- [ ] **2.6** 在 sage-libs 中添加 extras 依赖

  ```toml
  [project.optional-dependencies]
  agentic = ["isage-agentic>=0.1.0"]
  ```

- [ ] **2.7** 更新 sage-libs/agentic/ 为兼容层或删除

  - 选项 A：完全删除（推荐，干净）
  - 选项 B：保留 `__init__.py` 作为重导出层

### 阶段 3: 外迁 rag → isage-rag

**目标**：将 sage-libs/rag 完全迁移到独立包

- [ ] **3.1** 检查 sage-rag 仓库状态

  - 仓库：`/home/shuhao/sage-rag`
  - 当前状态：空骨架

- [ ] **3.2** 从 SAGE 主仓库迁移代码

  - 源：`packages/sage-libs/src/sage/libs/rag/`
  - 包含：
    - `chunk.py` - 文本分块
    - `document_loaders.py` - 文档加载
    - `types.py` - 类型定义
    - `interface/` - 接口层

- [ ] **3.3** 更新 sage-rag 的 pyproject.toml

  - 包名：`isage-rag`
  - 版本：`0.1.0`
  - Extras：`[retrieval]`, `[generation]`, `[evaluation]`

- [ ] **3.4** 在 sage-libs 中添加 extras 依赖

  ```toml
  [project.optional-dependencies]
  rag = ["isage-rag>=0.1.0"]
  ```

- [ ] **3.5** 删除或转换 sage-libs/rag/ 为兼容层

### 阶段 4: 清理 sage-libs

**目标**：更新文档和依赖，确保一致性

- [ ] **4.1** 更新 sage-libs/pyproject.toml

  - 添加所有 extras 依赖
  - 添加 `all` extras：`["isage-agentic>=0.1.0", "isage-rag>=0.1.0", ...]`

- [ ] **4.2** 更新 sage-libs/README.md

  - 列出外迁的包
  - 说明如何安装 extras

- [ ] **4.3** 更新文档

  - `REORGANIZATION_PROPOSAL.md` - 标记为已完成
  - 删除或归档过时文档

- [ ] **4.4** 检查外部引用

  - 搜索：`from sage.libs.sias`
  - 更新为：`from sage.libs.agentic.agents.action.tool_selection import sias_selector`

- [ ] **4.5** 运行测试

  - `sage-dev project test --coverage`
  - 确保所有功能正常

### 阶段 5: 发布与验证

- [ ] **5.1** 发布到 TestPyPI

  - `isage-agentic` 到 test.pypi.org
  - `isage-rag` 到 test.pypi.org

- [ ] **5.2** 安装测试

  ```bash
  pip install -i https://test.pypi.org/simple/ isage-agentic
  pip install -i https://test.pypi.org/simple/ isage-rag
  ```

- [ ] **5.3** 在 SAGE CI 中测试

  - 更新 `.github/workflows/*.yml`
  - 添加：`pip install -e packages/sage-libs[all]`

- [ ] **5.4** 发布到正式 PyPI

  - 确认测试通过后发布

## 📊 最终架构

### sage-libs（核心工具包）

**保留模块**：

- `dataops/` - 数据操作
- `safety/` - 安全检查
- `privacy/` - 隐私保护
- `integrations/` - 第三方集成
- `foundation/` - 基础工具
- `anns/` - ANN 接口层（实现在 isage-anns）
- `intent/` - 意图识别（暂时保留，未来可外迁）

**已外迁**：

- ~~`agentic/`~~ → `isage-agentic`（包含 SIAS tool selector）
- ~~`rag/`~~ → `isage-rag`
- ~~`sias/`~~ → 删除（错误架构，已整合到 isage-agentic）
- `anns/` 实现 → `isage-anns`
- `amms/` → `isage-amms`
- `finetune/` → `isage-finetune`

### isage-agentic（Agent 框架）

```
src/sage/libs/agentic/
├── interface/                 # 接口层
│   └── base.py                # 抽象基类
├── agents/                    # Agent 实现
│   ├── runtime/
│   ├── planning/
│   ├── action/
│   │   └── tool_selection/
│   │       ├── keyword_selector.py
│   │       ├── embedding_selector.py
│   │       ├── gorilla_selector.py
│   │       ├── dfsdt_selector.py
│   │       └── sias_selector.py     # ✨ SIAS 正确位置
│   └── bots/
├── workflow/                  # 工作流引擎
└── eval/                      # Agent 评估
```

### isage-rag（RAG 工具链）

```
src/sage/libs/rag/
├── interface/                 # 接口层
├── document_loaders.py        # 文档加载
├── chunk.py                   # 文本分块
├── types.py                   # 类型定义
└── pipeline.py                # 管道编排
```

## 🎯 成功标准

- [ ] SIAS 正确实现为 tool selector
- [ ] isage-agentic 和 isage-rag 可独立安装使用
- [ ] SAGE 通过 extras 依赖外迁包
- [ ] 所有测试通过（本地 + CI）
- [ ] 文档完整更新
- [ ] 发布到 PyPI

## 📝 注意事项

1. **向后兼容**：如需兼容，保留 `__init__.py` 作为重导出层
1. **渐进迁移**：先 TestPyPI，确认无问题再正式发布
1. **文档同步**：确保 docs-public 同步更新
1. **CI 调整**：所有 workflow 都要更新安装命令
1. **依赖管理**：确保 dependencies-spec.yaml 统一版本

## 🔗 相关资源

- SAGE 主仓库：`/home/shuhao/SAGE`
- sage-agentic 仓库：`/home/shuhao/sage-agentic`
- sage-rag 仓库：`/home/shuhao/sage-rag`
- PyPI 发布工具：`/home/shuhao/sage-pypi-publisher`

## 📅 时间估算

- 阶段 1（SIAS 重构）：2-3 小时
- 阶段 2（agentic 外迁）：3-4 小时
- 阶段 3（rag 外迁）：2-3 小时
- 阶段 4（清理文档）：1-2 小时
- 阶段 5（发布验证）：2-3 小时

**总计**：10-15 小时（约 2-3 个工作日）
