# SAGE CLI测试

SAGE命令行工具的完整测试套件，确保CLI功能的正确性和可靠性。

## 测试概述

本目录包含对SAGE CLI所有组件的测试，覆盖作业管理、系统部署、集群管理等核心功能。

## 测试文件

### `test_main.py`
主程序测试：
- CLI主入口功能测试
- 命令解析和路由测试
- 全局选项和配置测试
- 错误处理和异常测试

### `test_job.py`
作业管理测试：
- 作业创建和提交测试
- 作业状态管理测试
- 作业生命周期测试
- 作业监控和日志测试

### `test_deployment_manager.py`
部署管理器测试：
- 系统部署和启动测试
- 服务管理和配置测试
- 部署策略和回滚测试
- 健康检查和监控测试

### `test_cluster_manager.py`
集群管理器测试：
- 集群创建和管理测试
- 节点添加和删除测试
- 集群状态监控测试
- 故障检测和恢复测试

### `test_head_manager.py`
头节点管理器测试：
- 头节点启动和配置测试
- 作业调度和分发测试
- 资源管理和分配测试
- 集群协调和通信测试

### `test_worker_manager.py`
工作节点管理器测试：
- 工作节点注册和管理测试
- 任务执行和监控测试
- 资源使用和报告测试
- 节点故障和恢复测试

### `test_jobmanager.py`
作业管理器测试：
- 作业管理器核心功能测试
- 作业队列和调度测试
- 作业依赖和优先级测试
- 作业状态同步测试

### `test_config_manager.py`
配置管理器测试：
- 配置加载和解析测试
- 配置验证和合并测试
- 动态配置更新测试
- 配置备份和恢复测试

### `test_setup.py`
安装设置测试：
- 依赖安装和检查测试
- 环境配置和初始化测试
- 系统要求验证测试
- 安装过程异常处理测试

## 测试数据

### 配置文件
- 各种配置文件模板
- 错误配置用例
- 边界条件配置
- 多环境配置样本

### 作业脚本
- 测试作业脚本集合
- 不同类型的计算任务
- 错误脚本和异常情况
- 性能测试脚本

### 模拟环境
- 模拟集群环境
- 虚拟网络配置
- 资源使用模拟
- 故障场景模拟

## 运行测试

```bash
# 运行所有CLI测试
python -m pytest sage/cli/tests/

# 运行特定组件测试
python -m pytest sage/cli/tests/test_job.py
python -m pytest sage/cli/tests/test_deployment_manager.py

# 运行集成测试
python -m pytest sage/cli/tests/ -m "integration"

# 运行端到端测试
python -m pytest sage/cli/tests/ -m "e2e"
```

## 测试环境

### 依赖服务
- Docker容器环境
- 模拟Ray集群
- 本地文件系统
- 网络服务模拟

### 环境变量
```bash
export SAGE_TEST_MODE=true
export SAGE_CONFIG_PATH=test_configs/
export SAGE_LOG_LEVEL=DEBUG
```

## 测试覆盖率

目标测试覆盖率：
- 单元测试覆盖率 > 85%
- 集成测试覆盖主要流程
- 异常处理测试完整
- 用户场景测试全面

## 性能测试

### 响应时间
- 命令响应时间 < 1秒
- 作业提交延迟 < 5秒
- 集群启动时间 < 30秒
- 状态查询响应 < 100ms

### 并发测试
- 多用户并发操作
- 大量作业同时提交
- 集群扩缩容测试
- 高负载场景测试

## 持续集成

- 自动化测试执行
- 多环境兼容性测试
- 性能回归检测
- CLI功能完整性验证
