# SAGE CLI Tools 测试框架

本目录包含 SAGE CLI Tools 的完整测试套件，采用 pytest 框架和标准化测试组织结构。

## 测试结构

```
tests/
├── __init__.py                 # 测试包初始化
├── conftest.py                # pytest 配置和公共 fixtures
├── run_pytest.py              # pytest-based 测试运行器
├── test_basic.py              # 基础功能测试
├── test_cli/                  # CLI 相关测试
│   ├── __init__.py            
│   ├── test_main.py           # CLI 主模块单元测试
│   ├── test_commands_full.py  # 完整 CLI 命令功能测试
│   └── test_smoke.py          # 快速冒烟测试
├── test_dev/                  # 开发工具测试
│   ├── test_dependency_analyzer.py
│   ├── test_package_manager.py
│   └── test_status_checker.py
└── integration/               # 集成测试
    ├── test_full_workflow.py
    └── test_cli_integration.py
```

## 测试分类

采用 pytest markers 进行测试分类：

- `@pytest.mark.unit` - 单元测试（快速，隔离）
- `@pytest.mark.integration` - 集成测试（较慢，真实服务）
- `@pytest.mark.cli` - CLI 命令测试
- `@pytest.mark.slow` - 长时间运行的测试
- `@pytest.mark.quick` - 快速验证测试

## 运行测试

### 使用 pytest 测试运行器

```bash
# 运行所有测试
python run_pytest.py

# 运行特定类型的测试
python run_pytest.py --unit              # 只运行单元测试
python run_pytest.py --cli               # 只运行 CLI 测试
python run_pytest.py --integration       # 只运行集成测试
python run_pytest.py --quick             # 只运行快速测试

# 运行特定目录的测试
python run_pytest.py --pattern test_dev  # 只运行 test_dev 目录
python run_pytest.py --pattern test_cli  # 只运行 test_cli 目录

# 其他选项
python run_pytest.py --coverage          # 运行并生成覆盖率报告
python run_pytest.py --verbose           # 详细输出
python run_pytest.py --exitfirst         # 遇到第一个失败即退出
python run_pytest.py --failed            # 只运行上次失败的测试
```

### 直接使用 pytest

```bash
# 运行所有测试
pytest

# 运行特定文件
pytest test_dev/test_status_checker.py -v

# 按标记运行
pytest -m unit -v                    # 只运行单元测试
pytest -m "unit or cli" -v           # 运行单元测试和CLI测试
pytest -m "not slow" -v              # 排除慢速测试

# 生成覆盖率报告
pytest --cov=sage.tools --cov-report=html

# 并行运行测试
pytest -n auto                       # 需要 pytest-xdist 插件
```

## 测试指南

### 编写新测试

1. **选择合适的测试类型**：
   - 功能级别 → 单元测试 (`@pytest.mark.unit`)
   - CLI命令 → CLI测试 (`@pytest.mark.cli`)
   - 工作流 → 集成测试 (`@pytest.mark.integration`)

2. **使用 fixtures**：
   ```python
   @pytest.fixture
   def project_root():
       # 返回项目根目录
       pass
   
   def test_something(project_root):
       # 使用fixture
       pass
   ```

3. **适当的断言**：
   ```python
   assert result is not None
   assert len(items) > 0
   assert "expected" in output
   ```

### 测试最佳实践

- **隔离性**: 每个测试应该独立运行
- **可重复性**: 测试结果应该一致
- **清晰性**: 测试名称要描述性强
- **速度**: 单元测试应该快速执行
- **覆盖率**: 关键功能应有测试覆盖

## 故障排除

### 常见问题

1. **导入错误**: 确保项目根目录在 Python 路径中
2. **文件路径错误**: 使用 `project_root` fixture 获取正确路径
3. **测试隔离**: 使用 `tmp_path` fixture 创建临时文件
4. **Mock 对象**: 使用 `unittest.mock` 模拟外部依赖

### 调试测试

```bash
# 详细输出
pytest -v -s

# 进入调试模式
pytest --pdb

# 只运行失败的测试
pytest --lf

# 显示最慢的测试
pytest --durations=10
```
pytest tests/integration/ -v

# 带覆盖率的测试
pytest --cov=sage.tools --cov-report=html
```

### 测试标记

```bash
# 快速测试 (排除耗时测试)
pytest -m "not slow" -v

# 只运行冒烟测试标记的测试
pytest -m smoke -v
```

## 开发建议

### 测试选择指南

1. **开发过程中**: 使用冒烟测试快速验证 (`test_smoke.py`)
2. **功能开发**: 运行相关的单元测试 (`pytest test_cli/test_main.py`)
3. **提交前**: 运行完整集成测试 (`test_commands_full.py`)
4. **发布前**: 运行所有测试套件 (`python run_tests.py`)

### 添加新测试

- **单元测试**: 添加到相应的 `test_*/` 目录下
- **CLI功能测试**: 添加到 `test_cli/test_commands_full.py`
- **快速验证**: 如果是核心功能，考虑添加到 `test_cli/test_smoke.py`

### 避免重复

- 冒烟测试只包含关键路径验证
- 完整测试包含详细的功能验证
- 单元测试专注于函数/类级别的逻辑
```

## 测试标记

```bash
# 快速测试
pytest -m "not slow"

# 包含慢速测试
pytest -m slow

# CLI相关测试
pytest -m cli

# 单元测试
pytest -m unit

# 集成测试  
pytest -m integration
```
