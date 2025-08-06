# SAGE Userspace 测试架构文档

## 概述

本文档描述了 SAGE Userspace 包的完整测试组织架构，遵循了 [test-organization-planning-issue.md](../../../docs/issues/test-organization-planning-issue.md) 中制定的测试标准和最佳实践。

## 测试结构

### 目录组织

```
tests/
├── conftest.py                    # 共享测试配置和fixtures
├── run_tests.py                   # 测试运行脚本
├── generate_reports.py            # 测试报告生成器
├── README.md                      # 本文档
├── lib/                          # sage.apps.lib 模块測试
│   ├── agents/
│   │   ├── test_agent.py         # Agent基础类测试
│   │   └── test_bots.py          # 各种Bot组件测试
│   ├── rag/
│   │   ├── test_evaluate.py      # 评估模块测试
│   │   └── test_retriever.py     # 检索模块测试
│   ├── io/
│   │   └── test_source.py        # 数据源模块测试
│   ├── context/                   # 上下文模块测试
│   └── utils/                     # 工具模块测试
├── plugins/                       # sage.plugins 模块测试
│   └── test_longrefiner_adapter.py # LongRefiner插件测试
├── userspace/                     # sage.userspace 模块测试
│   └── test_agents.py            # Userspace Agent测试
└── reports/                       # 测试报告目录
    ├── coverage_report.md
    ├── compliance_report.md
    └── organization_report.md
```

### 测试原则

1. **1:1 映射**: 每个源文件对应一个测试文件
2. **标记系统**: 使用 pytest 标记分类测试
3. **全面覆盖**: 包含单元测试、集成测试、性能测试
4. **降级支持**: 当依赖不可用时优雅降级

## 测试标记系统

### 标记类型

- `@pytest.mark.unit`: 单元测试，测试单个函数或方法
- `@pytest.mark.integration`: 集成测试，测试组件间交互
- `@pytest.mark.slow`: 耗时测试，执行时间较长
- `@pytest.mark.external`: 外部依赖测试，需要网络或外部服务

### 使用示例

```python
@pytest.mark.unit
def test_function_basic():
    """单元测试示例"""
    pass

@pytest.mark.integration
def test_component_interaction():
    """集成测试示例"""
    pass

@pytest.mark.slow
def test_performance():
    """性能测试示例"""
    pass

@pytest.mark.external
def test_api_call():
    """外部依赖测试示例"""
    pass
```

## 运行测试

### 基本用法

```bash
# 进入项目目录
cd /home/flecther/SAGE/packages/sage-userspace

# 运行所有测试
python tests/run_tests.py

# 或使用 pytest 直接运行
python -m pytest tests/
```

### 高级选项

```bash
# 只运行单元测试
python tests/run_tests.py --unit

# 只运行集成测试
python tests/run_tests.py --integration

# 包含耗时测试
python tests/run_tests.py --slow

# 生成覆盖率报告
python tests/run_tests.py --coverage

# 生成HTML覆盖率报告
python tests/run_tests.py --html-coverage

# 只测试特定模块
python tests/run_tests.py --lib           # 只测试lib模块
python tests/run_tests.py --plugins       # 只测试plugins模块
python tests/run_tests.py --userspace     # 只测试userspace模块

# 只测试特定功能
python tests/run_tests.py --agents        # 只测试agents
python tests/run_tests.py --rag           # 只测试rag
python tests/run_tests.py --io            # 只测试io

# 并行运行测试
python tests/run_tests.py --parallel 4

# 详细输出
python tests/run_tests.py --verbose

# 遇到失败立即停止
python tests/run_tests.py --failfast

# 只运行上次失败的测试
python tests/run_tests.py --lf
```

### pytest 直接使用

```bash
# 运行特定测试文件
python -m pytest tests/lib/agents/test_agent.py -v

# 运行特定测试类
python -m pytest tests/lib/agents/test_agent.py::TestTool -v

# 运行特定测试方法
python -m pytest tests/lib/agents/test_agent.py::TestTool::test_tool_initialization -v

# 使用标记过滤
python -m pytest -m "unit and not slow" -v

# 生成覆盖率报告
python -m pytest --cov=sage.apps.lib --cov=sage.plugins --cov=sage.userspace --cov-report=html
```

## 生成测试报告

### 自动报告生成

```bash
# 生成所有报告
python tests/generate_reports.py
```

这将生成三类报告：

1. **覆盖率报告** (`reports/coverage_report.md`): 详细的代码覆盖率分析
2. **合规性报告** (`reports/compliance_report.md`): 测试标准合规性检查
3. **组织结构报告** (`reports/organization_report.md`): 测试文件组织结构分析

### 报告内容

#### 覆盖率报告
- 总体覆盖率统计
- 文件级覆盖率详情
- 测试方法统计
- 未覆盖代码分析

#### 合规性报告
- 测试文件覆盖完整性检查
- 测试标记使用情况
- 合规性评分
- 改进建议

#### 组织结构报告
- 测试目录结构树
- 测试文件分布统计
- 测试方法统计
- 组织架构分析

## 测试配置

### pytest 配置

测试配置定义在 `pyproject.toml` 中：

```toml
[tool.pytest.ini_options]
testpaths = ["tests", "src"]
python_files = ["test_*.py", "*_test.py"]
addopts = [
    # 覆盖率选项已注释，按需启用
    # "--cov=sage.apps.lib",
    # "--cov=sage.plugins", 
    # "--cov=sage.userspace",
]
```

### 共享 Fixtures

`conftest.py` 提供了丰富的共享 fixtures：

