# SAGE CLI

SAGE Framework 的命令行工具包，提供集群管理、作业部署和配置管理功能。

## 功能特性

### 🚀 核心功能
- **集群管理**: Ray 集群的启动、停止和监控
- **作业管理**: SAGE 作业的提交、监控和管理  
- **部署管理**: 系统组件的一键部署和配置
- **配置管理**: 统一的配置文件管理和环境设置

### 📋 命令概览
- `sage config` - 配置管理
- `sage deploy` - 系统部署
- `sage job` - 作业管理
- `sage cluster` - 集群管理
- `sage worker` - Worker 节点管理
- `sage head` - Head 节点管理

## 安装

```bash
pip install intsage-cli
```

### 开发安装
```bash
pip install intsage-cli[dev]
```

### 完整功能安装
```bash
pip install intsage-cli[full]
```

## 快速开始

### 1. 初始化配置
```bash
sage config init
```

### 2. 启动 SAGE 系统
```bash
sage deploy start
```

### 3. 检查系统状态
```bash
sage cluster status
```

### 4. 提交作业
```bash
sage job submit my_job.py
```

## 命令参考

### 配置管理 (`sage config`)
```bash
# 显示所有配置
sage config show

# 设置配置项
sage config set ray.head_port 10001

# 获取配置项
sage config get ray.head_port
```

### 部署管理 (`sage deploy`)
```bash
# 启动完整系统 (Ray + JobManager)
sage deploy start

# 仅启动 Ray 集群
sage deploy start --ray-only

# 仅启动 JobManager
sage deploy start --daemon-only

# 停止系统
sage deploy stop
```

### 集群管理 (`sage cluster`)
```bash
# 查看集群状态
sage cluster status

# 启动集群
sage cluster start

# 停止集群
sage cluster stop

# 重启集群
sage cluster restart
```

### 作业管理 (`sage job`)
```bash
# 提交作业
sage job submit script.py

# 查看作业状态
sage job status [job_id]

# 列出所有作业
sage job list

# 取消作业
sage job cancel job_id

# 查看作业日志
sage job logs job_id
```

## 配置文件

CLI 工具使用 `~/.sage/config.yaml` 作为默认配置文件：

```yaml
ray:
  head_port: 10001
  dashboard_port: 8265
  object_store_memory: 1000000000

jobmanager:
  port: 8080
  max_jobs: 100

deployment:
  log_level: INFO
  auto_scaling: true
```

## 环境变量

- `SAGE_CONFIG_PATH`: 自定义配置文件路径
- `SAGE_LOG_LEVEL`: 日志级别 (DEBUG, INFO, WARNING, ERROR)
- `RAY_ADDRESS`: Ray 集群地址
- `SAGE_HOME`: SAGE 安装目录

## 开发

### 项目结构
```
src/sage/cli/
├── __init__.py              # CLI 模块初始化
├── main.py                  # 主命令入口点
├── config_manager.py        # 配置管理
├── deploy.py               # 部署管理
├── job.py                  # 作业管理  
├── cluster_manager.py      # 集群管理
├── worker_manager.py       # Worker 管理
├── head_manager.py         # Head 节点管理
├── jobmanager_controller.py # JobManager 控制器
└── extensions.py           # 扩展管理
```

### 运行测试
```bash
pytest tests/
```

### 代码格式化
```bash
black src/sage/cli/
ruff check src/sage/cli/
```

## 许可证

MIT License - 详见 [LICENSE](../../LICENSE) 文件。

## 贡献

欢迎贡献代码！请查看 [CONTRIBUTING.md](../../CONTRIBUTING.md) 了解详细指南。

## 支持

- 📖 [文档](https://intellistream.github.io/SAGE-Pub/)
- 🐛 [问题报告](https://github.com/intellistream/SAGE/issues)
- 💬 [讨论](https://github.com/intellistream/SAGE/discussions)
