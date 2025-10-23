# SAGE Core模块测试架构

本目录包含了SAGE框架中`sage-kernel`包的`core`模块的完整测试套件，按照[测试组织规划Issue](../../docs/issues/test-organization-planning-issue.md)的要求设计实现。

## 📁 目录结构

```
tests/core/
├── README.md                           # 本文件 - 测试架构说明
├── conftest.py                         # 测试配置和共享fixtures
├── run_tests.py                        # 测试运行脚本
├── generate_coverage_report.py         # 覆盖率报告生成器
├── test_pipeline.py                    # Pipeline核心功能测试
├── api/                                # API模块测试（已存在）
│   ├── test_base_environment.py
│   ├── test_datastream.py
│   ├── test_local_environment.py
│   └── ...
├── function/                           # Function模块测试
│   ├── test_base_function.py          # BaseFunction基类测试
│   ├── test_comap_function.py         # CoMapFunction测试
│   ├── test_sink_function.py          # SinkFunction测试
│   └── test_source_function.py        # SourceFunction测试
├── operator/                          # Operator模块测试
│   └── test_base_operator.py          # BaseOperator基类测试
├── service/                           # Service模块测试
│   └── test_base_service.py           # BaseService基类测试
└── transformation/                    # Transformation模块测试（待完善）
```

## 🎯 测试覆盖范围

### 已完成的测试模块

#### 1. Pipeline测试 (`test_pipeline.py`)
- ✅ Pipeline类的创建和配置
- ✅ PipelineStep抽象基类
- ✅ DataTransformStep数据转换步骤
- ✅ FilterStep数据过滤步骤
- ✅ 便利函数测试
- ✅ 集成测试和错误处理

#### 2. Function模块测试 (`function/`)

**BaseFunction测试** (`test_base_function.py`)
- ✅ 基类创建和属性管理
- ✅ 上下文注入和logger管理
- ✅ 服务调用代理
- ✅ 状态管理功能

**CoMapFunction测试** (`test_comap_function.py`)
- ✅ 多流处理功能
- ✅ map0, map1, map2等方法测试
- ✅ 流独立性验证
- ✅ 错误处理和使用模式

**SinkFunction测试** (`test_sink_function.py`)
- ✅ 数据消费者功能
- ✅ 控制台、文件、数据库Sink示例
- ✅ 批处理和错误恢复
- ✅ 生命周期管理

**SourceFunction测试** (`test_source_function.py`)
- ✅ 数据生产者功能
- ✅ StopSignal机制
- ✅ 静态、计数器、无限数据源
- ✅ 资源管理和错误处理

#### 3. Operator模块测试 (`operator/`)

**BaseOperator测试** (`test_base_operator.py`)
- ✅ 操作器基类功能
- ✅ 数据包处理机制
- ✅ 路由器注入和状态管理
- ✅ 生命周期和错误处理

#### 4. Service模块测试 (`service/`)

**BaseService测试** (`test_base_service.py`)
- ✅ 服务基类功能
- ✅ 生命周期管理(setup/start/stop/cleanup)
- ✅ 上下文注入和日志管理
- ✅ 真实服务示例(数据库、缓存)

## 🏷️ 测试标记系统

按照pytest标记系统组织测试：

- `@pytest.mark.unit` - 单元测试
- `@pytest.mark.integration` - 集成测试  
- `@pytest.mark.slow` - 耗时测试
- `@pytest.mark.external` - 需要外部依赖的测试

## 🚀 运行测试

### 1. 快速运行所有测试
```bash
cd packages/sage-kernel
python -m pytest tests/core/ -v
```

### 2. 使用测试运行脚本
```bash
cd tests/core
python run_tests.py --help
```

**主要选项：**
```bash
# 检查测试结构合规性
python run_tests.py --check-structure

# 运行特定模块测试
python run_tests.py --module function

# 按测试类型运行
python run_tests.py --type unit

# 生成覆盖率报告
python run_tests.py --report

# 交互式模式
python run_tests.py --interactive

# 并行执行
python run_tests.py --parallel
```

### 3. 按模块运行测试

**Pipeline测试：**
```bash
python -m pytest tests/core/test_pipeline.py -v
```

**Function模块测试：**
```bash
python -m pytest tests/core/function/ -v
```

**Operator模块测试：**
```bash
python -m pytest tests/core/operator/ -v
```

**Service模块测试：**
```bash
python -m pytest tests/core/service/ -v
```

### 4. 按标记运行测试

**只运行单元测试：**
```bash
python -m pytest tests/core/ -m unit -v
```

**只运行集成测试：**
```bash
python -m pytest tests/core/ -m integration -v
```

