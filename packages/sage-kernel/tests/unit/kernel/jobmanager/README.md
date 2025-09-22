# SAGE JobManager测试

JobManager模块的完整测试套件，确保作业管理系统的可靠性和性能。

## 测试概述

本目录包含对SAGE JobManager所有组件的测试，覆盖作业提交、执行、监控等核心功能。

## 测试文件

### `test_jobmanager_submit.py`
作业提交测试：
- 作业提交流程测试
- 作业参数验证测试
- 批量作业提交测试
- 作业依赖关系测试

### `test_jobmanager_refactor.py`
JobManager重构测试：
- 新架构功能测试
- 重构后的兼容性测试
- 性能优化效果测试
- 代码质量和结构测试

### `test_service_task_factory_ownership.py`
服务任务工厂所有权测试：
- 任务工厂创建和管理测试
- 所有权转移和控制测试
- 任务生命周期管理测试
- 资源清理和回收测试

### `test_end_to_end.py`
端到端测试：
- 完整的作业执行流程测试
- 多组件集成测试
- 实际使用场景模拟测试
- 系统稳定性和可靠性测试

## 测试数据

### 作业脚本
- 简单计算任务脚本
- 复杂数据处理脚本
- 长时间运行任务脚本
- 错误和异常场景脚本

### 配置文件
- 各种作业配置模板
- 资源限制配置
- 网络和存储配置
- 错误配置测试用例

## 运行测试

```bash
# 运行所有JobManager测试
python -m pytest sage/jobmanager/tests/

# 运行特定测试
python -m pytest sage/jobmanager/tests/test_jobmanager_submit.py
python -m pytest sage/jobmanager/tests/test_end_to_end.py

# 运行端到端测试
python -m pytest sage/jobmanager/tests/test_end_to_end.py -v

# 运行性能测试
python -m pytest sage/jobmanager/tests/ -m "performance"
```

## 测试环境

### 依赖服务
- Ray集群环境
- 分布式存储系统
- 网络通信服务
- 监控和日志服务

### 环境配置
```bash
export SAGE_TEST_MODE=true
export RAY_ADDRESS=local
export SAGE_JOBMANAGER_PORT=19001
```

## 性能基准

### 作业提交性能
- 单作业提交延迟 < 1秒
- 批量作业提交吞吐量 > 100 jobs/s
- 并发提交支持 > 50 concurrent submissions

### 系统稳定性
- 长时间运行稳定性 > 7天
- 内存泄漏检测
- 故障恢复时间 < 30秒
- 数据一致性保证

## 测试策略

# SAGE JobManager测试套件

JobManager模块的完整测试套件，确保作业管理系统的可靠性和性能。提供全面的单元测试、集成测试和性能测试覆盖。

## 测试概述

本目录包含对SAGE JobManager所有组件的测试，覆盖作业提交、执行、监控等核心功能。

## 测试结构

### 核心组件测试
```
tests/jobmanager/
├── test_job_manager.py           # JobManager核心类测试
├── test_jobmanager_client.py     # 客户端类测试
├── test_job_manager_server.py    # 服务器端测试
├── test_job_info.py              # 作业信息管理测试
├── test_execution_graph.py       # 执行图管理测试
├── test_utils.py                 # 工具模块测试
├── test_integration.py           # 综合集成测试
├── test_runner.py                # 测试运行器
├── pytest.ini                    # 测试配置
└── README.md                     # 本文件
```

### 测试分类

#### 1. 单元测试 (`@pytest.mark.unit`)
- **test_job_manager.py**: JobManager类的所有功能
  - 单例模式测试
  - 作业提交、控制、状态查询
  - 生命周期管理
  - 错误处理

- **test_jobmanager_client.py**: 客户端功能
  - 初始化和连接管理
  - 请求构建和发送
  - 响应处理和错误恢复
  - 网络通信异常处理

- **test_job_manager_server.py**: 服务器端功能
  - TCP服务器生命周期
  - 请求路由和处理
  - 并发连接管理
  - 协议序列化/反序列化

- **test_job_info.py**: 作业信息管理
  - 作业元数据管理
  - 状态转换和验证
  - 进度跟踪
  - 序列化/持久化

- **test_execution_graph.py**: 执行图管理
  - 图构建和优化
  - 节点和边管理
  - 运行时上下文生成
  - 图验证和统计

- **test_utils.py**: 工具功能
  - 名称服务器功能
  - 端口分配和管理
  - 配置和注册表操作

#### 2. 集成测试 (`@pytest.mark.integration`)
- **test_integration.py**: 综合集成测试
  - 完整作业工作流程
  - 客户端-服务器通信
  - 多组件协同工作
  - 真实场景模拟

#### 3. 性能测试 (`@pytest.mark.slow` / `@pytest.mark.performance`)
- 高吞吐量作业提交
- 并发操作性能
- 内存使用和泄漏检测
- 网络通信性能

## 运行测试

### 使用测试运行器
```bash
# 运行所有单元测试
python test_runner.py unit

# 运行集成测试
python test_runner.py integration

# 运行所有测试
python test_runner.py all

# 运行性能测试
python test_runner.py performance

# 运行快速测试（排除慢速测试）
python test_runner.py quick

# 运行带覆盖率的测试
python test_runner.py coverage

# 运行特定关键字的测试
python test_runner.py all -k "job_submission"
```

### 直接使用pytest
```bash
# 运行所有JobManager测试
pytest tests/jobmanager/ -v

# 运行特定测试文件
pytest tests/jobmanager/test_job_manager.py -v

# 按标记运行测试
pytest tests/jobmanager/ -m "unit" -v
pytest tests/jobmanager/ -m "integration" -v

# 运行覆盖率测试
pytest tests/jobmanager/ --cov=sage.kernels.jobmanager --cov-report=html
```

## 测试覆盖范围

### 功能覆盖
- ✅ 作业生命周期管理（提交、执行、监控、控制）
- ✅ 分布式通信（客户端-服务器架构）
- ✅ 执行图构建和优化
- ✅ 作业信息持久化和查询
- ✅ 错误处理和恢复机制
- ✅ 并发控制和线程安全
- ✅ 资源管理和清理

### 质量目标
- **单元测试覆盖率**: ≥ 85%
- **集成测试覆盖率**: ≥ 70%
- **关键路径覆盖率**: = 100%
- **性能基准**: 符合SLA要求

---

**维护者**: SAGE开发团队  
**最后更新**: 2023年8月  
**测试覆盖率**: 85%+
