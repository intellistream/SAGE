# SAGE 集群管理系统使用指南

## 概述

重构后的SAGE集群管理系统提供了统一、模块化的Ray集群管理功能，包括：

- **配置管理**: 统一的YAML配置文件管理
- **部署管理**: 自动化项目部署到远程节点
- **Head节点管理**: Ray集群头节点的启动、停止、监控
- **Worker节点管理**: Ray工作节点的管理和动态扩缩容
- **集群管理**: 整个集群的统一管理

## 快速开始

### 1. 配置文件设置

首先，确保您的配置文件 `~/.sage/config.yaml` 已正确设置：

```yaml
# Head节点配置
head:
  host: "base-sage"              # Head节点主机名
  head_port: 6379                # Ray集群端口
  dashboard_port: 8265           # Dashboard端口
  dashboard_host: "0.0.0.0"      # Dashboard绑定地址
  temp_dir: "/tmp/ray_head"      # 临时目录
  log_dir: "/tmp/sage_head_logs" # 日志目录

# Worker配置
worker:
  bind_host: "localhost"          # Worker绑定主机
  temp_dir: "/tmp/ray_worker"     # 临时目录
  log_dir: "/tmp/sage_worker_logs" # 日志目录

# Worker节点SSH主机列表
workers_ssh_hosts: "sage2:22,sage4:22"

# SSH配置
ssh:
  user: "sage"                    # SSH用户名
  key_path: "~/.ssh/id_rsa"      # SSH私钥路径
  connect_timeout: 10            # 连接超时

# 远程环境配置
remote:
  sage_home: "/home/sage"                        # 远程SAGE项目目录
  python_path: "/opt/conda/envs/sage/bin/python" # Python路径
  ray_command: "/opt/conda/envs/sage/bin/ray"    # Ray命令路径
  conda_env: "sage"                              # Conda环境名
```

### 2. 如果配置文件不存在，可以创建默认配置

```bash
# 运行配置管理器创建默认配置
python -m sage.cli.config_manager
```

## 命令使用指南

### 集群管理 (推荐使用)

集群管理提供了最便捷的统一管理方式：

```bash
# 查看集群配置信息
sage cluster info

# 部署SAGE到所有Worker节点
sage cluster deploy

# 启动整个集群 (Head + 所有Workers)
sage cluster start

# 检查集群状态
sage cluster status

# 停止整个集群
sage cluster stop

# 重启整个集群
sage cluster restart

# 动态扩容：添加新Worker节点
sage cluster scale add sage5:22

# 动态缩容：移除Worker节点
sage cluster scale remove sage5:22
```

### Head节点管理

```bash
# 启动Head节点
sage head start

# 停止Head节点
sage head stop

# 检查Head节点状态
sage head status

# 重启Head节点
sage head restart

# 查看Head节点日志
sage head logs --lines 50
```

### Worker节点管理

```bash
# 启动所有Worker节点
sage worker start

# 停止所有Worker节点
sage worker stop

# 检查所有Worker节点状态
sage worker status

# 重启所有Worker节点
sage worker restart

# 查看Worker配置
sage worker config

# 部署SAGE到所有Worker节点
sage worker deploy

# 添加新Worker节点
sage worker add sage5:22

# 移除Worker节点
sage worker remove sage5:22
```

### 配置管理

```bash
# 查看当前配置
sage config

# 或查看详细集群配置
sage cluster info
```

## 典型使用场景

### 场景1: 首次部署集群

```bash
# 1. 检查配置
sage cluster info

# 2. 部署SAGE到所有Worker节点
sage cluster deploy

# 3. 启动集群
sage cluster start

# 4. 验证集群状态
sage cluster status
```

### 场景2: 日常集群管理

```bash
# 启动集群
sage cluster start

# 检查状态
sage cluster status

# 访问Dashboard (浏览器访问)
# http://base-sage:8265

# 停止集群
sage cluster stop
```

### 场景3: 动态扩缩容

```bash
# 添加新的Worker节点
sage cluster scale add new-worker:22

# 检查新节点状态
sage cluster status

# 如果需要移除节点
sage cluster scale remove new-worker:22
```

### 场景4: 故障排查

```bash
# 检查集群状态
sage cluster status

# 检查Head节点详细状态
sage head status

# 检查Worker节点状态
sage worker status

# 查看Head节点日志
sage head logs --lines 100

# 重启有问题的组件
sage head restart
# 或
sage worker restart
```

### 场景5: 更新部署

```bash
# 停止集群
sage cluster stop

# 重新部署更新
sage cluster deploy

# 启动集群
sage cluster start
```

## 高级功能

### 1. 单独管理Head和Worker

如果需要精细控制，可以分别管理：

```bash
# 先启动Head节点
sage head start

# 等待Head节点完全启动
sleep 5

# 再启动Worker节点
sage worker start
```

### 2. 检查特定组件

```bash
# 只检查Head节点
sage head status

# 只检查Worker节点
sage worker status
```

### 3. 查看详细日志

```bash
# Head节点日志
sage head logs --lines 50

# Worker节点日志需要SSH到具体节点查看
# 或通过Ray Dashboard查看
```

## 配置说明

### Head节点配置选项

- `host`: Head节点的主机名或IP地址
- `head_port`: Ray集群监听端口 (默认6379)
- `dashboard_port`: Ray Dashboard端口 (默认8265)
- `dashboard_host`: Dashboard绑定地址 (0.0.0.0表示所有接口)
- `temp_dir`: Ray临时文件目录
- `log_dir`: 日志文件目录

### Worker节点配置选项

- `bind_host`: Worker节点绑定的IP地址 (localhost表示使用主机名)
- `temp_dir`: Ray临时文件目录
- `log_dir`: 日志文件目录

### SSH配置选项

- `user`: SSH登录用户名
- `key_path`: SSH私钥文件路径
- `connect_timeout`: SSH连接超时时间

### 远程环境配置

- `sage_home`: 远程节点上SAGE项目的安装目录
- `python_path`: 远程Python解释器路径
- `ray_command`: 远程Ray命令路径
- `conda_env`: 要激活的Conda环境名称

## 注意事项

1. **SSH密钥**: 确保SSH私钥已正确配置，可以无密码登录到所有Worker节点
2. **网络连通性**: Head节点和Worker节点之间网络要互通
3. **端口开放**: 确保Ray相关端口 (6379, 8265等) 在防火墙中开放
4. **权限**: 确保用户有权限在指定目录创建文件和启动进程
5. **环境一致性**: 所有节点的Python和Ray版本应该一致

## 故障排查

### 常见问题

1. **SSH连接失败**
   ```bash
   # 检查SSH连接
   ssh -i ~/.ssh/id_rsa sage@sage2
   ```

2. **Ray启动失败**
   ```bash
   # 检查Ray命令是否可用
   /opt/conda/envs/sage/bin/ray --help
   ```

3. **端口被占用**
   ```bash
   # 检查端口占用
   netstat -tlnp | grep 6379
   ```

4. **权限问题**
   ```bash
   # 检查目录权限
   ls -la /tmp/ray_*
   ```

## 获取帮助

```bash
# 查看主命令帮助
sage --help

# 查看子命令帮助
sage cluster --help
sage head --help
sage worker --help
```

## 开发和扩展

如果需要修改配置或扩展功能，相关文件位置：

- 配置管理: `sage/cli/config_manager.py`
- 部署管理: `sage/cli/deployment_manager.py`
- Head管理: `sage/cli/head_manager.py`
- Worker管理: `sage/cli/worker_manager.py`
- 集群管理: `sage/cli/cluster_manager.py`
- 配置模板: `config/cluster_config_template.yaml`
