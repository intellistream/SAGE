# SAGE Examples Testing Tools

## 📋 概述

这个模块提供了用于测试和验证 `examples/` 目录中示例代码的工具集。

## ⚠️ 重要说明：开发环境专用

**这些工具仅在 SAGE 开发环境中可用。**

### 为什么？

Examples 测试工具需要访问 SAGE 项目的 `examples/` 目录。但是：

- 📦 **PyPI 安装**：通过 `pip install isage-tools` 安装时，不包含 `examples/` 目录
- 🔧 **开发安装**：从源码安装 `pip install -e packages/sage-tools` 时，可以访问完整的项目结构

### 设计决策

我们将 Examples 测试工具定位为**开发者工具**，原因如下：

1. **目标用户**：主要服务于 SAGE 的贡献者和维护者
2. **使用场景**：用于 CI/CD、pre-commit hooks、开发过程中的质量检查
3. **依赖关系**：需要访问源代码仓库中的 examples 和测试数据
4. **更新频率**：examples 代码经常变动，不适合打包到 PyPI

## 🚀 安装和使用

### 开发环境设置

```bash
# 1. 克隆 SAGE 仓库
git clone https://github.com/intellistream/SAGE
cd SAGE

# 2. 安装 sage-tools（开发模式）
pip install -e packages/sage-tools[dev]

# 3. 验证安装
sage-dev examples --help
```

### 环境检查

工具会自动检测开发环境，如果环境不满足要求，会给出清晰的提示：

```python
from sage.tools.dev.examples import ExampleTestSuite

try:
    suite = ExampleTestSuite()
except RuntimeError as e:
    # 会得到详细的错误信息和设置指引
    print(e)
```

### 手动设置 SAGE_ROOT

如果您的 SAGE 项目在特殊位置：

```bash
export SAGE_ROOT=/path/to/your/SAGE
sage-dev examples test
```

## 📖 使用指南

### 命令行接口

```bash
# 分析示例结构
sage-dev examples analyze

# 运行快速测试（CI 推荐）
sage-dev examples test --quick

# 测试特定类别
sage-dev examples test --category tutorials
sage-dev examples test --category rag

# 检查中间结果放置
sage-dev examples check

# 详细输出
sage-dev examples test --verbose

# 保存测试结果
sage-dev examples test --output results.json
```

### Python API

```python
from sage.tools.dev.examples import (
    ExampleAnalyzer,
    ExampleTestSuite,
    ensure_development_environment,
    get_development_info,
)

# 检查环境
if ensure_development_environment():
    print("✓ Development environment ready")
    
# 获取环境信息
info = get_development_info()
print(f"Examples directory: {info['examples_dir']}")
print(f"Project root: {info['project_root']}")

# 分析示例
analyzer = ExampleAnalyzer()
examples = analyzer.discover_examples()
print(f"Found {len(examples)} examples")

# 运行测试
suite = ExampleTestSuite()
stats = suite.run_all_tests(
    categories=["tutorials"],
    quick_only=True
)
print(f"Pass rate: {stats['passed'] / stats['total'] * 100:.1f}%")
```

## 🏗️ 架构设计

### 环境检测逻辑

工具按以下优先级查找 examples 目录：

1. **环境变量** `SAGE_ROOT`
2. **向上查找**：从当前工作目录向上查找包含 `examples/` 和 `packages/` 的目录
3. **包位置推断**：从 sage-tools 安装位置推断项目根目录
4. **Git 仓库**：使用 `git rev-parse --show-toplevel` 查找仓库根目录

### 错误处理策略

```python
# 导入时只警告，不失败
import sage.tools.dev.examples  # ⚠️ Warning if not in dev env

# 实际使用时才抛出错误
suite = ExampleTestSuite()  # ❌ RuntimeError with helpful message
```

这样设计的好处：
- ✅ 不会破坏 sage-tools 的普通用户安装
- ✅ 提供清晰的错误信息和解决方案
- ✅ 允许其他模块正常导入

## 🎯 CI/CD 集成

### GitHub Actions

```yaml
name: Examples Tests

on: [push, pull_request]

jobs:
  test-examples:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install SAGE Tools
        run: |
          pip install -e packages/sage-tools[dev]
      
      - name: Run Examples Tests
        run: |
          sage-dev examples test --quick
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: check-examples
        name: Check Examples Quality
        entry: sage-dev examples check
        language: system
        pass_filenames: false
```

## 🔧 开发指南

### 添加新的测试策略

编辑 `strategies.py`：

```python
"new_category": TestStrategy(
    name="new_category",
    timeout=90,
    requires_config=True,
    environment_vars={"CUSTOM_VAR": "value"},
)
```

### 自定义过滤规则

编辑 `filters.py`：

```python
def should_skip_file(file_path: Path, category: str) -> tuple[bool, str]:
    if "experimental" in file_path.name:
        return True, "Experimental features not tested"
    return False, ""
```

## 📊 测试报告

测试结果可以导出为 JSON 格式：

```json
{
  "timestamp": "2025-10-27T10:30:00",
  "statistics": {
    "total": 42,
    "passed": 38,
    "failed": 2,
    "skipped": 2,
    "timeout": 0
  },
  "results": [
    {
      "file_path": "examples/tutorials/hello_world.py",
      "status": "passed",
      "execution_time": 1.23,
      "output": "Hello, World!\\n"
    }
  ]
}
```

## ❓ 常见问题

### Q: 为什么不把 examples 打包到 PyPI？

**A:** 几个原因：
1. Examples 代码库很大，会显著增加包大小
2. Examples 经常更新，不应该绑定到 sage-tools 的发布周期
3. 这些工具主要服务于开发者，而开发者会克隆完整仓库

### Q: 我只是想用 SAGE，不想测试 examples，怎么办？

**A:** 完全没问题！如果您只是使用 SAGE：
```bash
pip install isage  # 或 pip install isage-tools
```

Examples 测试工具只是 sage-tools 的一个**可选开发功能**，不影响正常使用。

### Q: 如何在 Docker 容器中使用？

**A:** 在 Dockerfile 中：
```dockerfile
FROM python:3.11

# Clone SAGE repository
RUN git clone https://github.com/intellistream/SAGE /sage
WORKDIR /sage

# Install in development mode
RUN pip install -e packages/sage-tools[dev]

# Set SAGE_ROOT (optional, auto-detection usually works)
ENV SAGE_ROOT=/sage

# Now you can use examples testing tools
RUN sage-dev examples test --quick
```

### Q: 错误 "Examples directory not found" 怎么办？

**A:** 检查以下几点：
1. ✅ 确认你在 SAGE 项目目录中
2. ✅ 确认 `examples/` 目录存在
3. ✅ 尝试设置 `export SAGE_ROOT=/path/to/SAGE`
4. ✅ 确认是从源码安装：`pip install -e packages/sage-tools[dev]`

## 📝 贡献指南

如果您想改进 Examples 测试工具：

1. Fork SAGE 仓库
2. 创建功能分支
3. 修改 `packages/sage-tools/src/sage/tools/dev/examples/`
4. 添加测试到 `packages/sage-tools/tests/test_examples/`
5. 提交 Pull Request

## 📜 许可证

MIT License - 详见 [LICENSE](../../../../../LICENSE)

---

**总结**：Examples 测试工具是为 SAGE 开发者设计的专业工具，需要完整的开发环境。普通用户通过 PyPI 安装 SAGE 时不需要也不会安装这些工具。
