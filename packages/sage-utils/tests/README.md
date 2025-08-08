# SAGE Utils Tests

这里包含sage-utils包的测试文件。

## 测试结构

```
tests/
├── __init__.py
├── conftest.py              # pytest配置和fixtures
├── config/
│   ├── __init__.py
│   ├── test_loader.py       # 配置加载器测试
│   └── test_manager.py      # 配置管理器测试
└── logging/
    ├── __init__.py
    ├── test_custom_logger.py    # 自定义日志记录器测试
    └── test_custom_formatter.py # 自定义格式化器测试
```

## 运行测试

```bash
# 运行所有测试
pytest

# 运行特定模块测试
pytest tests/config/
pytest tests/logging/

# 带覆盖率的测试
pytest --cov=sage.utils --cov-report=html
```

## 测试标记

- `unit`: 单元测试
- `integration`: 集成测试  
- `slow`: 慢测试
