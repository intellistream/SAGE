# SAGE Framework 测试工具集

> ⚠️ **重要通知**: 本目录下的测试脚本正在逐步迁移到统一的 `sage dev test` 命令。
> 
> **推荐使用**: `sage dev test --test-type unit` 或 `sage dev test --test-type integration`
> 
> **详细信息**: 请查看 [MIGRATION.md](MIGRATION.md) 了解迁移指南和功能对比

本目录包含 SAGE Framework 的统一测试工具集，提供多种测试方式和配置选项。

## 📁 文件说明

### 🔧 主要测试工具

#### `run_tests.py` - 集成测试运行器
**Python 集成测试入口**，支持多种测试模式和配置。

```bash
# 基本使用
python run_tests.py --all                      # 测试所有包
python run_tests.py --quick                    # 快速测试主要包
python run_tests.py --packages sage-libs       # 测试指定包

# 测试类型
python run_tests.py --unit                     # 单元测试
python run_tests.py --integration              # 集成测试
python run_tests.py --performance              # 性能测试

# 高级选项
python run_tests.py --jobs 8 --timeout 600    # 8并发，10分钟超时
python run_tests.py --verbose --report test_report.txt
python run_tests.py --diagnose                 # 只运行诊断
```

#### `test_all_packages.sh` - 完整包测试脚本
**Bash 脚本**，用于全面测试所有 SAGE 包。

```bash
# 基本使用
./test_all_packages.sh                         # 测试所有包
./test_all_packages.sh sage-libs sage-kernel   # 测试指定包

# 配置选项
./test_all_packages.sh -j 8 -t 600             # 8并发，10分钟超时
./test_all_packages.sh --verbose               # 详细输出
./test_all_packages.sh --summary               # 摘要模式
./test_all_packages.sh --continue-on-error     # 遇错继续
./test_all_packages.sh --failed                # 重跑失败的测试
```

#### `quick_test.sh` - 快速测试脚本
**轻量级快速测试**，适合日常开发验证。

```bash
./quick_test.sh                                # 快速测试
./quick_test.sh --verbose                      # 详细输出
./quick_test.sh --summary                      # 摘要模式
```

**特性**：
- 🎯 只测试主要包 (sage-common, sage-kernel, sage-libs, sage-middleware)
- 🚀 3并发执行
- ⚡ 2分钟超时
- 🛡️ 自动容错

### 🔍 诊断工具

#### `diagnose_sage.py` - SAGE 安装诊断
检查 SAGE 安装状态和模块可用性。

```bash
python diagnose_sage.py
```

**检查项目**：
- 基础 sage 包导入
- 各子模块 (kernel, libs, middleware) 状态
- 命名空间包结构
- 安装路径和版本信息

#### `check_packages_status.sh` - 包状态检查
检查所有包的版本、依赖等信息。

```bash
./check_packages_status.sh
```

**检查项目**：
- 包存在性和结构
- 版本信息提取
- 依赖关系验证
- pyproject.toml 配置

## 🚀 推荐使用流程

### 日常开发验证
```bash
# 1. 快速检查
./quick_test.sh --summary

# 2. 如有问题，详细诊断
python run_tests.py --diagnose
```

### 全面测试
```bash
# 1. 状态检查
python diagnose_sage.py
./check_packages_status.sh

# 2. 单元测试
python run_tests.py --unit --verbose

# 3. 集成测试
python run_tests.py --integration

# 4. 完整测试（CI用）
./test_all_packages.sh --continue-on-error --summary
```

### CI/CD 环境
```bash
# 快速 CI 检查
python run_tests.py --quick --unit --jobs 4

# 完整 CI 测试
./test_all_packages.sh \
    --jobs 4 \
    --timeout 300 \
    --continue-on-error \
    --summary
```

## 🔧 配置说明

### 默认配置
- **并行任务数**: 4
- **超时时间**: 300秒 (5分钟)
- **测试类型**: unit
- **错误处理**: 继续执行

### 环境要求
- Python 3.8+
- pytest (用于某些包的测试)
- bash (用于 shell 脚本)

### 日志和报告
测试结果保存在项目根目录的 `.testlogs/` 文件夹中：
- `test_run_TIMESTAMP.log` - 主测试日志
- `PACKAGE_TIMESTAMP.log` - 各包详细日志
- `test_summary_TIMESTAMP.txt` - 测试摘要报告

## 🔗 与现有测试的集成

### 各包的测试运行器
工具会自动发现并使用各包的测试运行器：

- **sage-libs**: `packages/sage-libs/tests/run_tests.py`
- **sage-kernel**: `packages/sage-kernel/tests/` (pytest)
- **sage-middleware**: `packages/sage-middleware/tests/` (pytest)

### 测试标记支持
支持 pytest 标记系统：
- `unit` - 单元测试
- `integration` - 集成测试
- `performance` - 性能测试
- `slow` - 耗时测试
- `external` - 外部依赖测试

## 🆘 故障排除

### 常见问题

1. **包导入失败**
   ```bash
   python diagnose_sage.py  # 检查安装状态
   ```

2. **测试超时**
   ```bash
   ./test_all_packages.sh -t 600  # 增加超时时间
   ```

3. **并发问题**
   ```bash
   ./test_all_packages.sh -j 1  # 减少并发数
   ```

4. **查看详细错误**
   ```bash
   python run_tests.py --verbose --packages FAILED_PACKAGE
   ```

### 调试模式
```bash
# 详细输出 + 单包测试
python run_tests.py --packages sage-libs --verbose --unit

# 收集测试但不运行
python -m pytest packages/sage-libs/tests --collect-only
```

## 📈 测试覆盖率

部分工具支持生成覆盖率报告：
```bash
# HTML 覆盖率报告
cd packages/sage-libs/tests
python run_tests.py --html-coverage

# 终端覆盖率报告
python run_tests.py --coverage
```

覆盖率报告将保存在各包的 `htmlcov/` 目录中。
