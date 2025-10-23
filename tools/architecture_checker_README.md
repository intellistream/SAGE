# SAGE 架构合规性检测工具

自动检测代码是否符合 SAGE 系统架构设计规范。

## 🎯 功能特性

### 自动检测项

1. **包依赖规则** - 检查跨包导入是否符合层级架构
   - ✅ 允许向下依赖（高层 → 低层）
   - ❌ 禁止向上依赖（低层 → 高层）
   - ❌ 禁止同层跨包依赖（除非明确允许）

2. **导入路径合规性** - 检查是否使用公共 API
   - ⚠️ 警告直接导入内部模块
   - ✅ 推荐使用包的公共导出

3. **模块结构规范** - 检查包结构
   - 验证 `__init__.py` 存在
   - 检查目录结构完整性

4. **架构标记** - 检查 Layer 标记
   - 验证每个包的 `__layer__` 定义
   - 确保文档与实现一致

## 📦 使用方法

### 1. CI/CD 自动检查（推荐）

GitHub Actions 会在以下情况自动运行：

- **Pull Request**: 仅检查变更的文件
- **Push to main/main-dev**: 检查全部文件

无需额外配置，在 PR 中会自动运行并显示结果。

### 2. 本地手动检查

```bash
# 检查全部文件
python tools/architecture_checker.py

# 仅检查变更的文件（相对于 main 分支）
python tools/architecture_checker.py --changed-only --diff origin/main

# 严格模式（将警告也视为错误）
python tools/architecture_checker.py --strict
```

### 3. Git Pre-commit Hook（推荐开发者使用）

在每次 `git commit` 前自动检查：

```bash
# 安装 hooks
./tools/git-hooks/install.sh

# 现在每次 commit 都会自动检查
git commit -m "your message"

# 如果需要跳过检查
git commit --no-verify -m "your message"
```

## 🏗️ 架构规则

### 层级定义

```
L6: sage-studio, sage-tools      # 接口层
L5: sage-apps, sage-benchmark    # 应用层
L4: sage-middleware              # 领域层
L3: sage-kernel, sage-libs       # 核心层
L2: sage-platform                # 平台层
L1: sage-common                  # 基础层
```

### 依赖规则

#### ✅ 允许的依赖

```python
# 向下依赖 - 高层可以依赖低层
from sage.common import utils          # 任何包 → L1 ✅
from sage.platform import service      # L3-L6 → L2 ✅
from sage.kernel import api            # L4-L6 → L3 ✅
from sage.middleware import operators  # L5-L6 → L4 ✅

# 同层依赖（明确允许的）
from sage.libs import agents           # sage-kernel → sage-libs ✅
```

#### ❌ 禁止的依赖

```python
# 向上依赖 - 低层不能依赖高层
from sage.kernel import api            # 在 sage-common 中 ❌
from sage.middleware import operators  # 在 sage-kernel 中 ❌
from sage.apps import video            # 在 sage-middleware 中 ❌

# 未授权的跨层依赖
from sage.studio import models         # 在 sage-apps 中 ❌
```

### 导入最佳实践

#### ✅ 推荐

```python
# 使用包的公共 API
from sage.kernel.api import LocalEnvironment
from sage.middleware.operators.rag import ChromaRetriever
from sage.libs.agents import LangChainAgentAdapter
```

#### ⚠️ 不推荐（会产生警告）

```python
# 直接导入内部模块
from sage.kernel.runtime.dispatcher import Dispatcher
from sage.middleware.operators.rag.retriever.chroma_retriever import ChromaRetrieverImpl
```

## 📊 报告示例

### 成功示例

```
🔍 开始架构合规性检查...

📝 检查全部 692 个 Python 文件

1️⃣  检查包依赖关系...
2️⃣  检查包结构...
3️⃣  检查 Layer 标记...

================================================================================
📊 架构合规性检查报告
================================================================================

📈 统计信息:
  • 检查文件数: 692
  • 导入语句数: 3,245
  • 非法依赖: 0
  • 内部导入: 12
  • 缺少标记: 0

⚠️  发现 12 个警告:

1. [WARNING] INTERNAL_IMPORT
   文件: packages/sage-apps/src/sage/apps/video/operators.py:15
   问题: 直接导入内部模块: sage.kernel.runtime.communication
   建议: 建议使用包的公共 API 进行导入。

...

================================================================================
✅ 架构合规性检查通过！
================================================================================
```

