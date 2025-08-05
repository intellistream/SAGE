# SAGE 快速开始指南

## 🎉 恭喜！您的SAGE核心开发环境已成功安装

### 已安装的核心包：
- ✅ **sage-kernel** - SAGE核心内核功能
- ✅ **sage-dev-toolkit** - 开发工具集
- ✅ **开发工具** - pytest, black, isort, flake8, mypy

### 直接pip安装方式

您现在可以像您希望的那样使用简单的pip命令安装SAGE：

```bash
# 安装核心开发环境（推荐用于日常开发）
pip install -r requirements-core.txt

# 如果需要完整功能（可能有依赖冲突，需要手动解决）
pip install -r requirements-extended.txt
```

### 验证安装

```python
# 测试导入
import sage.kernels
import sage_dev_toolkit

print("SAGE核心环境已就绪！")
```

### 开发工作流

1. **编辑代码**：在 `packages/` 目录下的相应包中进行开发
2. **运行测试**：`pytest packages/sage-kernel/tests/`
3. **代码格式化**：`black packages/sage-kernel/src/`
4. **代码检查**：`flake8 packages/sage-kernel/src/`

### 可选安装扩展包

如果需要middleware和userspace功能：

```bash
# 单独安装（可能需要解决依赖冲突）
pip install -e ./packages/sage-middleware
pip install -e ./packages/sage-userspace
```

### 注意事项

- 核心环境已避免了主要的依赖冲突
- psutil版本警告不影响基本功能
- 如需完整AI/ML功能，可能需要手动解决torch/vllm版本冲突

### 下一步

您的开发环境已经准备就绪！可以开始：
- 编写和运行测试
- 开发新功能
- 使用SAGE的核心API

---

**这正是您想要的：简单的pip install方式，无需复杂的构建脚本！** 🚀
