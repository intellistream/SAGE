# SAGE Examples 测试系统

这个测试系统专门用于测试 `examples/` 目录下的所有示例代码，确保示例代码的质量和可用性。

## 功能特性

### 🔍 自动发现与分析
- **智能扫描**: 自动发现 `examples/` 目录下的所有 Python 文件
- **依赖分析**: 分析每个示例的导入依赖和外部包需求
- **分类识别**: 自动识别示例的类别（tutorials、rag、memory 等）
- **运行时评估**: 估算示例的运行时间（快速、中等、慢速）

### 🧪 CLI 集成测试
- **集中入口**: `packages/sage-tools/tests/test_cli/runner.py` 汇总所有命令分组的测试用例
- **真实路径**: 针对 `sage` Typer CLI 的高频命令执行带有隔离依赖的模拟“真命令”流程
- **统一辅助**: `helpers.py` 提供配置、进程等虚拟对象，确保测试无副作用但覆盖更多执行逻辑
- **便捷运行**: 可直接运行 `python packages/sage-tools/tests/test_cli/runner.py` 或通过 `sage dev test` 集成入口触发（后续任务）

### 🚀 灵活的测试执行
- **多种运行模式**: 支持独立脚本和 pytest 集成两种方式
- **分类测试**: 可以按类别（如只测试 tutorials）运行测试
- **快速测试**: 支持只运行快速测试以提高CI效率
- **智能跳过**: 自动跳过需要用户输入、GUI或缺失依赖的示例

### 📊 详细的结果报告
- **实时进度**: 显示测试执行进度和状态
- **结果统计**: 提供通过/失败/跳过/超时的详细统计
- **错误信息**: 捕获并显示详细的错误信息
- **JSON报告**: 支持导出结构化的测试结果

### 🛠️ 环境管理
- **测试环境**: 为每种类型的示例配置专门的测试环境
- **模拟数据**: 为需要数据的示例自动生成测试数据
- **配置管理**: 自动创建测试配置文件避免真实服务依赖

## 快速开始

### 1. 安装依赖

```bash
pip install typer rich pytest pytest-timeout
```

### 2. 分析示例结构

```bash
# 查看所有示例的分析报告
./tools/tests/run_examples_tests.sh --analyze

# 或使用 Python 直接运行
python3 tools/tests/test_examples.py analyze
```

### 3. 运行测试

```bash
# 运行所有快速测试（推荐用于CI）
./tools/tests/run_examples_tests.sh --quick

# 只测试 tutorials 类别
./tools/tests/run_examples_tests.sh --category tutorials

# 使用 pytest 运行（推荐）
./tools/tests/run_examples_tests.sh --pytest --quick

# 保存测试结果
./tools/tests/run_examples_tests.sh --quick --output results.json
```

## 测试策略

### 按类别的测试策略

#### Tutorials 类别
- **超时**: 30秒
- **依赖**: 通常无外部依赖
- **期望成功率**: 80%+
- **特点**: 基础功能演示，应该稳定运行

#### RAG 类别  
- **超时**: 120秒
- **依赖**: 可能需要 API keys、向量数据库
- **期望成功率**: 30%+（因依赖问题）
- **特点**: 会自动跳过缺失API key的示例

#### Memory 类别
- **超时**: 60秒
- **依赖**: 内存服务、数据文件
- **期望成功率**: 60%+
- **特点**: 测试内存管理功能

#### Service 类别
- **超时**: 90秒
- **依赖**: 网络端口、配置文件
- **期望成功率**: 可变
- **特点**: 长期运行的服务会被跳过

### 自动跳过条件

示例会在以下情况被自动跳过：
- 包含 `# SKIP_TEST` 标记
- 需要用户输入（`input()` 函数）
- 需要GUI（tkinter、matplotlib show等）
- 缺失外部依赖包
- 匹配跳过模式（如 `*_interactive.py`）

## 文件结构

```
tools/tests/
├── test_examples.py           # 主要的测试框架
├── test_examples_pytest.py    # pytest 集成
├── example_strategies.py      # 测试策略配置
├── run_examples_tests.sh      # 便捷运行脚本
├── pytest.ini               # pytest 配置
└── README.md                 # 本文档
```

