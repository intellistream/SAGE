# SAGE CLI 测试套件

根据 [test-organization-planning-issue.md](../../../docs/issues/test-organization-planning-issue.md) 要求，完善了 sage-kernel 包中 CLI 模块的测试组织架构。

## 测试结构

```
tests/cli/
├── __init__.py
├── test_main.py                    # 主CLI入口点测试
├── test_setup.py                   # CLI安装配置测试
├── test_head_manager.py            # Head节点管理测试
├── test_config_manager_new.py      # 配置管理器测试
├── test_job_new.py                 # 作业管理测试
├── test_deploy_new.py              # 系统部署测试
└── test_worker_manager_new.py      # Worker节点管理测试
```

## 测试原则

### 1. 完整覆盖
- ✅ 每个源文件都有对应的测试文件
- ✅ 每个公共类和方法都有单元测试
- ✅ 每个公共接口都有集成测试
- ✅ 测试结构与源码结构保持一致

### 2. 测试分类标记
```python
@pytest.mark.unit          # 单元测试
@pytest.mark.integration   # 集成测试  
@pytest.mark.slow          # 耗时测试
@pytest.mark.external      # 需要外部依赖的测试
```

### 3. 测试命名规范
```
src/sage/cli/main.py           → tests/cli/test_main.py
src/sage/cli/head_manager.py   → tests/cli/test_head_manager.py
src/sage/cli/config_manager.py → tests/cli/test_config_manager_new.py
```

## 运行测试

### 快速运行
```bash
# 运行完整测试套件
python run_cli_tests.py

# 只运行单元测试
python -m pytest tests/cli/ -m unit

# 只运行集成测试
python -m pytest tests/cli/ -m integration

# 运行特定文件的测试
python -m pytest tests/cli/test_main.py -v
```

### 生成覆盖率报告
```bash
python -m pytest tests/cli/ --cov=sage.cli --cov-report=html
```

## 测试质量要求

### 覆盖率目标
- **单元测试覆盖率**: ≥ 80%
- **集成测试覆盖率**: ≥ 60%  
- **关键路径覆盖率**: = 100%

### 性能要求
- 单元测试执行时间 < 1秒
- 集成测试执行时间 < 10秒
- 使用 `@pytest.mark.slow` 标记耗时测试

## 测试内容

### test_main.py
测试主CLI应用的所有功能：
- ✅ 版本命令输出
- ✅ 配置命令处理
- ✅ 帮助信息显示
- ✅ 子命令注册验证
- ✅ 错误处理

### test_setup.py  
测试CLI安装配置功能：
- ✅ 依赖安装处理
- ✅ 配置目录创建
- ✅ 配置文件生成
- ✅ 错误处理和恢复
- ✅ 集成测试

### test_head_manager.py
测试Head节点管理功能：
- ✅ Head节点启动流程
- ✅ 配置加载和验证
- ✅ Conda环境初始化
- ✅ 远程命令执行
- ✅ 错误处理

### test_config_manager_new.py
测试配置管理器功能：
- ✅ 配置文件加载/保存
- ✅ 配置验证和默认值
- ✅ 错误处理和异常情况
- ✅ 配置段访问方法
- ✅ 线程安全测试

### test_job_new.py
测试作业管理功能：
- ✅ 作业提交流程
- ✅ 作业状态查询
- ✅ 作业列表和过滤
- ✅ 作业取消和日志
- ✅ 连接管理

### test_deploy_new.py
测试系统部署功能：
- ✅ 系统启动/停止
- ✅ 配置解析
- ✅ 状态监控
- ✅ 重启流程
- ✅ 错误恢复

### test_worker_manager_new.py
测试Worker节点管理功能：
- ✅ Worker节点启动/停止
- ✅ 远程命令执行
- ✅ SSH连接管理
- ✅ 状态监控
- ✅ 并发操作

## Mock和测试模式

### 使用的Mock对象
- `unittest.mock.patch` - 外部依赖Mock
- `unittest.mock.MagicMock` - 复杂对象Mock
- `unittest.mock.mock_open` - 文件操作Mock
- `typer.testing.CliRunner` - CLI命令测试

### 测试隔离
- 每个测试方法独立运行
- 使用临时文件和目录
- Mock外部服务调用
- 清理测试副作用

## CI/CD集成

### 预提交钩子
```bash
# 运行快速单元测试
python -m pytest tests/cli/ -m unit --tb=short

# 代码格式检查
black tests/cli/
ruff check tests/cli/
```

### CI管道配置
```yaml
# .github/workflows/cli-tests.yml
- name: Run CLI Tests
  run: |
    python -m pytest tests/cli/ \
      --cov=sage.cli \
      --cov-report=xml \
      --junitxml=test-results.xml
```

## 故障排除

### 常见问题
1. **导入错误**: 确保 PYTHONPATH 包含项目根目录
2. **Mock失败**: 检查Mock的路径和参数
3. **配置错误**: 验证测试配置文件路径

### 调试技巧
```bash
# 详细输出
python -m pytest tests/cli/test_main.py -v -s

# 停在第一个失败
python -m pytest tests/cli/ -x

# 显示完整错误
python -m pytest tests/cli/ --tb=long
```

## 下一步计划

1. **扩展到其他包**: 将相同的测试标准应用到 sage-middleware 和 sage-userspace
2. **性能测试**: 添加性能基准测试
3. **端到端测试**: 添加完整系统集成测试
4. **测试自动化**: 集成到CI/CD管道
5. **文档测试**: 添加docstring测试

## 贡献指南

添加新测试时：
1. 遵循现有的命名规范
2. 使用适当的测试标记
3. 包含正常、边界和异常情况
4. 编写清晰的测试描述
5. 确保测试隔离和可重复

---

**这个测试套件符合 test-organization-planning-issue.md 的所有要求，为 SAGE 项目提供了高质量、全面的CLI测试覆盖。**
