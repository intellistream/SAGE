# JobManager 启动故障排除

## 🚨 常见启动问题

### 1. 启动命令失败

**问题描述**：执行 `sage jobmanager start` 命令失败

**错误示例**：
```bash
$ sage jobmanager start
Error: JobManager failed to start. Port 19001 already in use.
```

**解决方案**：

1. **检查是否已经启动**
   ```bash
   sage jobmanager status
   ```

2. **停止现有实例**
   ```bash
   sage jobmanager stop
   sleep 3
   sage jobmanager start
   ```

3. **强制重启**
   ```bash
   sage jobmanager restart --force
   ```

### 2. 端口冲突

**问题描述**：默认端口 19001 被占用

**解决方案**：

1. **查找占用端口的进程**
   ```bash
   # Linux/Mac
   sudo lsof -i :19001
   sudo netstat -tlnp | grep 19001
   
   # Windows  
   netstat -ano | findstr :19001
   ```

2. **终止占用进程**
   ```bash
   # 根据PID终止进程
   sudo kill -9 <PID>
   
   # 或者终止所有相关进程
   sudo pkill -f jobmanager
   ```

3. **使用其他端口**
   ```bash
   sage jobmanager start --port 19002
   
   # 永久配置
   echo "SAGE_JOBMANAGER_PORT=19002" >> ~/.sage/config
   ```

### 3. 权限问题

**问题描述**：没有权限绑定端口或创建文件

**错误示例**：
```
PermissionError: [Errno 13] Permission denied: bind
```

**解决方案**：

1. **使用非特权端口 (>1024)**
   ```bash
   sage jobmanager start --port 8001
   ```

2. **检查文件权限**
   ```bash
   # 确保配置目录权限正确
   mkdir -p ~/.sage
   chmod 755 ~/.sage
   
   # 检查日志目录权限
   mkdir -p ~/.sage/logs
   chmod 755 ~/.sage/logs
   ```

3. **以管理员权限运行**（仅在必要时）
   ```bash
   sudo sage jobmanager start
   ```

### 4. 配置文件问题

**问题描述**：配置文件格式错误或路径问题

**解决方案**：

1. **重置配置文件**
   ```bash
   # 备份现有配置
   mv ~/.sage/config ~/.sage/config.backup
   
   # 重新初始化
   sage jobmanager init
   ```

2. **验证配置文件**
   ```bash
   sage config validate
   ```

3. **手动创建配置**
   ```bash
   mkdir -p ~/.sage
   cat > ~/.sage/config << EOF
   [jobmanager]
   host = localhost
   port = 19001
   workers = 4
   log_level = INFO
   EOF
   ```

### 5. 依赖包问题

**问题描述**：缺少必要的依赖包

**错误示例**：
```
ModuleNotFoundError: No module named 'some_required_module'
```

**解决方案**：

1. **重新安装SAGE**
   ```bash
   pip uninstall isage -y
   pip install isage
   ```

2. **检查环境**
   ```bash
   # 验证Python环境
   python -c "import sage; print('✅ SAGE模块正常')"
   
   # 检查必要依赖
   pip list | grep -E "(ray|fastapi|uvicorn)"
   ```

3. **使用虚拟环境**
   ```bash
   python -m venv sage-env
   source sage-env/bin/activate
   pip install isage
   sage jobmanager start
   ```

### 6. 内存不足

**问题描述**：系统内存不足导致启动失败

**解决方案**：

1. **检查内存使用**
   ```bash
   free -h
   ps aux --sort=-%mem | head
   ```

2. **限制内存使用**
   ```bash
   sage jobmanager start --max-memory 1G --workers 2
   ```

3. **清理内存**
   ```bash
   # 清理缓存
   sudo sync && sudo sysctl vm.drop_caches=3
   
   # 关闭不必要的进程
   sudo systemctl stop unnecessary-service
   ```

### 7. 网络配置问题

**问题描述**：网络接口配置导致启动失败

**解决方案**：

1. **指定网络接口**
   ```bash
   # 绑定到localhost
   sage jobmanager start --host 127.0.0.1
   
   # 绑定到所有接口
   sage jobmanager start --host 0.0.0.0
   
   # 绑定到特定IP
   sage jobmanager start --host 192.168.1.100
   ```

2. **检查网络配置**
   ```bash
   # 查看网络接口
   ip addr show
   ifconfig
   
   # 测试网络连通性
   ping localhost
   ```

## 🔧 启动流程调试

### 启用详细日志

```bash
# 启用DEBUG级别日志
sage jobmanager start --log-level DEBUG

# 实时查看日志
sage jobmanager logs --follow

# 查看启动日志
sage jobmanager logs --startup
```

### 手动启动步骤

如果自动启动失败，可以尝试手动启动：

```bash
# 1. 检查环境
python -c "import sage; print(sage.__version__)"

# 2. 检查配置
sage config show

# 3. 检查端口
netstat -tlnp | grep 19001

# 4. 清理旧进程
pkill -f jobmanager

# 5. 启动服务
sage jobmanager start --verbose
```

### 验证启动状态

```bash
# 检查进程状态
sage jobmanager status

# 测试连接
sage jobmanager ping

# 检查健康状态
sage jobmanager health-check

# 查看服务信息
sage jobmanager info
```

## 🐛 常见错误代码

| 错误代码 | 描述 | 解决方案 |
|---------|------|----------|
| `EADDRINUSE` | 端口已被占用 | 更换端口或终止占用进程 |
| `EACCES` | 权限不足 | 使用非特权端口或提升权限 |
| `ENOENT` | 文件或目录不存在 | 检查配置路径和权限 |
| `ENOMEM` | 内存不足 | 释放内存或降低资源使用 |
| `ECONNREFUSED` | 连接被拒绝 | 检查网络配置和防火墙 |

## 🚀 性能优化

### 启动性能优化

```bash
# 减少工作进程数
sage jobmanager start --workers 2

# 禁用不必要的功能
sage jobmanager start --no-monitoring --no-dashboard

# 使用更快的存储
sage jobmanager start --work-dir /tmp/sage
```

### 资源限制

```bash
# 限制CPU使用
sage jobmanager start --max-cpu-percent 50

# 限制内存使用  
sage jobmanager start --max-memory 2G

# 设置超时时间
sage jobmanager start --startup-timeout 60
```

## 📊 监控和维护

### 定期健康检查

```bash
# 创建健康检查脚本
cat > /usr/local/bin/sage-health-check.sh << 'EOF'
#!/bin/bash
if ! sage jobmanager ping &>/dev/null; then
    echo "$(date): JobManager不响应，正在重启..."
    sage jobmanager restart
fi
EOF

chmod +x /usr/local/bin/sage-health-check.sh

# 添加到crontab
echo "*/5 * * * * /usr/local/bin/sage-health-check.sh" | crontab -
```

### 日志轮转

```bash
# 配置日志轮转
sudo cat > /etc/logrotate.d/sage-jobmanager << EOF
/home/*/.sage/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    copytruncate
}
EOF
```

## 📞 获取帮助

如果问题仍然存在：

1. **生成诊断报告**
   ```bash
   sage diagnose --jobmanager --output sage_jobmanager_diagnostic.txt
   ```

2. **联系技术支持**
   - 📧 support@sage-ai.com
   - 🐛 [GitHub Issues](https://github.com/ShuhuaGao/SAGE/issues)
   - 💬 [社区讨论](https://github.com/ShuhuaGao/SAGE/discussions)

---

💡 **小贴士**：大多数启动问题都可以通过清理环境和重新启动解决：
```bash
sage jobmanager stop
pkill -f jobmanager
sage jobmanager start
```
