# SAGE CLI 用户指南

## 🚀 简化的命令行工具

SAGE 现在提供了更用户友好的独立CLI命令，支持shell tab补全：

### 🎯 主要命令

```bash
# JobManager 管理
sage-jobmanager start    # 启动 JobManager
sage-jobmanager stop     # 停止 JobManager  
sage-jobmanager status   # 查看状态
sage-jobmanager restart  # 重启

# 作业管理
sage-job submit          # 提交作业
sage-job list            # 列出作业
sage-job status          # 查看作业状态
sage-job kill            # 终止作业

# 集群管理
sage-cluster start       # 启动集群
sage-cluster stop        # 停止集群
sage-cluster status      # 集群状态
sage-cluster scale       # 扩缩容

# Worker 节点管理
sage-worker start        # 启动 Worker
sage-worker stop         # 停止 Worker
sage-worker list         # 列出 Worker

# Head 节点管理
sage-head start          # 启动 Head 节点
sage-head stop           # 停止 Head 节点
sage-head status         # Head 节点状态

# 部署管理
sage-deploy start        # 启动部署
sage-deploy stop         # 停止部署
sage-deploy status       # 部署状态

# 配置管理
sage-config show         # 显示配置
sage-config set          # 设置配置
sage-config reset        # 重置配置

# 扩展管理
sage-extensions list     # 列出扩展
sage-extensions install  # 安装扩展
sage-extensions enable   # 启用扩展
```

### ✅ 优势

1. **Tab补全支持**: 用户可以使用 `sage-<TAB>` 来查看所有可用命令
2. **独立命令**: 每个组件都有独立的命令，更直观
3. **向后兼容**: 原来的 `sage` 统一命令仍然可用
4. **更好的用户体验**: 命令名称直接对应功能

### 🔄 从统一命令迁移

#### 旧方式 ➡️ 新方式

```bash
# 旧方式（仍然支持）
sage jobmanager start

# 新方式（推荐）
sage-jobmanager start
```

### 💡 快速开始

```bash
# 1. 启动 JobManager
sage-jobmanager start

# 2. 启动集群
sage-cluster start

# 3. 提交作业
sage-job submit my_job.py

# 4. 查看状态
sage-job status
sage-cluster status
```

### 🛠️ 开发者工具

```bash
# 安装开发工具包
pip install intsage-dev-toolkit

# 使用开发工具
sage-dev test
sage-dev analyze
sage-dev package
```

### 📚 详细帮助

每个命令都支持详细的帮助信息：

```bash
sage-jobmanager --help
sage-job --help  
sage-cluster --help
# ...等等
```

---

**现在SAGE CLI更加用户友好了！** 🎉
