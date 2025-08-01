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

### 单元测试
- 核心组件功能测试
- 边界条件和异常测试
- 接口兼容性测试
- 性能基准测试

### 集成测试
- 组件间交互测试
- 分布式环境测试
- 网络通信测试
- 数据同步测试

### 端到端测试
- 完整用户场景测试
- 系统负载测试
- 故障恢复测试
- 升级兼容性测试
