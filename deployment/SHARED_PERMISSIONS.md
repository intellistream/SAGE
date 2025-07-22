# SAGE 共享实验室环境权限管理指南

## 概述

SAGE系统现已支持实验室共享机器的权限管理。系统会自动检测用户是否在sudo组中，并应用相应的权限策略。

## 权限策略

### 对于sudo组用户（推荐）
- **所有者**: root:sudo
- **权限**: 775 (rwxrwxr-x) 目录权限，664 (rw-rw-r--) 文件权限
- **特性**: 
  - 所有sudo组用户都可以访问SAGE资源
  - 新创建的文件自动继承sudo组权限（setgid位）
  - 多用户可以同时使用SAGE系统

### 对于普通用户
- **所有者**: user:user
- **权限**: 755 (rwxr-xr-x) 目录权限，644 (rw-r--r--) 文件权限
- **特性**: 只有当前用户可以访问SAGE资源

## 使用方法

### 1. 启动系统（自动权限设置）
```bash
./sage_deployment.sh start
```

### 2. 手动修复所有权限
```bash
./sage_deployment.sh fix-permissions
```

### 3. 重新设置权限
```bash
./sage_deployment.sh setup-permissions
```

### 4. 独立权限修复脚本
```bash
./fix_permissions.sh
```

## 权限修复的目录

系统会自动处理以下目录的权限：

1. **Ray共享目录**: `/var/lib/ray_shared`
   - Ray集群的共享数据和会话信息
   
2. **SAGE临时目录**: `/tmp/sage`
   - PID文件和临时数据
   
3. **Ray会话目录**: `/tmp/ray`
   - Ray运行时会话数据
   
4. **SAGE日志目录**: `$SAGE_LOG_DIR` (默认: `$SAGE_HOME/logs`)
   - 系统日志文件

## 将用户添加到sudo组

如果用户不在sudo组中，建议管理员将其添加：

```bash
# 管理员执行
sudo usermod -a -G sudo <username>

# 用户需要重新登录或执行
newgrp sudo
```

## 故障排除

### 权限错误
如果遇到权限错误，运行：
```bash
./sage_deployment.sh fix-permissions
```

### 锁文件错误
如果遇到Ray锁文件错误：
```bash
# 清理旧的锁文件
find /var/lib/ray_shared -name "*.lock" -mtime +1 -delete
find /tmp/ray -name "*.lock" -mtime +1 -delete
```

### 检查当前权限状态
```bash
# 检查目录权限
ls -la /tmp/sage
ls -la /var/lib/ray_shared

# 检查用户组
groups
id
```

## 安全注意事项

1. **sudo组权限**: sudo组用户拥有系统管理权限，请确保只有可信用户在此组中
2. **共享访问**: 在共享环境中，sudo组中的所有用户都可以访问彼此的SAGE数据
3. **定期清理**: 建议定期清理旧的会话文件和日志

## 最佳实践

1. **统一环境**: 建议实验室所有SAGE用户都加入sudo组，使用统一的权限模式
2. **定期检查**: 定期运行 `./sage_deployment.sh fix-permissions` 确保权限正确
3. **监控日志**: 关注系统启动日志中的权限相关信息
4. **备份重要数据**: 在权限更改前备份重要的SAGE配置和数据

## 技术细节

### setgid位的作用
设置了setgid位(g+s)的目录，新创建的文件会继承目录的组所有权，确保所有sudo组用户都能访问。

### 权限继承
```bash
# 目录权限示例
drwxrwsr-x root sudo  # 's'表示setgid位已设置
```

这确保了在该目录中创建的文件自动属于sudo组。
