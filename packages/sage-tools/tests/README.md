# SAGE Tools 测试文件夹

此目录包含 SAGE Tools 包的所有测试文件。

## 测试结构

```
tests/
├── __init__.py           # 测试包初始化
├── conftest.py          # pytest 配置和固件
├── test_studio/         # Studio 相关测试
├── test_dev/            # 开发工具测试
├── test_management/     # 管理工具测试
└── test_scripts/        # 脚本测试
```

## 运行测试

```bash
# 运行所有测试
pytest

# 运行特定模块测试
pytest tests/test_studio/

# 运行单个测试文件
pytest tests/test_studio/test_cli.py

# 运行带覆盖率的测试
pytest --cov=sage.tools

# 运行慢速测试
pytest -m slow

# 排除慢速测试
pytest -m "not slow"
```
