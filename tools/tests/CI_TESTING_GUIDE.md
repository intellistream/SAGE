# SAGE CI/CD 测试集成指南

## 概述

我们已经成功将pytest测试集成到SAGE框架的CI/CD流程中。现在CI/CD包含以下几个层次的测试：

## 测试架构

### 1. 快速检查 (quick-check) - ci.yml & dev-ci.yml
- **目的**: 快速验证基础功能和代码质量
- **包含内容**:
  - 基础导入测试
  - Issues Manager快速测试
  - 代码质量检查 (flake8, black, isort)
- **运行时间**: 5-15分钟
- **触发条件**: 每次push和PR

### 2. 完整测试 (full-test) - ci.yml
- **目的**: 全面的功能和集成测试
- **包含内容**:
  - 完整的SAGE安装
  - 综合pytest套件 (单元测试 + 集成测试)
  - Issues Manager完整测试
  - 测试报告生成
- **运行时间**: 20-40分钟
- **触发条件**: PR到main分支

### 3. 专门的Pytest CI - pytest-ci.yml
- **目的**: 专业的pytest测试流水线
- **包含内容**:
  - 测试发现和分类
  - 并行测试执行
  - 性能测试
  - 详细测试报告
- **运行时间**: 30-60分钟
- **触发条件**: 测试文件变更、手动触发

## 测试类型

### 单元测试 (Unit Tests)
```bash
# 使用统一测试运行器
python tools/tests/run_tests.py --quick --unit --jobs 4 --timeout 120

# 或直接使用pytest
cd packages/sage-common
python -m pytest tests/ -v --tb=short
```

### 集成测试 (Integration Tests)
```bash
# 运行集成测试
python tools/tests/run_tests.py --quick --integration --jobs 2 --timeout 300

# Issues Manager集成测试
cd tools/tests
bash test_issues_manager.sh --integration
```

### 性能测试 (Performance Tests)
```bash
# 运行性能测试
python tools/tests/run_tests.py --quick --performance --jobs 1 --timeout 600
```

## Issues Manager 测试

我们为 `issues_manager.sh` 创建了全面的自动化测试：

### 测试脚本
- `tools/tests/test_issues_manager.sh` - 完整测试套件
- `tools/tests/quick_test.sh` - 快速验证测试
- `tools/tests/Makefile` - 简化的测试入口

### 测试模式
```bash
# 快速测试 (CI适用)
bash test_issues_manager.sh --quick

# 完整测试
bash test_issues_manager.sh --full

# 集成测试
bash test_issues_manager.sh --integration

# 使用Makefile
make test-quick
make test-full
```

## CI/CD 工作流程

### 开发工作流 (dev-ci.yml)
1. **代码推送到开发分支** → 触发快速测试
2. **包含pytest快速验证** → 基础功能确认
3. **Issues Manager测试** → 工具功能验证

### 生产工作流 (ci.yml)
1. **PR到main分支** → 触发完整测试
2. **全面的pytest测试套件** → 深度质量验证
3. **完整的Issues Manager测试** → 工具集成验证
4. **测试报告生成** → 结果可视化

### 专业测试工作流 (pytest-ci.yml)
1. **测试文件变更** → 自动触发
2. **测试发现** → 识别需要测试的包
3. **并行测试执行** → 单元/集成/性能测试
4. **结果聚合** → 统一报告和PR评论

## 测试配置

### pytest.ini 配置
项目根目录的 `pytest.ini` 包含:
- 测试标记 (markers): unit, integration, slow, performance等
- 测试路径配置
- 警告过滤
- 超时设置

### 包级别配置
每个包 (`packages/sage-*/`) 都有自己的:
- `tests/` 目录
- `pyproject.toml` 或 `setup.cfg` 测试配置
- 独立的pytest配置

## 使用指南

### 开发者日常使用
```bash
# 快速验证代码
make test-quick

# 运行特定包的测试
python tools/tests/run_tests.py --packages sage-common --unit

# 运行Issues Manager测试
cd tools/tests && bash test_issues_manager.sh --quick
```

### CI/CD 触发
- **自动触发**: push到主要分支、PR创建
- **手动触发**: GitHub Actions界面 → Run workflow
- **特定测试**: 使用 pytest-ci.yml 的输入参数

### 测试结果查看
- **GitHub Actions**: 查看workflow运行日志
- **测试报告**: 下载生成的HTML报告
- **PR评论**: 自动生成的测试摘要

## 故障排除

### 常见问题
1. **测试超时**: 检查 `--timeout` 参数设置
2. **导入错误**: 确认包安装正确，检查 PYTHONPATH
3. **Issues Manager测试失败**: 检查GitHub令牌配置

### 调试命令
```bash
# 检查包状态
python tools/tests/run_tests.py --diagnose

# 运行单个测试文件
python -m pytest packages/sage-common/tests/test_specific.py -v

# 生成详细报告
python tools/tests/run_tests.py --quick --unit --verbose --report debug_report.txt
```

## 最佳实践

### 1. 测试编写
- 使用合适的pytest标记 (`@pytest.mark.unit`, `@pytest.mark.integration`)
- 编写清晰的测试文档
- 使用fixture复用测试设置

### 2. CI/CD优化
- 使用缓存加速依赖安装
- 并行执行独立测试
- 及时清理测试产生的中间文件

### 3. 问题排查
- 查看详细的测试日志
- 使用本地复现CI环境
- 检查测试依赖和环境变量

这个集成为SAGE框架提供了完整的测试保障，确保代码质量和功能稳定性。
