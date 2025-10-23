# 架构合规性检测工具 - 快速开始

## 🚀 5 分钟上手

### 1. 首次使用

```bash
# 克隆仓库后，安装 pre-commit hook（可选但推荐）
./tools/git-hooks/install.sh
```

### 2. 日常使用

#### 自动检查（推荐）

提交代码时自动检查：

```bash
git add .
git commit -m "your changes"
# 🔍 自动运行架构检查
```

#### 手动检查

```bash
# 检查全部文件
python tools/architecture_checker.py

# 仅检查变更文件（快速）
python tools/architecture_checker.py --changed-only
```

### 3. 遇到错误时

**示例错误:**

```
❌ [ERROR] ILLEGAL_DEPENDENCY
   文件: packages/sage-kernel/src/sage/kernel/service.py:5
   问题: 非法依赖: sage-kernel (L3) -> sage-middleware (L4)
   建议: L3 层不应该依赖 L4 层的包
```

**如何修复:**

1. 查看 `docs/PACKAGE_ARCHITECTURE.md` 了解层级规则
2. 重构代码，移除非法依赖
3. 或者将功能移到正确的层级

### 4. 跳过检查（紧急情况）

```bash
# 跳过 pre-commit hook
git commit --no-verify -m "emergency fix"
```

⚠️ **注意:** 跳过检查后应尽快修复问题

## 📋 常见场景

### 场景 1: 创建新模块

**正确示例:**

```python
# packages/sage-middleware/src/sage/middleware/operators/my_operator.py
from sage.common import utils          # ✅ L4 -> L1
from sage.kernel.api import Function   # ✅ L4 -> L3
from sage.libs.agents import Agent     # ✅ L4 -> L3
```

**错误示例:**

```python
# packages/sage-kernel/src/sage/kernel/core/executor.py
from sage.middleware import operators  # ❌ L3 -> L4 非法向上依赖
```

### 场景 2: 重构现有代码

1. 运行检查找出违规
2. 分析依赖关系
3. 将功能移到合适的层级
4. 重新检查直到通过

### 场景 3: PR Review

CI 会自动检查，在 PR 页面查看结果：

- ✅ 绿色勾: 架构合规
- ❌ 红色叉: 存在违规，需要修复

## 🎓 学习资源

- **详细文档:** `tools/architecture_checker_README.md`
- **架构规范:** `docs/PACKAGE_ARCHITECTURE.md`
- **实现细节:** `docs/dev-notes/ARCHITECTURE_CHECKER_IMPLEMENTATION.md`

## 💡 最佳实践

1. **开发前:** 安装 pre-commit hook
2. **编码时:** 遵循层级规则，向下依赖
3. **提交前:** 确保检查通过
4. **遇到问题:** 查阅文档，理解规则
5. **不确定时:** 询问团队，避免技术债务

## 🆘 获取帮助

- **Issue:** 发现 bug 或有建议？创建 Issue
- **Discussion:** 使用问题？在 Discussions 提问
- **Review:** 不确定设计？请求 Code Review

---

**记住:** 架构检查是为了保持代码健康，不是为了增加负担。如果规则不合理，欢迎讨论改进！
