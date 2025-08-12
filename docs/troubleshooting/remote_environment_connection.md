# RemoteEnvironment 连接故障排除

## 🚨 连接失败的常见原因

### 1. JobManager 未启动

**问题描述**：尝试连接 RemoteEnvironment 时失败，提示无法连接到 JobManager

**错误示例**：
```
sage.common.exceptions.ConnectionError: Failed to connect to JobManager at localhost:19001
Health check failed: Connection refused
```

**解决方案**：

1. **检查 JobManager 状态**
   ```bash
   sage jobmanager status
   ```

2. **启动 JobManager**
   ```bash
   # 启动服务
   sage jobmanager start
   
   # 检查启动状态
   sage jobmanager status
   
   # 查看详细日志
   sage jobmanager logs
   ```

3. **验证连接**
   ```bash
   # 测试连接
   python -c "
   from sage.kernel.client import RemoteEnvironment
   env = RemoteEnvironment()
   print('✅ 连接成功！')
   "
   ```

### 2. 端口冲突

**问题描述**：默认端口 19001 已被其他服务占用

**错误示例**：
```
OSError: [Errno 98] Address already in use
```

**解决方案**：

1. **检查端口占用**
   ```bash
   # Linux/Mac
   netstat -tlnp | grep 19001
   lsof -i :19001
   
   # Windows
   netstat -ano | findstr :19001
   ```

2. **使用不同端口**
   ```bash
   # 启动 JobManager 时指定端口
   sage jobmanager start --port 19002
   
   # 在代码中指定端口
   from sage.kernel.client import RemoteEnvironment
   env = RemoteEnvironment(host='localhost', port=19002)
   ```

3. **配置环境变量**
   ```bash
   export SAGE_JOBMANAGER_PORT=19002
   sage jobmanager start
   ```

### 3. 防火墙/网络问题

**问题描述**：网络配置阻止连接

**解决方案**：

1. **检查防火墙设置**
   ```bash
   # Ubuntu/Debian
   sudo ufw status
   sudo ufw allow 19001
   
   # CentOS/RHEL
   sudo firewall-cmd --list-ports
   sudo firewall-cmd --add-port=19001/tcp --permanent
   sudo firewall-cmd --reload
   ```

2. **测试网络连接**
   ```bash
   # 测试本地连接
   telnet localhost 19001
   
   # 测试远程连接
   telnet your-server-ip 19001
   ```

3. **配置网络接口**
   ```bash
   # 绑定到所有接口（谨慎使用）
   sage jobmanager start --host 0.0.0.0
   
   # 绑定到特定接口
   sage jobmanager start --host 192.168.1.100
   ```

### 4. SSL/TLS 证书问题

**问题描述**：启用了加密通信但证书配置有问题

**错误示例**：
```
ssl.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed
```

**解决方案**：

1. **重新生成证书**
   ```bash
   sage ssl-cert generate
   sage jobmanager restart
   ```

2. **验证证书**
   ```bash
   sage ssl-cert verify
   ```

3. **临时禁用SSL验证**（仅测试）
   ```python
   import ssl
   ssl._create_default_https_context = ssl._create_unverified_context
   
   from sage.kernel.client import RemoteEnvironment
   env = RemoteEnvironment(verify_ssl=False)
   ```

### 5. 权限问题

**问题描述**：没有权限访问端口或文件

**错误示例**：
```
PermissionError: [Errno 13] Permission denied
```

**解决方案**：

1. **使用非特权端口**
   ```bash
   sage jobmanager start --port 8001  # > 1024
   ```

2. **修改文件权限**
   ```bash
   # 检查日志文件权限
   ls -la ~/.sage/logs/
   
   # 修复权限
   chmod 644 ~/.sage/logs/*
   chmod 755 ~/.sage/
   ```

3. **以合适的用户运行**
   ```bash
   # 切换到正确的用户
   su - sage-user
   sage jobmanager start
   ```

### 6. 内存/资源不足

**问题描述**：系统资源不足导致 JobManager 无法正常启动

**解决方案**：

1. **检查系统资源**
   ```bash
   # 检查内存使用
   free -h
   
   # 检查CPU使用
   top
   
   # 检查磁盘空间
   df -h
   ```

2. **调整 JobManager 配置**
   ```bash
   # 限制内存使用
   sage jobmanager start --max-memory 2G
   
   # 限制工作进程数
   sage jobmanager start --workers 2
   ```

3. **清理系统资源**
   ```bash
   # 清理临时文件
   sudo rm -rf /tmp/sage_*
   
   # 重启系统服务
   sudo systemctl restart sage-jobmanager
   ```

## 🔧 高级故障排除

### 启用调试模式

```bash
# 启用详细日志
sage jobmanager start --log-level DEBUG

# 查看实时日志
sage jobmanager logs --follow

# 生成诊断报告
sage diagnose --jobmanager
```

### 手动连接测试

```python
import socket
import time

def test_connection(host='localhost', port=19001):
    """测试TCP连接"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ 端口 {port} 可达")
            return True
        else:
            print(f"❌ 端口 {port} 不可达")
            return False
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False

# 运行测试
test_connection()
```

### 重置配置

```bash
# 备份当前配置
cp -r ~/.sage ~/.sage.backup

# 重置为默认配置
rm -rf ~/.sage
sage jobmanager init

# 重新启动
sage jobmanager start
```

## 📞 获取帮助

如果以上解决方案都无法解决问题：

1. **收集诊断信息**
   ```bash
   sage diagnose --full > sage_diagnostic.txt
   ```

2. **查看详细日志**
   ```bash
   sage jobmanager logs --error --last-24h
   ```

3. **提交问题报告**
   - 📧 技术支持：support@sage-ai.com
   - 🐛 GitHub Issues：[SAGE Issues](https://github.com/ShuhuaGao/SAGE/issues)
   - 💬 社区讨论：[GitHub Discussions](https://github.com/ShuhuaGao/SAGE/discussions)

---

💡 **小贴士**：大多数连接问题都可以通过重启 JobManager 解决：`sage jobmanager restart`
