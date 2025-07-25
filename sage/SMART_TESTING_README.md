# 智能测试系统

这是一个基于代码变化的智能测试系统，能够根据git变化自动映射到相应的 `sage_tests/xxx_tests` 目录并运行测试。

## 功能特性

- 🔍 **智能检测**: 自动检测git变化的文件
- 📁 **智能映射**: 将源码变化映射到对应的测试目录
- 🧪 **自动运行**: 只运行相关的测试，节省时间
- 📊 **详细报告**: 提供测试结果总结

## 源码到测试目录的映射规则

| 源码目录 | 测试目录 | 说明 |
|----------|----------|------|
| `sage.core/` | `core_tests/` | 核心功能测试 |
| `sage.runtime/` | `runtime_tests/` | 运行时测试 |
| `sage.service.memory./` | `memory_tests/` | 内存管理测试 |
| `sage_vector/` | `vector_tests/` | 向量操作测试 |
| `frontend/` | `frontend_tests/` | 前端API测试 |
| `sage.utils/` | `utils_tests/` | 工具类测试 |
| `sage.libs/` | `function_tests/` | 函数库测试 |
| `sage_plugins/` | `function_tests/` | 插件测试 |
| `sage.core/service/` | `service_tests/` | 服务系统测试 |
| `sage.core/function/` | `function_tests/` | 函数测试 |
| `sage.libs/io/` | `function_tests/io_tests/` | IO函数测试 |
| `sage.libs/rag/` | `function_tests/rag_tests/` | RAG函数测试 |

## 使用方法

### 1. 本地使用

```bash
# 测试相对于上一次提交的变化
python run_smart_tests_local.py

# 测试相对于main分支的变化  
python run_smart_tests_local.py --base main

# 测试相对于指定提交的变化
python run_smart_tests_local.py --base HEAD~5

# 直接使用智能测试运行器
python scripts/smart_test_runner.py --base-branch main
```

### 2. GitHub Actions自动运行

智能测试系统会在以下情况自动运行：
- Push到 `main`, `develop`, `v*.*.*` 分支
- 创建针对 `main`, `develop` 的Pull Request

GitHub Actions配置文件：`.github/workflows/smart-tests.yml`

## 工作流程

1. **检测变化**: 使用 `git diff` 检测变化的文件
2. **智能映射**: 根据映射规则找到对应的测试目录
3. **查找测试**: 在测试目录中递归查找所有 `test_*.py` 和 `*_test.py` 文件
4. **运行测试**: 使用 `pytest` 运行相关测试
5. **结果报告**: 显示详细的测试结果

## 示例输出

```
🚀 开始智能测试...
📂 项目根目录: /home/tjy/SAGE
📂 测试目录: /home/tjy/SAGE/sage_tests

🔍 检测到 15 个文件发生变化:
  - sage.core/service/service_caller.py
  - sage.runtime/dispatcher.py
  - sage.utils/custom_logger.py
  ...

📁 sage.core/service/service_caller.py -> service_tests/
📁 sage.runtime/dispatcher.py -> runtime_tests/
📁 sage.utils/custom_logger.py -> utils_tests/

🎯 需要运行的测试目录 (3 个):
  - /home/tjy/SAGE/sage_tests/service_tests
  - /home/tjy/SAGE/sage_tests/runtime_tests
  - /home/tjy/SAGE/sage_tests/utils_tests

============================================================
🧪 运行 /home/tjy/SAGE/sage_tests/service_tests 中的测试:
  - /home/tjy/SAGE/sage_tests/service_tests/test_service_caller.py
  - /home/tjy/SAGE/sage_tests/service_tests/test_concurrent_service_calls.py
  ...

✅ /home/tjy/SAGE/sage_tests/service_tests 测试通过

============================================================
📊 测试结果总结:
  ✅ 通过 /home/tjy/SAGE/sage_tests/service_tests
  ✅ 通过 /home/tjy/SAGE/sage_tests/runtime_tests
  ✅ 通过 /home/tjy/SAGE/sage_tests/utils_tests

🎉 所有测试通过! (3 个测试目录)
```

## 配置说明

### 添加新的映射规则

编辑 `scripts/smart_test_runner.py` 中的 `source_to_test_mapping` 字典：

```python
self.source_to_test_mapping = {
    # 现有映射...
    "新的源码目录/": "对应的测试目录/",
}
```

### 测试文件命名规范

智能测试系统会查找以下模式的测试文件：
- `test_*.py` - 以test_开头的文件
- `*_test.py` - 以_test结尾的文件

## 故障排除

### 常见问题

1. **没有找到对应的测试目录**
   - 检查源码目录是否在映射规则中
   - 确认测试目录是否存在

2. **测试失败**
   - 查看详细的pytest输出
   - 检查测试代码是否正确

3. **网络相关测试失败**
   - 某些测试需要网络连接（如embedding测试）
   - 在CI环境中可能需要跳过这些测试

### 调试模式

```bash
# 显示详细的git diff信息
git diff --name-only HEAD~1

# 手动运行特定测试目录
python -m pytest sage_tests/service_tests/ -v
```

## 贡献指南

1. 添加新的源码模块时，请在映射规则中添加对应关系
2. 确保测试文件遵循命名规范
3. 在CI环境中测试新的映射规则

---

这个智能测试系统让我们能够：
- ⚡ 快速运行相关测试，节省时间
- 🎯 只测试受影响的代码，提高效率  
- 🔍 自动发现需要测试的模块
- 📊 清晰的测试结果报告
