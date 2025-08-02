# SAGE 一键环境安装和测试

## 🚀 快速开始

只需要一个命令，即可从头安装环境并运行完整测试：

```bash
python one_click_setup_and_test.py
```

## 📋 这个脚本会做什么

1. **🗑️ 删除旧环境** - 清理现有的test_env目录和缓存
2. **🐍 创建新环境** - 创建全新的Python虚拟环境  
3. **📦 安装依赖** - 安装pyproject.toml中的所有依赖包
4. **🧪 运行测试** - 执行完整的测试套件（59个测试文件）
5. **📊 生成报告** - 输出详细的测试报告

## ⚙️ 使用选项

```bash
# 默认模式（4个并行进程）
python one_click_setup_and_test.py

# 使用更多并行进程（推荐）
python one_click_setup_and_test.py --workers 8

# 快速测试模式（仅智能差异测试）
python one_click_setup_and_test.py --quick-test

# 查看帮助
python one_click_setup_and_test.py --help
```

## 💡 使用场景

- **新环境设置** - 第一次设置开发环境
- **环境重置** - 依赖冲突或环境污染时重置
- **CI/CD验证** - 验证项目在干净环境中的安装和测试
- **版本切换** - 切换Python版本后重新设置环境

## ⚠️ 注意事项

- 运行前会提示确认删除现有test_env目录
- 需要Python 3.11+版本
- 首次运行需要下载大量依赖包（约2-3GB）
- 完整测试可能需要5-15分钟，取决于硬件性能

## 📈 输出说明

脚本运行后会生成：
- **测试日志**: `test_logs/` 目录下的详细日志文件
- **测试报告**: `test_reports/` 目录下的Markdown报告
- **虚拟环境**: `test_env/` 目录下的Python环境

## 🔧 后续使用

安装完成后，你可以：

```bash
# 激活环境
source test_env/bin/activate

# 重新运行测试
python scripts/test_runner.py --all

# 智能差异测试（推荐日常使用）
python scripts/test_runner.py --diff

# 查看测试日志
ls -la test_logs/
```

## 📂 其他工具

如需要更多高级功能，可以查看 `testing_archive/` 目录中的完整测试工具集。

---

🎉 **开始使用SAGE一键环境安装和测试，享受简洁高效的开发体验！**
