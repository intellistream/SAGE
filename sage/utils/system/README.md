# SAGE 系统工具模块

本模块提供系统级别的工具函数，包括环境管理、网络操作和进程控制等功能。

## 概述

系统工具模块封装了SAGE框架需要的各种系统级操作，提供跨平台兼容的系统交互能力。

## 核心组件

### `environment_utils.py`
环境管理工具：
- 环境变量读取和设置
- 系统路径管理
- 配置文件处理
- 平台兼容性检查
- 环境初始化和清理

### `network_utils.py`
网络操作工具：
- 端口可用性检查
- 网络连接测试
- IP地址获取和验证
- 网络配置管理
- 服务发现功能

### `process_utils.py`
进程控制工具：
- 进程启动和管理
- 进程状态监控
- 进程间通信
- 资源使用监控
- 进程清理和回收

## 主要特性

- **跨平台兼容**: 支持Windows、Linux、macOS
- **异常处理**: 完善的错误处理和恢复机制
- **性能监控**: 提供资源使用情况监控
- **安全性**: 安全的系统操作封装

## 使用场景

- **环境配置**: 自动检测和配置运行环境
- **服务部署**: 网络服务启动和管理
- **资源监控**: 系统资源使用情况监控
- **进程管理**: 分布式环境下的进程协调

## 快速开始

```python
# 环境工具
from sage.utils.system.environment_utils import EnvironmentUtils

env_utils = EnvironmentUtils()
python_path = env_utils.get_python_path()
config_dir = env_utils.get_config_directory()

# 网络工具
from sage.utils.system.network_utils import NetworkUtils

net_utils = NetworkUtils()
available_port = net_utils.find_free_port()
is_reachable = net_utils.check_connection("example.com", 80)

# 进程工具
from sage.utils.system.process_utils import ProcessUtils

proc_utils = ProcessUtils()
process = proc_utils.start_process(["python", "script.py"])
status = proc_utils.get_process_status(process.pid)
```

## 工具函数

### 环境管理
- `get_system_info()`: 获取系统信息
- `setup_environment()`: 初始化环境配置
- `load_config()`: 加载配置文件
- `validate_dependencies()`: 检查依赖项

### 网络操作
- `find_free_port()`: 查找可用端口
- `check_port_in_use()`: 检查端口占用
- `get_local_ip()`: 获取本机IP地址
- `test_connectivity()`: 测试网络连通性

### 进程控制
- `start_daemon()`: 启动守护进程
- `kill_process_tree()`: 终止进程树
- `monitor_resources()`: 监控资源使用
- `cleanup_processes()`: 清理僵尸进程

## 配置选项

支持通过配置文件或环境变量进行定制：
- 超时设置
- 重试策略
- 日志级别
- 安全策略
