# RemoteEnvironment 使用指南

## 🚀 快速开始

使用RemoteEnvironment时，您需要确保JobManager服务正在运行。

### 步骤1：启动JobManager

```bash
# 启动JobManager服务（默认端口19001）
sage jobmanager start

# 自定义主机和端口
sage jobmanager start --host 127.0.0.1 --port 19001

# 检查服务状态
sage jobmanager status
```

### 步骤2：使用RemoteEnvironment

```python
from sage.core.api.remote_environment import RemoteEnvironment

# 创建远程环境
env = RemoteEnvironment(
    name="my_remote_app",
    host="127.0.0.1",    # JobManager服务主机
    port=19001           # JobManager服务端口
)

# 构建数据流
stream = env.from_batch([1, 2, 3, 4, 5])
result = stream.map(lambda x: x * 2)

# 提交任务
job_uuid = env.submit()
print(f"任务已提交，UUID: {job_uuid}")
```

## 🔧 常见问题解决

### 问题1：连接失败

**错误信息**：
```
Failed to connect to JobManager at 127.0.0.1:19001
```

**解决方案**：
1. **检查JobManager是否启动**：
   ```bash
   sage jobmanager status
   ```

2. **启动JobManager**：
   ```bash
   sage jobmanager start
   ```

3. **检查主机和端口是否正确**：
   ```bash
   # 检查端口是否被占用
   netstat -tlnp | grep 19001
   ```

### 问题2：权限问题

**错误信息**：
```
Permission denied when connecting to JobManager
```

**解决方案**：
1. **确保您有权访问指定的主机和端口**
2. **如果使用非标准端口，检查防火墙设置**
3. **如果是本地环境，检查JobManager是否以正确的用户启动**

### 问题3：健康检查失败

**错误信息**：
```
JobManager health check failed
```

**解决方案**：
1. **重启JobManager**：
   ```bash
   sage jobmanager restart
   ```

2. **强制重启（如果普通重启失败）**：
   ```bash
   sage jobmanager restart --force
   ```

3. **检查JobManager日志**：
   ```bash
   # 查看JobManager进程
   ps aux | grep job_manager
   ```

## 📋 环境检查清单

在使用RemoteEnvironment前，请确认：

- [ ] JobManager服务已启动并运行正常
- [ ] 网络连接正常，无防火墙阻止
- [ ] 主机地址和端口配置正确
- [ ] 相关权限设置正确

## 🛠️ 高级配置

### 自定义超时设置

```python
env = RemoteEnvironment(
    name="my_app",
    host="127.0.0.1",
    port=19001,
    config={
        "connection_timeout": 30,    # 连接超时（秒）
        "request_timeout": 60,       # 请求超时（秒）
        "retry_attempts": 3          # 重试次数
    }
)
```

### 健康检查

```python
# 在使用前检查JobManager健康状态
health = env.health_check()
if health.get("status") != "success":
    print("JobManager不健康，请检查服务状态")
    # 处理错误...
else:
    print("JobManager运行正常")
    # 继续操作...
```

## 📚 相关文档

- [JobManager CLI 文档](../CLI_USER_GUIDE.md)
- [执行环境详解](../docs-public/docs_src/kernel/core/execution_environments.md)
- [故障排除指南](../docs/troubleshooting/)

## 💡 最佳实践

1. **开发阶段**：在本地启动JobManager进行测试
2. **生产环境**：确保JobManager作为服务持续运行
3. **错误处理**：始终检查健康状态后再提交任务
4. **资源管理**：适当配置超时和重试参数

需要帮助？请访问我们的 [GitHub Issues](https://github.com/intellistream/SAGE/issues) 页面。
