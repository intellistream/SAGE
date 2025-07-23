# SAGE 简化部署脚本说明

## 概述

我们已经简化了 `sage_deployment.sh` 脚本，整合了系统级安装功能，实现了"一键部署"的体验。

## 主要改进

### 🎯 **缺省行为**
当不带任何参数运行时，脚本会自动执行完整的部署流程：
```bash
./deployment/sage_deployment.sh
```

这个命令会：
1. **自动检测权限** - 检查是否有sudo/root权限
2. **系统级安装** - 创建sage用户组，安装CLI工具到系统路径
3. **设置权限** - 配置必要的目录和文件权限
4. **设置CLI工具** - 确保sage-jm命令可用
5. **启动系统** - 启动Ray集群和JobManager Daemon
6. **验证安装** - 检查所有组件是否正常工作

### 🚀 **核心功能**

#### 完整部署（缺省）
```bash
./deployment/sage_deployment.sh
# 或者
./deployment/sage_deployment.sh 
```

#### 仅启动系统
```bash
./deployment/sage_deployment.sh start
```

#### 系统状态检查
```bash
./deployment/sage_deployment.sh status
```

#### 停止系统
```bash
./deployment/sage_deployment.sh stop
```

#### 重启系统
```bash
./deployment/sage_deployment.sh restart
```

#### 仅执行系统级安装
```bash
sudo ./deployment/sage_deployment.sh install-system
```

### 🔧 **智能权限处理**

脚本会智能检测当前用户权限：

1. **Root用户** - 直接执行系统级安装
2. **有sudo权限** - 询问是否执行系统级安装
3. **无sudo权限** - 跳过系统级安装，使用开发模式

### 📁 **系统级安装路径**

系统级安装后的目录结构：
```
/usr/local/lib/sage/
├── jobmanager_controller.py
└── sage_jm_wrapper.sh

/usr/local/bin/
└── sage-jm -> /usr/local/lib/sage/sage_jm_wrapper.sh

/etc/sage/
├── environment.conf
└── config/

/var/log/sage/         # 日志目录
/var/lib/sage/         # 数据目录
```

### 👥 **用户组管理**

- 自动创建`sage`用户组
- 将系统中的普通用户加入sage组
- 设置适当的目录权限，允许sage组成员访问

### 🔄 **向后兼容**

- 保留了原有的所有功能模块
- 如果检测到现有的模块化脚本，会优先使用
- 提供简化的fallback实现，确保基本功能可用

## 使用示例

### 首次部署
```bash
# 完整部署（推荐）
./deployment/sage_deployment.sh

# 输出示例：
[INFO] === Starting SAGE Full Deployment ===
[INFO] Sudo available, performing system-level installation...
[WARNING] System-level installation requires sudo privileges
Proceed with system-level installation? [Y/n] y
[INFO] Executing system installation with sudo...
[INFO] === Performing System-Level Installation ===
[INFO] Creating sage group...
[SUCCESS] Created sage group
[INFO] Creating system directories...
[SUCCESS] Created system directories
[INFO] Installing SAGE files...
[SUCCESS] Files installed to system locations
[INFO] Setting up permissions...
[SUCCESS] Permissions set correctly
[INFO] Setting up CLI command...
[SUCCESS] CLI command 'sage-jm' installed
[INFO] Adding users to sage group...
[SUCCESS] Users added to sage group
[SUCCESS] === System-Level Installation Completed ===
[INFO] === Setting up permissions ===
[INFO] === Setting up CLI tools ===
[SUCCESS] System-level CLI installation detected
[SUCCESS] CLI tools setup completed
[INFO] === Starting SAGE System ===
[INFO] Starting Ray cluster...
[SUCCESS] Ray cluster started
[INFO] Starting JobManager Daemon...
[SUCCESS] JobManager Daemon started
[INFO] Verifying CLI tools...
[SUCCESS] CLI tools working correctly
[INFO] === System Status ===
[SUCCESS] Ray cluster: Running
[SUCCESS] JobManager Daemon: Running
[SUCCESS] CLI tools: Available (sage-jm)
[SUCCESS] === SAGE Full Deployment Completed ===
```

### 日常使用
```bash
# 检查状态
./deployment/sage_deployment.sh status

# 停止系统
./deployment/sage_deployment.sh stop

# 重启系统
./deployment/sage_deployment.sh restart
```

### CLI工具使用
```bash
# 系统级安装后，任何用户都可以使用
sage-jm --help
sage-jm status
sage-jm submit <job>
sage-jm list
```

## 故障排除

### 问题1：权限被拒绝
```bash
# 检查用户是否在sage组中
groups | grep sage

# 如果不在，重新登录或手动添加
sudo usermod -a -G sage $USER
# 然后重新登录
```

### 问题2：CLI命令不可用
```bash
# 检查符号链接
ls -l /usr/local/bin/sage-jm

# 重新执行系统安装
sudo ./deployment/sage_deployment.sh install-system
```

### 问题3：系统启动失败
```bash
# 检查详细状态
./deployment/sage_deployment.sh status

# 查看日志
tail -f /var/log/sage/*.log
```

## 与原版本的对比

| 功能 | 原版本 | 简化版本 |
|------|--------|----------|
| 缺省行为 | 显示帮助 | 完整部署 |
| 系统安装 | 需要单独脚本 | 自动整合 |
| 权限检查 | 手工处理 | 自动检测 |
| CLI设置 | 复杂步骤 | 一键完成 |
| 用户体验 | 需要多步骤 | 一步到位 |

## 建议

1. **生产环境**：直接运行 `./deployment/sage_deployment.sh`
2. **开发环境**：可以使用 `./deployment/sage_deployment.sh start` 跳过系统安装
3. **多用户环境**：确保执行完整部署以获得最佳权限配置

这个简化版本大大降低了SAGE的部署复杂度，同时保持了所有核心功能。
