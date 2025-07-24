# SAGE 系统级安装指南

## 概述

本指南介绍如何在多用户环境下进行SAGE系统的系统级安装，解决权限问题并确保所有用户都能正常使用SAGE CLI工具。

## 问题背景

之前的安装方式存在以下问题：
- CLI工具符号链接指向用户特定路径（如 `/home/zrc/develop_item/T-SAGE/SAGE/deployment/sage_jm_wrapper.sh`）
- 多用户环境下权限冲突
- 不同用户之间无法共享SAGE工具

## 解决方案

### 系统级目录结构

安装后的系统级目录结构：
```
/usr/local/lib/sage/          # SAGE库文件
├── jobmanager_controller.py  # JobManager控制器
└── sage_jm_wrapper.sh        # CLI包装脚本

/usr/local/bin/
└── sage-jm -> /usr/local/lib/sage/sage_jm_wrapper.sh  # CLI命令符号链接

/etc/sage/                    # 配置文件
├── environment.conf          # 环境配置
└── config/                   # 其他配置文件

/var/log/sage/                # 日志目录
/var/lib/sage/                # 数据目录
```

### 权限模型

- 创建`sage`用户组
- 所有SAGE相关文件属于`root:sage`
- 日志和数据目录允许sage组写入
- 自动将系统用户添加到sage组

## 安装步骤

### 1. 系统级安装

运行系统级安装脚本：
```bash
sudo ./deployment/install_system.sh
```

这个脚本会：
- 创建`sage`用户组
- 创建必要的系统目录
- 复制文件到系统位置
- 设置正确的权限
- 创建CLI命令符号链接
- 将用户添加到sage组

### 2. 验证安装

安装完成后，用户需要重新登录以使组权限生效，然后验证：
```bash
# 检查sage-jm命令是否可用
sage-jm --help

# 检查用户是否在sage组中
groups | grep sage

# 查看符号链接
ls -l /usr/local/bin/sage-jm
```

### 3. 开发环境安装

如果是开发环境，仍然可以使用原有的部署脚本：
```bash
./deployment/sage_deployment.sh start
```

修改后的脚本会检测是否已有系统级安装，并优先使用系统级安装。

## 卸载

如需卸载系统级安装：
```bash
sudo ./deployment/uninstall_system.sh
```

这个脚本会：
- 删除CLI符号链接
- 删除系统文件
- 询问是否删除配置、日志和数据目录
- 询问是否删除sage用户组

## 文件修改说明

### 1. `sage_jm_wrapper.sh`

修改了路径检测逻辑：
- 检测是否在系统安装路径下
- 支持从多个可能的位置查找SAGE项目根目录
- 向后兼容开发环境

### 2. `install_system.sh` (新增)

完整的系统级安装脚本：
- 创建用户组和目录
- 复制文件并设置权限
- 配置CLI工具
- 验证安装

### 3. `uninstall_system.sh` (新增)

完整的系统级卸载脚本：
- 安全删除系统文件
- 可选保留用户数据
- 验证卸载结果

### 4. `cli_manager.sh`

更新了CLI工具设置：
- 检测系统级安装
- 优先使用系统级CLI工具
- 向后兼容开发环境

### 5. `setup.py`

添加了setuptools的entry_points支持，为将来的pip安装做准备。

## 最佳实践

1. **生产环境**：使用系统级安装
2. **开发环境**：可以使用开发安装或系统级安装
3. **多用户环境**：必须使用系统级安装
4. **权限管理**：通过sage用户组管理访问权限

## 故障排除

### 问题1：sage-jm命令不可用
```bash
# 检查符号链接
ls -l /usr/local/bin/sage-jm

# 检查PATH
echo $PATH | grep /usr/local/bin

# 重新登录或source环境
source ~/.bashrc
```

### 问题2：权限被拒绝
```bash
# 检查用户组
groups

# 如果不在sage组中，添加用户到组
sudo usermod -a -G sage $USER

# 重新登录使组权限生效
```

### 问题3：找不到SAGE项目根目录
```bash
# 检查可能的位置
ls -d /opt/sage /usr/local/share/sage $HOME/SAGE 2>/dev/null

# 如果需要，创建符号链接
sudo ln -s /path/to/your/sage/project /opt/sage
```

## 升级

要升级系统级安装：
1. 先卸载旧版本：`sudo ./deployment/uninstall_system.sh`
2. 安装新版本：`sudo ./deployment/install_system.sh`

或者直接覆盖安装（保留配置和数据）：
```bash
sudo ./deployment/install_system.sh
```