### 核心组件

#### `ExampleAnalyzer`
- 发现和分析示例文件
- 提取依赖信息
- 分类和评估示例

#### `ExampleRunner`
- 执行单个示例
- 管理执行环境
- 捕获输出和错误

#### `ExampleTestSuite`
- 协调整个测试流程
- 生成测试报告
- 管理测试统计

#### `ExampleTestStrategies`
- 为不同类别定义测试策略
- 配置超时、环境变量等
- 定义成功/失败模式

## 使用示例

### 命令行工具

```bash
# 查看帮助
./tools/tests/run_examples_tests.sh --help

# 分析示例（不运行）
./tools/tests/run_examples_tests.sh --analyze

# 快速测试（CI用）
./tools/tests/run_examples_tests.sh --quick --timeout 30

# 详细测试特定类别
./tools/tests/run_examples_tests.sh --category rag --verbose

# pytest 集成测试
./tools/tests/run_examples_tests.sh --pytest --quick
```

### Python API

```python
from test_examples import ExampleTestSuite, ExampleAnalyzer

# 分析示例
analyzer = ExampleAnalyzer()
examples = analyzer.discover_examples()
print(f"发现 {len(examples)} 个示例")

# 运行测试
suite = ExampleTestSuite()
stats = suite.run_all_tests(categories=["tutorials"], quick_only=True)
print(f"通过率: {stats['passed'] / stats['total'] * 100:.1f}%")
```

### pytest 集成

```bash
# 运行所有示例测试
cd tools/tests
python3 -m pytest test_examples_pytest.py -v

# 运行特定类别
python3 -m pytest test_examples_pytest.py -k "tutorials" -v

# 快速测试
python3 -m pytest test_examples_pytest.py -m quick_examples -v
```

## CI/CD 集成

### GitHub Actions 示例

```yaml
name: Examples Tests

on: [push, pull_request]

jobs:
  test-examples:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install typer rich pytest pytest-timeout
        
    - name: Run quick examples tests
      run: |
        ./tools/tests/run_examples_tests.sh --quick --timeout 60
        
    - name: Run pytest integration
      run: |
        cd tools/tests && python3 -m pytest test_examples_pytest.py -m quick_examples
```

## 扩展和自定义

### 添加新的测试策略

在 `example_strategies.py` 中添加新类别：

```python
"new_category": TestStrategy(
    name="new_category",
    timeout=90,
    requires_config=True,
    requires_data=False,
    success_patterns=["Success", "Completed"],
    failure_patterns=["Error", "Failed"],
    environment_vars={"CUSTOM_VAR": "test_value"}
)
```

### 自定义跳过条件

在 `ExampleTestFilters.should_skip_file()` 中添加：

```python
if 'custom_marker' in content:
    return True, "Custom skip condition"
```

### 添加新的结果验证

在测试策略中定义 `success_patterns` 和 `failure_patterns`：

```python
success_patterns=[
    "Pipeline completed successfully",
    "All tests passed",
    "✓ Done"
]
```

## 故障排除

### 常见问题

1. **导入错误**: 确保 PYTHONPATH 正确设置
2. **依赖缺失**: 使用 `--analyze` 查看依赖需求
3. **超时**: 增加 `--timeout` 值或使用 `--quick`
4. **权限问题**: 确保脚本有执行权限

### 调试技巧

```bash
# 详细输出
./tools/tests/run_examples_tests.sh --verbose

# 单独测试某个示例
python3 examples/tutorials/hello_world.py

# 查看详细错误
python3 tools/tests/test_examples.py test --category tutorials --timeout 120
```

## 贡献指南

1. 新增示例时，确保包含适当的文档
2. 添加 `# SKIP_TEST` 标记来跳过不适合自动测试的示例
3. 为复杂示例添加配置文件模板
4. 更新测试策略以覆盖新的示例类型

---

这个测试系统让 SAGE 的示例代码始终保持高质量和可用性，为用户提供可靠的学习和参考资源。