**排除慢速测试：**
```bash
python -m pytest tests/core/ -m "not slow" -v
```

## 📊 覆盖率报告

### 生成覆盖率报告
```bash
# 自动生成完整报告
python generate_coverage_report.py

# 或使用pytest直接生成
python -m pytest tests/core/ --cov=src/sage/core --cov-report=html --cov-report=term-missing
```

### 覆盖率目标

根据Issue要求：
- **单元测试覆盖率**: ≥ 80%
- **集成测试覆盖率**: ≥ 60%  
- **关键路径覆盖率**: = 100%

## 🛠️ 开发指南

### 添加新测试

1. **创建测试文件**：按照命名规范创建测试文件
   ```
   src/sage/core/新模块.py → tests/core/test_新模块.py
   ```

2. **使用测试模板**：参考现有测试文件的结构
   ```python
   import pytest
   from unittest.mock import Mock

   @pytest.mark.unit
   class TestNewModule:
       def test_creation(self):
           # 测试创建
           pass

       def test_functionality(self):
           # 测试功能
           pass

   @pytest.mark.integration  
   class TestNewModuleIntegration:
       def test_integration_scenario(self):
           # 集成测试
           pass
   ```

3. **添加适当的标记**：使用pytest标记分类测试

4. **更新conftest.py**：如需要共享的fixtures

### 测试最佳实践

1. **测试命名**：清晰描述测试目的
   ```python
   def test_pipeline_executes_steps_in_order(self):
   def test_function_handles_empty_input_gracefully(self):  
   def test_operator_processes_multiple_packets(self):
   ```

2. **使用Mock**：减少外部依赖
   ```python
   @patch('sage.core.api.function.base_function.ServiceCallProxy')
   def test_with_mocked_service(self, mock_proxy):
       # 测试逻辑
   ```

3. **边界条件**：测试边界和异常情况
   ```python
   def test_handles_none_input(self):
   def test_handles_empty_list(self):
   def test_raises_error_on_invalid_input(self):
   ```

4. **数据驱动测试**：使用pytest.mark.parametrize
   ```python
   @pytest.mark.parametrize("input_data,expected", [
       ("hello", "HELLO"),
       ("world", "WORLD"),
   ])
   def test_uppercase_transform(self, input_data, expected):
       result = transform_to_upper(input_data)
       assert result == expected
   ```

## 📈 质量指标

### 当前状态

- ✅ **测试架构完成度**: 100% (按Issue要求)
- ✅ **核心模块覆盖**: Pipeline, Function, Operator, Service
- ✅ **测试分类**: Unit, Integration, Slow
- ✅ **自动化工具**: 测试运行器, 覆盖率报告器

### 持续改进

- [ ] Transformation模块测试完善
- [ ] 增加性能基准测试
- [ ] 集成CI/CD管道
- [ ] 添加更多边界情况测试

## 🤝 贡献指南

1. **运行现有测试**：确保所有测试通过
   ```bash
   python run_tests.py --report
   ```

2. **添加新测试**：按照架构规范添加

3. **检查覆盖率**：确保覆盖率不降低
   ```bash  
   python generate_coverage_report.py
   ```

4. **更新文档**：同步更新README和注释

## 📚 相关文档

- [Issue: 完善packages目录中各包的测试组织架构](../../docs/issues/test-organization-planning-issue.md)
- [SAGE开发工具包文档](../../dev-toolkit/README.md)
- [pytest官方文档](https://docs.pytest.org/)
- [coverage.py文档](https://coverage.readthedocs.io/)

## 🆘 常见问题

### Q: 测试运行失败怎么办？
A:
1. 检查依赖是否安装：`pip install -e .[dev]`
2. 检查Python路径：确保在正确的目录运行
3. 查看错误日志：使用`-v`参数获取详细输出

### Q: 如何调试单个测试？
A:
```bash
python -m pytest tests/core/test_pipeline.py::TestPipeline::test_creation -v -s
```

### Q: 覆盖率报告在哪里？
A:
- HTML报告：`htmlcov/core/index.html`
- 终端报告：运行测试时直接显示
- JSON报告：`coverage-core.json`

### Q: 如何添加新的测试标记？
A: 在`pyproject.toml`的`[tool.pytest.ini_options]`部分添加新标记

---

**维护者**: SAGE开发团队  
**最后更新**: 2025-08-04  
**版本**: 1.0.0

- Python 3.8+
- pytest 测试框架
- 相关服务运行环境
- 网络连接（用于分布式测试）

## 测试数据和配置

测试使用预定义的测试数据集和配置文件，确保测试结果的一致性和可重现性。详细配置请参考各测试文件中的设置。
