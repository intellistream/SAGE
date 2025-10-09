# SAGE JobManager工具模块

JobManager工具模块提供作业管理器相关的辅助工具和服务。

## 模块概述

本模块包含JobManager系统运行所需的各种工具和辅助服务，支持作业管理器的核心功能。

## 核心组件

### `name_server.py`
名称服务器：
- 提供服务发现和注册功能
- 管理分布式环境中的服务地址
- 支持服务健康检查和故障转移
- 提供负载均衡和路由功能
- 包含服务元数据管理

## 主要特性

- **服务发现**: 自动发现和注册服务
- **健康监控**: 持续监控服务健康状态
- **负载均衡**: 智能的请求分发和负载均衡
- **故障恢复**: 自动的故障检测和恢复机制
- **高可用性**: 支持多实例部署和热备份

## 使用场景

- **分布式服务管理**: 管理分布式环境中的各种服务
- **服务路由**: 为客户端提供服务路由和发现
- **系统监控**: 监控分布式系统的健康状态
- **故障恢复**: 自动处理服务故障和恢复

## 快速开始

```python
from sage.kernels.jobmanager.utils.name_server import NameServer

# 创建名称服务器
name_server = NameServer(host="localhost", port=8080)

# 注册服务
name_server.register_service("jobmanager", "localhost:9001")
name_server.register_service("worker", "localhost:9002")

# 发现服务
jobmanager_addr = name_server.discover_service("jobmanager")
worker_addrs = name_server.discover_services("worker")

# 启动服务器
name_server.start()
```

## 配置选项

- `host`: 服务器绑定地址
- `port`: 服务器监听端口
- `health_check_interval`: 健康检查间隔
- `service_timeout`: 服务超时时间
- `max_retries`: 最大重试次数
