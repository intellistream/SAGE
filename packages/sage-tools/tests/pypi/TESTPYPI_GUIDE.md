# TestPyPI 使用指南

## 概述

TestPyPI是PyPI的测试环境，用于在正式发布前验证包的发布流程和安装体验。

## 为什么需要TestPyPI

- 🧪 **安全测试**：在不影响正式PyPI的情况下测试发布流程
- 🔍 **验证体验**：模拟真实用户从PyPI安装的完整过程
- 🐛 **发现问题**：提前发现元数据、依赖关系等配置问题
- 📦 **版本管理**：测试版本号和包结构是否正确

## 重要注意事项

### TestPyPI的限制

1. **依赖包缺失**
   - TestPyPI是独立的包索引，不包含所有PyPI的包
   - 许多常用依赖（如`fastapi`、`uvicorn`、`numpy`等）可能不存在
   - 某些包在TestPyPI上可能是错误或过期的版本

2. **错误包示例**
   - `FASTAPI`（全大写）：是一个错误的包，安装会失败
   - 正确的包名应该是`fastapi`（小写）

3. **版本限制**
   - TestPyPI上的包版本可能与正式PyPI不同步
   - 依赖版本约束可能无法满足

## 正确的发布和测试流程

### 1. 发布到TestPyPI

```bash
# 使用sage dev命令发布到TestPyPI
sage dev pypi publish --dry-run

# 或者使用twine直接上传
twine upload --repository testpypi dist/*
```

### 2. 从TestPyPI测试安装

#### ✅ 正确的安装方式

```bash
# 方式1：同时指定TestPyPI和正式PyPI
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            isage

# 方式2：在新的虚拟环境中测试
python -m venv test_env
source test_env/bin/activate  # Windows: test_env\Scripts\activate
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            isage[dev]
```

**参数说明**：
- `--index-url https://test.pypi.org/simple/`：主索引为TestPyPI，SAGE包从这里下载
- `--extra-index-url https://pypi.org/simple/`：备用索引为正式PyPI，依赖包从这里下载

#### ❌ 错误的安装方式

```bash
# 错误1：缺少 --extra-index-url
pip install --index-url https://test.pypi.org/simple/ isage
# 问题：依赖包（如fastapi）无法从TestPyPI获取，安装失败

# 错误2：使用错误的包名
pip install --index-url https://test.pypi.org/simple/ FASTAPI
# 问题：全大写的FASTAPI是错误的包
```

### 3. 验证安装

```bash
# 检查版本
sage --version

# 测试核心功能
python -c "import sage; print(sage.__version__)"

# 运行快速验证
sage dev pypi validate --fast

# 测试示例
cd examples
python agents/agent_workflow_demo.py
```

## 常见错误和解决方案

### 错误1：依赖安装失败

**错误信息**：
```
ERROR: Could not find a version that satisfies the requirement fastapi>=0.115.0
```

**原因**：TestPyPI缺少`fastapi`包

**解决方案**：
```bash
# 添加 --extra-index-url 参数
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            isage
```

### 错误2：错误的包版本

**错误信息**：
```
Downloading FASTAPI-1.0.tar.gz
error: subprocess-exited-with-error
FileNotFoundError: [Errno 2] No such file or directory: 'DESCRIPTION.txt'
```

**原因**：TestPyPI上的`FASTAPI`（全大写）是一个错误的包

**解决方案**：
```bash
# 使用 --extra-index-url 让pip从正式PyPI获取正确的fastapi
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            isage
```

### 错误3：版本冲突

**错误信息**：
```
ERROR: Cannot install isage because these package versions have conflicting dependencies
```

**解决方案**：
1. 检查包的依赖版本约束
2. 确保所有子包版本一致
3. 使用`--no-deps`跳过依赖检查（仅用于测试）：
   ```bash
   pip install --index-url https://test.pypi.org/simple/ \
               --no-deps isage
   # 然后手动安装依赖
   pip install fastapi uvicorn typer rich
   ```

## 发布前检查清单

在发布到TestPyPI前，确保：

- [ ] 所有包版本号已更新
- [ ] pyproject.toml中的依赖关系正确
- [ ] 本地验证通过：`sage dev pypi validate`
- [ ] 构建无错误：`sage dev pypi build`
- [ ] README和文档已更新
- [ ] 变更日志已记录

在TestPyPI测试后，确保：

- [ ] 包能成功安装（使用正确的命令）
- [ ] 核心功能正常工作
- [ ] CLI命令可用
- [ ] 示例代码能运行
- [ ] 文档中的安装说明正确

## 最佳实践

### 1. 使用隔离环境

```bash
# 创建专门用于TestPyPI测试的环境
python -m venv testpypi_test
source testpypi_test/bin/activate

# 测试安装
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            isage

# 测试完成后删除环境
deactivate
rm -rf testpypi_test
```

### 2. 自动化测试脚本

```bash
#!/bin/bash
# test_testpypi_install.sh

set -e

echo "🧪 创建测试环境..."
python -m venv testpypi_env
source testpypi_env/bin/activate

echo "📦 从TestPyPI安装SAGE..."
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            isage[dev]

echo "✅ 验证安装..."
sage --version
python -c "import sage; print(f'SAGE {sage.__version__} 安装成功')"

echo "🧹 清理..."
deactivate
rm -rf testpypi_env

echo "🎉 TestPyPI测试完成！"
```

### 3. 版本管理策略

```bash
# 使用开发版本号进行TestPyPI测试
# 例如：1.0.0rc1, 1.0.0.dev1, 1.0.0a1

# 在pyproject.toml中
version = "1.0.0rc1"  # 候选版本

# 测试通过后，更新为正式版本
version = "1.0.0"
```

## sage dev pypi命令集成

SAGE提供了集成的命令来简化TestPyPI的使用：

```bash
# 发布到TestPyPI
sage dev pypi publish --dry-run

# 命令会自动：
# 1. 构建所有包
# 2. 上传到TestPyPI
# 3. 显示正确的测试安装命令

# 输出示例：
# 🎉 TestPyPI发布成功！
# 📝 从TestPyPI安装测试：
#    pip install --index-url https://test.pypi.org/simple/ \
#                --extra-index-url https://pypi.org/simple/ isage
```

## 总结

TestPyPI是PyPI发布流程中的重要一环，但需要注意：

1. ✅ **始终使用** `--extra-index-url https://pypi.org/simple/`
2. 🧪 **在隔离环境**中测试安装
3. 📝 **记录测试结果**，确保所有功能正常
4. 🚀 **测试通过后**再发布到正式PyPI

遵循这些最佳实践，可以确保SAGE包的发布质量和用户安装体验！
