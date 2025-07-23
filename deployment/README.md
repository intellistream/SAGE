# SAGE Deployment Scripts - 模块化部署脚本

这个目录包含了SAGE系统的模块化部署脚本，提供了完整的系统管理功能。

## 目录结构

```
deployment/
├── sage_deployment.sh         # 原始单体脚本（保留）
├── sage_deployment.sh      # 新的模块化主脚本
├── jobmanager_controller.py   # JobManager控制器
├── jobmanager_daemon.py       # JobManager守护进程
├── config/                    # 配置文件
│   ├── environment.sh         # 环境变量配置
│   └── default.conf          # 默认配置
├── scripts/                   # 功能模块脚本
│   ├── common.sh             # 公共函数库
│   ├── ray_manager.sh        # Ray集群管理
│   ├── daemon_manager.sh     # 守护进程管理
│   ├── permission_manager.sh # 权限管理
│   ├── cli_manager.sh        # CLI工具管理
│   ├── health_checker.sh     # 健康检查
│   └── system_utils.sh       # 系统工具
└── templates/                 # 配置模板
    └── systemd/              # systemd服务模板
```

## 快速开始

### 启动系统

```bash
# 启动完整的SAGE系统（新版本）
./sage_deployment.sh start

# 或使用原始脚本
./sage_deployment.sh start
```

### 检查状态

```bash
# 检查系统状态
./sage_deployment.sh status

# 执行健康检查
./sage_deployment.sh health
```

### 停止系统

```bash
# 停止完整系统
./sage_deployment.sh stop
```

## 功能模块说明

### 1. common.sh - 公共函数库
- 日志输出函数
- 端口检查工具
- PID文件管理
- 基础工具函数

### 2. ray_manager.sh - Ray集群管理
- Ray head节点启动/停止
- Ray权限设置
- Ray状态检查
- Ray配置管理

### 3. daemon_manager.sh - 守护进程管理  
- JobManager守护进程生命周期管理
- 健康状态检查
- 日志管理

### 4. permission_manager.sh - 权限管理
- 系统目录权限设置
- Ray session权限管理
- 权限验证

### 5. cli_manager.sh - CLI工具管理
- sage-jm命令安装
- CLI工具状态检查
- 使用指南显示

### 6. health_checker.sh - 健康检查
- 系统依赖检查
- Python环境检查  
- 服务健康监控
- 实时状态监控

### 7. system_utils.sh - 系统工具
- 系统信息收集
- 日志收集
- 性能测试
- 系统诊断

## 命令参考

### 系统管理命令

```bash
./sage_deployment.sh start          # 启动系统
./sage_deployment.sh stop           # 停止系统  
./sage_deployment.sh restart        # 重启系统
./sage_deployment.sh status         # 显示状态
./sage_deployment.sh health         # 健康检查
./sage_deployment.sh monitor [间隔] # 实时监控
```

### CLI工具管理

```bash
./sage_deployment.sh install-cli    # 安装CLI工具
./sage_deployment.sh uninstall-cli  # 卸载CLI工具
./sage_deployment.sh check-cli      # 检查CLI状态
```

### 单独组件管理

```bash
./sage_deployment.sh start-ray      # 仅启动Ray
./sage_deployment.sh stop-ray       # 仅停止Ray
./sage_deployment.sh start-daemon   # 仅启动守护进程
./sage_deployment.sh stop-daemon    # 仅停止守护进程
```

### 系统诊断和维护

```bash
./sage_deployment.sh diagnose       # 系统诊断
./sage_deployment.sh collect-logs   # 收集日志
./sage_deployment.sh cleanup        # 清理临时文件
./sage_deployment.sh report         # 生成系统报告
./sage_deployment.sh performance    # 性能测试
```

## 环境变量

可以通过环境变量自定义配置：

```bash
export RAY_HEAD_PORT=10001           # Ray GCS端口
export RAY_CLIENT_PORT=10002         # Ray客户端端口
export RAY_DASHBOARD_PORT=8265       # Ray仪表板端口
export DAEMON_HOST=127.0.0.1         # 守护进程主机
export DAEMON_PORT=19001             # 守护进程端口
export SAGE_LOG_DIR=/path/to/logs    # 日志目录
```

## 从原始脚本升级

从原始单体脚本升级到模块化版本：

1. **兼容性**: 原始脚本 `./sage_deployment.sh` 仍然可用
2. **新功能**: 新脚本 `./sage_deployment.sh` 提供更多功能
3. **配置**: 环境变量完全兼容，无需修改
4. **增强**: 新增诊断、监控、日志收集等功能

## 故障排除

### 端口冲突
```bash
export RAY_HEAD_PORT=10011
export RAY_DASHBOARD_PORT=8275
./sage_deployment.sh start
```

### 权限问题
```bash
./sage_deployment.sh diagnose
# 或手动修复
sudo chmod 1777 /var/lib/ray_shared
```

### 查看详细日志
```bash
# 收集所有日志
./sage_deployment.sh collect-logs

# 实时监控
./sage_deployment.sh monitor 3
```

---

## 原始部署说明 (如何架设 SAGE 集群)