### 失败示例

```
❌ 发现 3 个架构违规:

1. [ERROR] ILLEGAL_DEPENDENCY
   文件: packages/sage-kernel/src/sage/kernel/service/base.py:5
   问题: 非法依赖: sage-kernel (L3) -> sage-middleware (L4)
   建议: 请检查 PACKAGE_ARCHITECTURE.md 中的依赖规则。L3 层不应该依赖 L4 层的包。

2. [ERROR] ILLEGAL_DEPENDENCY
   文件: packages/sage-common/src/sage/common/utils.py:12
   问题: 非法依赖: sage-common (L1) -> sage-kernel (L3)
   建议: 请检查 PACKAGE_ARCHITECTURE.md 中的依赖规则。L1 层不应该依赖 L3 层的包。

================================================================================
❌ 架构合规性检查失败！
   发现 2 个必须修复的问题
================================================================================
```

## 🔧 高级选项

```bash
# 指定项目根目录
python tools/architecture_checker.py --root /path/to/sage

# 仅检查特定 diff
python tools/architecture_checker.py --changed-only --diff origin/develop

# 严格模式（警告也会导致失败）
python tools/architecture_checker.py --strict

# 组合使用
python tools/architecture_checker.py \
  --root /path/to/sage \
  --changed-only \
  --diff origin/main \
  --strict
```

## 📝 集成到开发流程

### 建议的工作流

1. **开发前** - 安装 pre-commit hook
   ```bash
   ./tools/git-hooks/install.sh
   ```

2. **开发中** - 遵循架构规则
   - 参考 `docs/PACKAGE_ARCHITECTURE.md`
   - 使用公共 API 进行导入
   - 避免向上依赖

3. **提交前** - 自动检查
   - Pre-commit hook 自动运行
   - 修复发现的问题

4. **提交后** - CI 验证
   - GitHub Actions 自动检查
   - PR 中查看检查结果

5. **Review 时** - 关注架构
   - 检查 CI 报告
   - 确保符合架构规范

## ❓ 常见问题

### Q: 为什么我的导入被标记为非法依赖？

A: 检查以下几点：
1. 确认你的包在哪一层（查看 `PACKAGE_ARCHITECTURE.md`）
2. 确认被导入的包在哪一层
3. 检查依赖方向是否正确（只能向下依赖）

### Q: 如何临时跳过检查？

A: 使用 `--no-verify` 标志：
```bash
git commit --no-verify -m "emergency fix"
```

**注意**: 仅在紧急情况下使用，应该尽快修复架构问题。

### Q: 警告会导致 CI 失败吗？

A: 默认情况下不会。只有 ERROR 级别的违规会导致失败。
使用 `--strict` 模式可以让警告也导致失败。

### Q: 如何添加新的检查规则？

A: 编辑 `tools/architecture_checker.py`：
1. 在 `ArchitectureChecker` 类中添加新方法
2. 在 `run_checks()` 中调用新方法
3. 提交 PR 并更新本文档

### Q: 检查器本身有 bug 怎么办？

A: 请提交 Issue 或 PR：
- Issue 标题格式: `[Architecture Checker] 描述问题`
- 包含错误输出和复现步骤
- 如果可能，提供修复方案

## 🤝 贡献指南

欢迎改进架构检查器！

### 添加新的检查项

1. Fork 并 clone 仓库
2. 在 `architecture_checker.py` 中添加检查方法
3. 添加测试用例
4. 更新文档
5. 提交 PR

### 报告问题

如果发现：
- 误报（False Positive）
- 漏报（False Negative）
- 性能问题
- 文档错误

请创建 Issue 并提供详细信息。

## 📚 参考文档

- [SAGE 包架构](../../docs/PACKAGE_ARCHITECTURE.md) - 完整的架构文档
- [贡献指南](../../CONTRIBUTING.md) - 如何参与开发
- [开发者指南](../../docs/DEVELOPER.md) - 开发环境设置

## 📄 License

MIT License - 参见项目根目录的 LICENSE 文件
