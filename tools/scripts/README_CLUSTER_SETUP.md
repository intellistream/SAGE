# SAGE Cluster 快速配置指南

## 🚀 功能概览

本指南帮助你快速配置 SAGE 集群环境，包括：

1. **SSH 免密登录配置** - 自动配置 sage2, sage3, sage4 的免密登录
1. **Ray 版本自动同步** - 启动 worker 前自动检查并同步 Ray 版本

## 📋 前提条件

### 主机配置

- **Head 节点**: 当前机器
- **Worker 节点**: sage2, sage3, sage4
- **用户名**: sage
- **密码**: 123

### 网络要求

- 所有节点可互相访问
- SSH 端口开放（默认 22）

## 🔧 步骤 1: 配置 SSH 免密登录

### 自动配置（推荐）

```bash
cd /home/lpl/SAGE_dev
./tools/scripts/setup_ssh_keys.sh
```

脚本会自动：

1. 检查并安装 `sshpass` 工具
1. 生成 SSH 密钥对（如果不存在）
1. 将公钥复制到所有 worker 节点
1. 验证免密登录

### 手动配置

如果自动脚本失败，可以手动配置：

```bash
# 1. 生成 SSH 密钥（如果没有）
ssh-keygen -t rsa -b 4096

# 2. 为每个 worker 节点复制公钥
ssh-copy-id sage@sage2
ssh-copy-id sage@sage3
ssh-copy-id sage@sage4

# 3. 验证
ssh sage@sage2 'hostname'
ssh sage@sage3 'hostname'
ssh sage@sage4 'hostname'
```

## ✅ 步骤 2: 启动集群

配置完 SSH 免密登录后，启动集群：

```bash
sage cluster start
```

启动过程会自动：

1. 检查每个 worker 节点的 Ray 版本
1. 如果版本不一致，提示是否升级
1. 自动安装匹配的 Ray 版本
1. 启动所有节点

### 示例输出

```
🚀 启动Ray集群...
第1步: 启动Head节点
✅ Head节点启动成功

⏳ 等待Head节点完全启动...

第2步: 启动所有Worker节点
🚀 启动Ray Worker节点...

🔍 检查 Ray 版本一致性...
✅ sage2: Ray 版本一致 (2.9.0)
⚠️  sage3: Ray 版本不一致
   本地版本: 2.9.0
   远程版本: 2.8.0
是否将 sage3 的 Ray 升级到 2.9.0? [Y/n]: y
📦 在 sage3 上安装 Ray 2.9.0...
✅ 安装成功

✅ sage4: Ray 版本一致 (2.9.0)

🔧 启动Worker节点 1/3: sage2:22 (IP: 192.168.1.2)
✅ Worker节点启动成功

🔧 启动Worker节点 2/3: sage3:22 (IP: 192.168.1.3)
✅ Worker节点启动成功

🔧 启动Worker节点 3/3: sage4:22 (IP: 192.168.1.4)
✅ Worker节点启动成功

✅ Ray集群启动完成！
```

## 🛠️ 常用命令

### 集群管理

```bash
# 启动集群
sage cluster start

# 停止集群
sage cluster stop

# 重启集群
sage cluster restart

# 查看集群状态
sage cluster status

# 查看集群配置
sage cluster info
```

### 单独管理 Worker

```bash
# 启动所有 worker
sage cluster worker start

# 停止所有 worker
sage cluster worker stop

# 查看 worker 状态
sage cluster worker status
```

### Head 节点管理

```bash
# 启动 head 节点
sage cluster head start

# 停止 head 节点
sage cluster head stop

# 查看 head 节点状态
sage cluster head status
```

## 🔍 故障排查

### SSH 连接失败

```bash
# 测试 SSH 连接
ssh sage@sage2 'echo "Connection OK"'

# 检查 SSH 密钥权限
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub

# 检查 SSH 服务
ssh sage@sage2 'systemctl status sshd'
```

### Ray 版本不匹配

```bash
# 查看本地 Ray 版本
ray --version

# 查看远程 Ray 版本
ssh sage@sage2 'conda activate sage && ray --version'

# 手动升级远程 Ray
ssh sage@sage2 'conda activate sage && pip install ray==2.9.0'
```

### Worker 启动失败

```bash
# 查看 worker 日志
ssh sage@sage2 'cat /tmp/sage_worker_logs/worker.log'

# 手动启动 worker（调试）
ssh sage@sage2 'conda activate sage && ray start --address=<head-ip>:6379'

# 停止卡住的 Ray 进程
ssh sage@sage2 'ray stop'
```

## 📝 配置文件

配置文件位于项目根目录 `config/cluster.yaml`，直接编辑即可：

```bash
vi config/cluster.yaml
```

**配置示例：**

```yaml
cluster_name: sage-cluster

provider:
  type: local
  head_ip: 192.168.1.100
  worker_ips:
    - 192.168.1.101
    - 192.168.1.102
    - 192.168.1.103

auth:
  ssh_user: sage
  ssh_private_key: ~/.ssh/id_rsa
  connect_timeout: 10

ray:
  head_port: 6379
  dashboard_port: 8265

remote:
  conda_env: sage
  auto_sync_ray_version: true
```

## 🎯 最佳实践

1. **首次使用**：先配置 SSH 免密登录
1. **版本同步**：保持所有节点的 Ray 版本一致
1. **日志查看**：定期检查 `/tmp/sage_worker_logs/worker.log`
1. **资源监控**：通过 Ray Dashboard 监控集群状态（http://localhost:8265）
1. **清理进程**：出现问题时使用 `sage cluster stop` 完全清理

## 📚 更多资源

- Ray 文档: https://docs.ray.io/
- SAGE 文档: /home/lpl/SAGE_dev/README.md
- 集群管理脚本: /home/lpl/SAGE_dev/tools/scripts/
