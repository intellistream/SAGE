# sage-libs 重组完成总结

**完成时间**: 2026-01-10\
**方案**: A (保守拆分 + 可选依赖)

## ✅ 已完成的外迁

### 1. isage-agentic

- **仓库**: https://github.com/intellistream/sage-agentic
- **提交**: 80fbac2 (initial), 5210a76 (remove sias/intent)
- **大小**: ~1.5M (98 files after removing sias/intent)
- **包含模块**:
  - `agents/` - Planning (ReAct, ToT, hierarchical), Tool selection, Bots, Runtime
  - `workflow/` - Workflow orchestration and optimization
  - `eval/` - Agent evaluation and telemetry
  - `reasoning/` - Reasoning tools for planning
  - `interface/`, `interfaces/`, `registry/` - Protocols and registration system
- **PyPI包名**: `isage-agentic`

### 2. isage-sias

- **仓库**: https://github.com/intellistream/sage-sias
- **提交**: (initial commit)
- **大小**: ~100K (4 Python files)
- **包含模块**:
  - `continual_learner.py` - Continual learning with buffer management
  - `coreset_selector.py` - Coreset selection algorithms
  - `types.py` - Common types and protocols
- **PyPI包名**: `isage-sias`

### 3. isage-intent

- **仓库**: https://github.com/intellistream/sage-intent
- **提交**: 139c1b1
- **大小**: ~104K (8 Python files)
- **包含模块**:
  - `keyword_recognizer.py` - Keyword-based intent recognition
  - `llm_recognizer.py` - LLM-based semantic understanding
  - `classifier.py` - Multi-recognizer classification
  - `catalog.py` - Intent catalog management
  - `factory.py` - Recognizer factory
- **PyPI包名**: `isage-intent`

### 4. isage-finetune (之前已完成)

- **仓库**: https://github.com/intellistream/sage-finetune
- **提交**: 6437c02
- **大小**: ~460K (20 files)
- **PyPI包名**: `isage-finetune`

### 5. isage-amms (之前已完成)

- **仓库**: https://github.com/intellistream/sage-amms
- **提交**: a747bcd
- **大小**: ~2.3M (152 files)
- **PyPI包名**: `isage-amms`

### 6. isage-anns (之前已完成)

- **仓库**: (已存在)
- **PyPI包名**: `isage-anns`

## 📝 SAGE 主仓库更改

### pyproject.toml 更新

```toml
[project.optional-dependencies]
anns = ["isage-anns>=0.1.0"]
amms = ["isage-amms>=0.1.0"]
finetune = ["isage-finetune>=0.1.0"]
agentic = ["isage-agentic>=0.1.0"]
sias = ["isage-sias>=0.1.0"]
intent = ["isage-intent>=0.1.0"]
all = [
    "isage-anns>=0.1.0",
    "isage-amms>=0.1.0",
    "isage-finetune>=0.1.0",
    "isage-agentic>=0.1.0",
    "isage-sias>=0.1.0",
    "isage-intent>=0.1.0",
    ...
]
```

### 删除的目录

- `packages/sage-libs/src/sage/libs/agentic/` (完整目录)
- `packages/sage-libs/src/sage/libs/sias/` (完整目录)
- `packages/sage-libs/src/sage/libs/finetune/` (已替换为兼容层 finetune.py)

### 兼容性策略

**不提供向后兼容** - 用户需要:

1. 卸载旧版本的 sage-libs
1. 安装新版本 + 可选依赖: `pip install 'isage-libs[all]'`
1. 更新导入语句:
   ```python
   # 旧方式（不再支持）
   from sage.libs.agentic import ReActPlanner
   from sage.libs.sias import ContinualLearner
   from sage.libs.intent import KeywordIntentRecognizer

   # 新方式
   from sage_agentic import ReActPlanner
   from sage_sias import ContinualLearner
   from sage_intent import KeywordIntentRecognizer
   ```

## 📦 安装方式

```bash
# 基础安装（不包含外迁的模块）
pip install isage-libs

# 安装特定功能
pip install 'isage-libs[agentic]'
pip install 'isage-libs[sias]'
pip install 'isage-libs[intent]'

# 安装所有功能
pip install 'isage-libs[all]'

# 开发安装
cd packages/sage-libs
pip install -e '.[all]'
```

## 🎯 sage-libs 保留内容

目前 `sage-libs` 保留以下模块（可能进一步整理）:

- `rag/` - RAG相关工具
- `integrations/` - 第三方集成
- `safety/` - 安全相关工具
- `privacy/` - 隐私保护
- `eval/` - 评估工具
- `dataops/` - 数据操作工具
- `foundation/` - 基础工具

## 📊 统计数据

| 包名           | 大小 | 文件数 | 状态      |
| -------------- | ---- | ------ | --------- |
| isage-anns     | -    | -      | ✅ 已完成 |
| isage-amms     | 2.3M | 152    | ✅ 已完成 |
| isage-finetune | 460K | 20     | ✅ 已完成 |
| isage-agentic  | 1.5M | 98     | ✅ 已完成 |
| isage-sias     | 100K | 4      | ✅ 已完成 |
| isage-intent   | 104K | 8      | ✅ 已完成 |

**总计**: 6 个独立包，~4.5M 代码已外迁

## 🔄 下一步

1. **发布到 PyPI**:

   ```bash
   # 使用 sage-pypi-publisher
   cd /path/to/sage-pypi-publisher
   ./publish.sh isage-agentic --test-pypi --auto-bump patch
   ./publish.sh isage-sias --test-pypi --auto-bump patch
   ./publish.sh isage-intent --test-pypi --auto-bump patch
   ```

1. **更新 CI/CD**:

   - 在 GitHub Actions 中添加外迁包的测试
   - 更新 SAGE 的测试以使用新的包名

1. **更新文档**:

   - 更新 `docs-public/` 中的引用
   - 创建迁移指南
   - 更新示例代码

1. **考虑进一步整理** (可选):

   - `rag/`, `integrations/`, `safety/` 等模块是否需要独立？
   - `foundation/` 是否应该作为独立的工具库？

## 📚 相关文档

- 重组提案: `packages/sage-libs/docs/REORGANIZATION_PROPOSAL.md`
- 外迁路线图: `packages/sage-libs/docs/EXTERNALIZATION_ROADMAP.md`
- Agentic 外迁计划: `packages/sage-libs/docs/AGENTIC_EXTERNALIZATION_PLAN.md`

## 🎉 成功标准

- [x] 所有目标包已创建 GitHub 仓库
- [x] 代码已迁移并提交
- [x] SAGE 主仓库已更新
- [x] pyproject.toml 配置正确
- [x] 文档已整理到正确位置
- [ ] PyPI 发布（待完成）
- [ ] CI/CD 更新（待完成）
- [ ] 迁移指南（待完成）
