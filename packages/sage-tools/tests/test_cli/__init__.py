"""
CLI测试模块

这个模块包含所有CLI相关的测试：

1. test_main.py - CLI主模块的单元测试 (pytest)
2. test_commands_full.py - 完整的CLI命令功能测试
3. test_smoke.py - 冒烟测试，快速验证核心功能

测试层次：
- Unit Tests (test_main.py): 测试单个组件和函数
- Integration Tests (test_commands_full.py): 测试完整的命令流程
- Smoke Tests (test_smoke.py): 快速验证核心功能是否可用

运行方式：
```bash
# 快速冒烟测试 (2-3分钟)
python test_cli/test_smoke.py

# 完整功能测试 (10-15分钟)  
python test_cli/test_commands_full.py

# pytest单元测试
pytest test_cli/test_main.py -v
```
"""
