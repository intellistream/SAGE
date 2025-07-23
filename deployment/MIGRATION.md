# SAGE Deployment Migration Guide
# SAGE 部署迁移指南

## 从单体脚本迁移到模块化版本

### 旧脚本 → 新脚本映射

| 旧脚本/功能 | 新命令 | 说明 |
|-------------|--------|------|
| `./sage_deployment.sh start` | `./sage_deployment.sh start` | 启动系统 |
| `./sage_deployment.sh stop` | `./sage_deployment.sh stop` | 停止系统 |
| `./sage_deployment.sh status` | `./sage_deployment.sh status` | 查看状态 |
| `./fix_ray_permissions.sh` | `./sage_deployment.sh fix-ray-permissions` | 修复Ray权限 |

### 新增功能

新的模块化版本提供了许多增强功能：

```bash
# 健康检查
./sage_deployment.sh health

# 实时监控
./sage_deployment.sh monitor

# 系统诊断
./sage_deployment.sh diagnose

# 日志收集
./sage_deployment.sh collect-logs

# 独立组件管理
./sage_deployment.sh start-ray
./sage_deployment.sh stop-daemon
./sage_deployment.sh restart-ray

# 权限修复（集成了 fix_ray_permissions.sh）
./sage_deployment.sh fix-ray-permissions
```

### 兼容性保证

- ✅ 环境变量完全兼容
- ✅ 原始脚本继续可用  
- ✅ 配置文件位置不变
- ✅ 日志格式保持一致

### 迁移步骤

1. **测试新脚本**
   ```bash
   # 先测试状态查看
   ./sage_deployment.sh status
   
   # 测试健康检查
   ./sage_deployment.sh health
   ```

2. **逐步切换**
   ```bash
   # 停止旧系统
   ./sage_deployment.sh stop
   
   # 启动新系统
   ./sage_deployment.sh start
   ```

3. **验证功能**
   ```bash
   # 验证所有组件正常
   ./sage_deployment.sh diagnose
   ```

### 弃用通知

以下脚本已标记为弃用但仍可使用：

- `fix_ray_permissions.sh` → 使用 `./sage_deployment.sh fix-ray-permissions`

### 回滚方案

如果需要回滚到旧版本：

```bash
# 停止新系统
./sage_deployment.sh stop

# 启动旧系统
./sage_deployment.sh start
```

### 获取帮助

```bash
# 查看所有新命令
./sage_deployment.sh help

# 查看特定命令帮助
./sage_deployment.sh diagnose --help
```