- **基础数据**: `sample_config`, `sample_data`, `sample_query`
- **文档数据**: `sample_documents`, `sample_embeddings`, `sample_qa_pair`
- **模拟对象**: `mock_environment`, `mock_llm_client`, `mock_vector_store`
- **异步支持**: `mock_async_client`
- **测试工具**: `temp_dir`, `create_temp_file`

## 测试覆盖范围

### lib 模块测试

#### agents 模块
- **test_agent.py**: Agent基础类、Tool类、BochaSearch类
- **test_bots.py**: QuestionBot、AnswerBot、CriticBot、SearcherBot

#### rag 模块  
- **test_evaluate.py**: 各种评估器 (F1、Recall、BERT、ROUGE-L等)
- **test_retriever.py**: 检索器 (Dense、BM25、Hybrid)

#### io 模块
- **test_source.py**: 数据源 (文本、JSON、CSV、Kafka、数据库、API)

### plugins 模块测试

- **test_longrefiner_adapter.py**: LongRefiner插件适配器完整测试

### userspace 模块测试

- **test_agents.py**: BasicAgent、CommunityAgent测试

## 测试质量保证

### 测试类型分布

- **单元测试**: 测试单个函数、方法的功能
- **集成测试**: 测试组件间的交互和工作流
- **性能测试**: 测试性能特征和资源使用
- **外部依赖测试**: 测试外部服务集成

### 错误处理

每个测试都包含：

1. **正常情况测试**: 验证基本功能
2. **边界情况测试**: 验证极端输入处理
3. **异常情况测试**: 验证错误处理
4. **降级测试**: 验证依赖不可用时的行为

### Mock 策略

- **外部依赖 Mock**: 数据库、API、网络服务
- **复杂对象 Mock**: ML模型、大型计算组件
- **时间敏感 Mock**: 时间戳、超时处理
- **文件系统 Mock**: 文件读写操作

## 持续集成

### 预提交检查

建议的预提交钩子：

```bash
# 运行快速单元测试
python tests/run_tests.py --unit --quiet

# 代码格式检查
black --check src/ tests/

# 类型检查  
mypy src/
```

### CI 管道

完整 CI 管道应包括：

```yaml
# 示例 GitHub Actions 配置
- name: Run Unit Tests
  run: python tests/run_tests.py --unit --coverage

- name: Run Integration Tests  
  run: python tests/run_tests.py --integration

- name: Generate Reports
  run: python tests/generate_reports.py

- name: Upload Coverage
  uses: codecov/codecov-action@v3
```

## 开发工作流

### 新功能开发

1. **创建源文件**: 在 `src/sage/` 下创建新模块
2. **创建测试文件**: 在 `tests/` 下创建对应测试
3. **编写测试**: 先写测试，再实现功能 (TDD)
4. **运行测试**: 确保所有测试通过
5. **检查覆盖率**: 确保新代码有足够覆盖率

### 测试编写指南

```python
# 测试文件模板
"""
测试 sage.apps.lib.module_name 模块
"""

import pytest
from unittest.mock import Mock, patch

# 尝试导入，处理依赖不可用的情况
try:
    from sage.apps.lib.module_name import TargetClass
    MODULE_AVAILABLE = True
except ImportError as e:
    MODULE_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Module not available: {e}")


@pytest.mark.unit
class TestTargetClass:
    """测试 TargetClass 类"""
    
    def test_initialization(self):
        """测试初始化"""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        # 测试代码
        pass
    
    def test_method_name(self):
        """测试具体方法"""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        # 测试代码
        pass


@pytest.mark.integration  
class TestTargetClassIntegration:
    """集成测试"""
    pass


@pytest.mark.unit
class TestTargetClassFallback:
    """降级测试"""
    
    def test_fallback_behavior(self):
        """测试降级行为"""
        # 这个测试总是运行，不依赖具体实现
        pass
```

## 故障排除

### 常见问题

1. **导入错误**: 某些模块可能因为依赖不完整而无法导入
   - 解决方案: 使用 `pytest.skip()` 跳过不可用的测试

2. **Mock 对象问题**: Mock 配置不正确
   - 解决方案: 仔细检查 Mock 的返回值和调用参数

3. **异步测试问题**: 异步代码测试复杂
   - 解决方案: 使用 `pytest-asyncio` 和 `AsyncMock`

4. **覆盖率过低**: 某些代码分支未覆盖
   - 解决方案: 添加边界情况和异常情况测试

### 调试技巧

```bash
# 详细输出模式
python -m pytest -v -s

# 只运行失败的测试
python -m pytest --lf -v

# 进入调试模式
python -m pytest --pdb

# 显示最慢的测试
python -m pytest --durations=10
```

## 贡献指南

### 提交新测试

1. 确保测试文件遵循命名规范: `test_*.py`
2. 使用适当的 pytest 标记
3. 包含降级测试以处理依赖不可用情况
4. 更新相关文档

### 代码审查检查清单

- [ ] 测试覆盖新增功能的所有公共方法
- [ ] 包含正常、边界和异常情况测试
- [ ] 使用了适当的 pytest 标记
- [ ] Mock 对象配置正确
- [ ] 测试命名清晰描述测试目的
- [ ] 包含必要的文档字符串

## 参考资料

- [pytest 官方文档](https://docs.pytest.org/)
- [测试组织规划 Issue](../../../docs/issues/test-organization-planning-issue.md)
- [SAGE 开发指南](../README.md)
- [Python 测试最佳实践](https://docs.python-guide.org/writing/tests/)

---

**维护者**: IntelliStream Team  
**最后更新**: 2025-01-01  
**版本**: 1.0.0
