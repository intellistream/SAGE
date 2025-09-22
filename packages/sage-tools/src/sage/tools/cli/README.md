# SAGE 命令行界面 (CLI)

SAGE统一命令行工具，提供完整的作业管理、系统部署和集群管理功能。

## 🚀 快速开始

### 安装
```bash
python sage/cli/setup.py
```

### 基本命令
```bash
# 启动系统
sage deploy start

# 运行作业
sage job run your_script.py

# 查看作业
sage job list
sage job show 1

# 停止系统
sage deploy stop
```

## 📋 主要命令

### 作业管理 (`sage job`)
- `list` - 列出所有作业
- `show <job>` - 显示作业详情  
- `run <script>` - 运行Python脚本
- `stop <job>` - 停止作业
- `monitor` - 实时监控所有作业

### 系统部署 (`sage deploy`)
- `start` - 启动SAGE系统
- `stop` - 停止SAGE系统
- `status` - 显示系统状态
- `health` - 健康检查

### 集群管理 (`sage cluster`)
- `create` - 创建集群
- `scale` - 集群扩缩容
- `info` - 集群信息

## 🔄 迁移指南

从旧CLI迁移到新统一CLI：

| 旧命令 | 新命令 |
|--------|--------|
| `sage-jm list` | `sage job list` |
| `sage-jm show 1` | `sage job show 1` |
| `sage-deploy start` | `sage deploy start` |

## 📖 详细文档

更多详细的命令参考、配置选项和扩展开发，请参阅：

**[📚 CLI 完整参考文档](../../../docs-public/docs_src/tools/cli_reference.md)**

包含完整的：
- 所有命令的详细说明和参数
- 配置文件格式和选项
- 架构设计和组件说明
- 故障排除和性能优化
- 扩展开发和插件系统

# 启动系统
sage deploy start

# 检查健康状态
sage job health
```

### 配置问题
```bash
# 查看当前配置
sage config

# 手动编辑配置
vi ~/.sage/config.yaml
```

## 📚 示例

### 完整工作流程
```bash
# 1. 启动系统
sage deploy start

# 2. 检查健康状态
sage job health

# 3. 运行脚本
sage job run my_analysis.py --input data.csv

# 4. 监控作业
sage job monitor

# 5. 查看特定作业
sage job show 1

# 6. 停止作业（如需要）
sage job stop 1

# 7. 停止系统
sage deploy stop
```

### 批量操作
```bash
# 清理所有作业
sage job cleanup --force

# 重启系统
sage deploy restart

# 批量监控
sage job monitor --refresh 2
```

## 📁 核心组件

### [测试模块](./tests/)
完整的CLI功能测试覆盖，确保命令行工具的可靠性。

### 核心管理器

#### `main.py`
CLI主入口程序：
- 命令解析和路由
- 全局选项处理
- 错误处理和用户友好的错误信息
- 插件系统和扩展支持

#### `job.py`
作业管理命令：
- 作业提交和管理
- 作业状态查询和监控
- 作业生命周期控制
- 批量作业操作

#### `deploy.py`
部署管理命令：
- 系统启动和停止
- 服务健康检查
- 系统状态监控
- 配置管理

#### `cluster_manager.py`
集群管理器：
- 集群创建和销毁
- 节点管理和监控
- 资源分配和调度
- 集群扩缩容操作

#### `head_manager.py`
头节点管理器：
- 头节点服务启动
- 作业调度和分发
- 集群协调和通信
- 资源监控和报告

#### `worker_manager.py`
工作节点管理器：
- 工作节点注册和管理
- 任务执行和监控
- 资源使用报告
- 节点健康状态维护

#### `jobmanager_controller.py`
作业管理器控制器：
- JobManager服务控制
- 作业队列管理
- 作业优先级和依赖处理
- 状态同步和通知

#### `deployment_manager.py`
部署管理器：
- 部署策略和配置
- 服务生命周期管理
- 版本管理和回滚
- 环境隔离和资源管理

#### `config_manager.py`
配置管理器：
- 配置文件加载和解析
- 配置验证和合并
- 动态配置更新
- 配置模板和预设

#### `setup.py`
安装设置脚本：
- 环境依赖检查和安装
- CLI工具注册和配置
- 系统初始化和配置
- 权限设置和路径配置

## 🏗️ 架构设计

### 命令结构
```
sage
├── job          # 作业管理
│   ├── list
│   ├── show
│   ├── run
│   ├── stop
│   ├── monitor
│   └── ...
├── deploy       # 系统部署
│   ├── start
│   ├── stop
│   ├── status
│   └── ...
├── cluster      # 集群管理
│   ├── create
│   ├── scale
│   ├── info
│   └── ...
└── config       # 配置管理
    ├── show
    ├── set
    └── ...
```

### 组件交互
```
CLI Main
    ↓
Command Router
    ↓
Specific Manager (Job/Deploy/Cluster)
    ↓
SAGE Core Services
```

## 🔒 安全和权限

### 权限管理
- 基于角色的访问控制
- 用户身份验证
- 操作权限验证
- 审计日志记录

### 安全特性
- 配置文件加密
- 通信加密传输
- 敏感信息保护
- 安全的临时文件处理

## ⚡ 性能优化

### 响应速度
- 命令缓存机制
- 异步操作支持
- 批量操作优化
- 智能状态更新

### 资源效率
- 内存使用优化
- 网络请求合并
- 连接池管理
- 后台任务处理

## 🔧 扩展开发

### 自定义命令
```python
from sage.cli.base import BaseCommand

class CustomCommand(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--option', help='Custom option')
    
    def handle(self, args):
        # 实现自定义逻辑
        return result
```

### 插件系统
- 支持第三方命令插件
- 动态加载和注册
- 插件依赖管理
- 插件配置和参数

## 📊 监控和日志

### 实时监控
- 作业状态实时更新
- 系统资源监控
- 错误和异常追踪
- 性能指标收集

### 日志系统
- 结构化日志记录
- 多级日志输出
- 日志轮转和归档
- 远程日志聚合

## 🌐 多环境支持

### 环境配置
- 开发、测试、生产环境
- 环境隔离和切换
- 配置继承和覆盖
- 环境特定的默认值

### 部署模式
- 本地单机部署
- 分布式集群部署
- 容器化部署
- 云端部署

SAGE CLI致力于为用户提供简单、强大、可靠的命令行体验，让复杂的分布式计算变得触手可及。
