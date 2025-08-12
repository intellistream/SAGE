# 🚀 SAGE CLI 用户指南

SAGE 1.0.1 版本改进了CLI用户体验，现在提供更直观的独立命令！

## 📦 安装更新

```bash
# 升级到最新版本
pip install --upgrade isage-kernel

# 或安装完整框架
pip install --upgrade isage
```

## 🛠️ 新的CLI命令结构

### 🎯 主要改进

**之前**: `sage jobmanager start`  
**现在**: `sage-jobmanager start` ✨

这样用户可以利用shell的tab补全功能，输入 `sage-` 然后按Tab就能看到所有可用命令！

### 📋 完整命令列表

| 新命令 | 功能描述 | 示例用法 |
|--------|----------|----------|
| `sage-jobmanager` | JobManager 管理 | `sage-jobmanager start` |
| `sage-worker` | Worker 节点管理 | `sage-worker start --port 8080` |
| `sage-head` | Head 节点管理 | `sage-head start` |
| `sage-cluster` | 集群管理 | `sage-cluster status` |
| `sage-job` | 作业管理 | `sage-job submit my_job.py` |
| `sage-deploy` | 系统部署 | `sage-deploy start` |
| `sage-config` | 配置管理 | `sage-config show` |
| `sage-extensions` | 扩展管理 | `sage-extensions list` |

### 🔄 向后兼容

原来的 `sage` 统一命令仍然可用：

```bash
# 这些命令仍然有效
sage jobmanager start
sage worker start
sage cluster status
```

## 🎊 用户体验提升

### ✅ Tab 补全支持

```bash
$ sage-<TAB>
sage-cluster      sage-head         sage-worker
sage-config       sage-job          sage-deploy
sage-extensions   sage-jobmanager
```

### ✅ 更清晰的命令结构

每个组件都有独立的命令，便于记忆和使用：

```bash
# JobManager 操作
sage-jobmanager start
sage-jobmanager stop
sage-jobmanager restart
sage-jobmanager status

# Worker 操作  
sage-worker start --port 8080
sage-worker stop
sage-worker list

# 集群操作
sage-cluster start
sage-cluster stop
sage-cluster status
sage-cluster info
```

## 🔧 JobManager 快速上手

### 🚀 基础使用

JobManager是SAGE的核心服务，必须在使用RemoteEnvironment前启动：

```bash
# 1. 启动JobManager（默认端口19001）
sage-jobmanager start

# 2. 检查状态
sage-jobmanager status

# 3. 查看详细信息
sage-jobmanager info
```

### ⚙️ 高级配置

```bash
# 指定主机和端口
sage-jobmanager start --host 0.0.0.0 --port 19002

# 后台运行
sage-jobmanager start --daemon

# 详细日志输出
sage-jobmanager start --verbose
```

### 🛠️ 故障排除

```bash
# 强制重启（解决大部分问题）
sage-jobmanager restart --force

# 停止所有相关进程
sage-jobmanager kill

# 清理并重启
sage-jobmanager stop
sage-jobmanager start --clean
```

### 💡 常见使用场景

**开发阶段**：
```bash
# 启动开发环境
sage-jobmanager start --debug
# 运行您的SAGE代码
python your_script.py
```

**生产环境**：
```bash
# 启动生产服务
sage-jobmanager start --daemon --host 0.0.0.0
# 检查健康状态
sage-jobmanager health
```

**遇到问题**：
```bash
# 快速诊断
sage-jobmanager status
sage-jobmanager logs

# 完全重置
sage-jobmanager restart --force
```

## 🚀 快速上手

### 1. 启动 JobManager
```bash
sage-jobmanager start
```

### 2. 启动 Worker
```bash
sage-worker start --port 8080
```

### 3. 检查集群状态
```bash
sage-cluster status
```

### 4. 提交作业
```bash
sage-job submit my_analysis.py
```

### 5. 查看作业状态
```bash
sage-job list
sage-job status <job-id>
```

## 💡 最佳实践

### 🔧 开发环境设置

```bash
# 1. 启动开发集群
sage-cluster start --dev

# 2. 检查所有组件
sage-deploy status

# 3. 配置开发环境
sage-config set development true
```

### 🎯 生产环境部署

```bash
# 1. 部署生产集群
sage-deploy start --production

# 2. 验证部署
sage-cluster info
sage-jobmanager status
```

## 🆘 常见命令

```bash
# 查看帮助
sage-jobmanager --help
sage-worker --help
sage-cluster --help

# 检查版本
sage --version
sage-kernel --version

# 查看系统状态
sage-deploy status
sage-cluster info
```

---

**现在 SAGE CLI 更加用户友好了！** 🎉

试试 `sage-<Tab>` 来发现所有可用命令！
