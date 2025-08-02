# SAGE 一键自动化测试系统

这个测试系统为 SAGE 项目提供了完整的自动化测试解决方案，包括环境管理、智能测试、并行执行和详细报告。

## 🚀 快速开始

### 1. 基本使用

```bash
# 默认模式：环境检查 + 快速测试 + 报告
./quick_test.sh

# 或使用 Python 版本
python run_all_tests.py
```

### 2. 交互式菜单（推荐新手使用）

```bash
./quick_test.sh --interactive
```

### 3. 常用测试模式

```bash
# 快速测试（适合日常开发）
./quick_test.sh --quick

# 完整测试套件（适合提交前）
./quick_test.sh --full --workers 8

# 智能差异测试（仅测试修改相关的代码）
./quick_test.sh --diff

# GitHub Actions 本地模拟
./quick_test.sh --github
```

## 📋 功能特性

### 🔧 自动化测试功能
- ✅ **智能测试发现**: 自动扫描项目中的所有测试文件
- ✅ **并行执行**: 支持多核并行测试，提升执行效率
- ✅ **差异化测试**: 基于 git diff 只运行相关测试
- ✅ **环境管理**: 自动检查和设置 Python 虚拟环境
- ✅ **详细日志**: 为每个测试文件生成独立的执行日志

### 📊 报告和监控
- ✅ **测试报告**: 自动生成 Markdown 格式的详细报告
- ✅ **性能统计**: 显示执行时间、成功率等指标
- ✅ **环境信息**: 记录系统环境和依赖状态
- ✅ **实时进度**: 测试执行时显示实时进度条

### 🎭 GitHub Actions 集成
- ✅ **本地模拟**: 使用 act 工具本地运行 GitHub Actions
- ✅ **工作流验证**: 在提交前验证 CI/CD 流程
- ✅ **多工作流支持**: 支持项目中的所有工作流文件

## 📂 文件结构

```
SAGE 测试系统/
├── run_all_tests.py          # Python 主测试脚本（功能最全）
├── quick_test.sh             # Bash 快捷脚本（快速启动）
├── test_config.toml          # 测试配置文件
├── scripts/test_runner.py    # 核心测试运行器
├── test_logs/                # 测试执行日志
├── test_reports/             # 测试报告输出
└── test_env/                 # Python 虚拟环境
```

## 🛠️ 详细使用说明

### Python 脚本 (run_all_tests.py)

这是功能最完整的脚本，提供所有高级功能：

```bash
# 查看所有选项
python run_all_tests.py --help

# 各种测试模式
python run_all_tests.py --quick              # 快速测试
python run_all_tests.py --full --workers 8   # 完整测试，8个并发
python run_all_tests.py --diff               # 智能差异测试
python run_all_tests.py --github-actions     # GitHub Actions 模拟
python run_all_tests.py --report             # 仅生成报告
python run_all_tests.py --interactive        # 交互式菜单

# 环境管理
python run_all_tests.py --setup              # 设置测试环境
```

### Bash 脚本 (quick_test.sh)

轻量级脚本，适合快速操作：

```bash
# 查看帮助
./quick_test.sh --help

# 基本操作
./quick_test.sh --check          # 环境检查
./quick_test.sh --setup          # 设置环境
./quick_test.sh --quick          # 快速测试
./quick_test.sh --full           # 完整测试
./quick_test.sh --diff           # 差异测试
./quick_test.sh --github         # GitHub Actions 模拟
./quick_test.sh --report         # 生成报告
./quick_test.sh --interactive    # 交互式菜单

# 自定义并发数
./quick_test.sh --full --workers 16
```

## ⚙️ 配置说明

### 测试配置 (test_config.toml)

配置文件包含以下主要部分：

```toml
[test_suites]
# 定义不同的测试套件
quick_tests = ["sage/cli/tests/test_config_manager.py", ...]
core_tests = ["sage/core/", "sage/cli/", ...]

[test_config]
# 测试执行配置
default_workers = 4
max_workers = 8
test_timeout = 300

[paths]
# 路径配置
project_root = "."
venv_path = "./test_env"
test_logs_dir = "./test_logs"
```

### 环境要求

- **Python**: 3.11+
- **关键依赖**: pytest, torch, ray, fastapi
- **可选工具**: act (GitHub Actions 本地运行)
- **系统**: Linux/macOS (推荐)

## 📊 测试报告

测试完成后会在 `test_reports/` 目录下生成详细报告：

```
test_reports/
├── test_report_20250802_143022.md    # Markdown 报告
└── test_report_20250802_143022.json  # JSON 数据
```

报告包含：
- 📊 执行概览（成功率、耗时等）
- 🏗️ 环境信息（Python版本、依赖状态）
- 📈 性能统计（CPU、内存使用）
- 📋 推荐操作（如何修复失败的测试）

## 🔍 日志查看

每个测试文件都有独立的日志：

```bash
# 查看所有日志文件
ls -la test_logs/

# 查看特定测试的日志
cat test_logs/sage_cli_tests_test_config_manager.py.log

# 查看最新的日志
ls -lt test_logs/*.log | head -5
```

## 🎯 使用场景

### 日常开发流程

```bash
# 1. 修改代码后，快速检查
./quick_test.sh --diff

# 2. 提交前完整验证
./quick_test.sh --full

# 3. 查看测试报告
cat test_reports/test_report_*.md
```

### CI/CD 集成

```bash
# 本地验证 GitHub Actions
./quick_test.sh --github

# 模拟完整 CI 流程
python run_all_tests.py --github-actions
```

### 性能优化

```bash
# 使用更多并发进程
./quick_test.sh --full --workers 16

# 监控资源使用
htop  # 查看 CPU 使用
```

## 🚨 故障排除

### 常见问题

1. **虚拟环境问题**
   ```bash
   ./quick_test.sh --setup  # 重新设置环境
   ```

2. **依赖缺失**
   ```bash
   source test_env/bin/activate
   pip install -e .
   ```

3. **测试失败**
   ```bash
   # 查看具体错误
   cat test_logs/failed_test.log
   
   # 重新运行单个测试
   pytest sage/specific/test_file.py -v
   ```

4. **Docker 连接问题**
   ```bash
   # 检查 Docker 状态
   docker info
   
   # 启动 Docker 服务
   sudo systemctl start docker
   ```

### 性能调优

- **调整并发数**: 根据 CPU 核心数设置 `--workers`
- **内存限制**: 在 `test_config.toml` 中配置内存限制
- **排除慢测试**: 在配置中添加排除模式

## 🤝 贡献指南

如需扩展测试系统功能：

1. 修改 `run_all_tests.py` 添加新功能
2. 更新 `test_config.toml` 添加配置选项
3. 更新此 README 文档
4. 添加相应的测试用例

## 📞 支持

如有问题请：
1. 查看 `test_logs/` 中的详细日志
2. 运行 `./quick_test.sh --check` 检查环境
3. 使用 `./quick_test.sh --interactive` 交互式诊断

---

🎉 **开始使用 SAGE 一键自动化测试系统，提升你的开发效率！**
