# TCP服务器重构文档

## 重构概述

我们成功地重构了 `JobManagerServer` 和 `LocalTcpServer`，将通用的TCP服务器功能提取到一个基础类中，提高了代码的可维护性和可扩展性。

## 重构架构

### 1. BaseTcpServer（基础TCP服务器类）

位置：`sage/utils/local_tcp_server.py`

这是一个抽象基类，提供了通用的TCP服务器功能：

**核心功能：**
- TCP连接管理（监听、接受连接、处理客户端）
- 消息收发框架（长度前缀协议）
- 服务器生命周期管理（启动、停止）
- 多线程客户端处理
- 错误处理和日志记录

**抽象方法：**
- `_handle_message_data(message_data: bytes, client_address: tuple) -> Optional[Dict[str, Any]]`
  - 子类必须实现此方法来处理具体的消息数据

**可重写方法：**
- `_serialize_response(response: Any) -> bytes`
  - 默认使用pickle序列化，子类可以重写使用其他格式（如JSON）

### 2. LocalTcpServer（本地TCP服务器）

继承自 `BaseTcpServer`，专门用于处理基于消息类型的多处理器架构：

**特色功能：**
- 基于消息类型的处理器注册机制
- 默认处理器支持
- 自动消息类型提取
- pickle序列化支持

**主要方法：**
- `register_handler(message_type: str, handler: Callable)` - 注册特定类型的消息处理器
- `set_default_handler(handler: Callable)` - 设置默认消息处理器
- `unregister_handler(message_type: str)` - 注销消息处理器

### 3. JobManagerServer（作业管理服务器）

继承自 `BaseTcpServer`，专门处理JobManager的业务逻辑：

**特色功能：**
- JSON消息格式支持
- JobManager业务逻辑处理
- 作业生命周期管理接口

**主要处理的操作：**
- `submit_job` - 提交作业
- `get_job_status` - 获取作业状态
- `pause_job` / `continue_job` - 暂停/继续作业
- `delete_job` - 删除作业
- `list_jobs` - 列出作业
- `health_check` - 健康检查
- 等等...

## 重构优势

### 1. 代码复用
- 消除了重复的TCP服务器逻辑
- 统一的连接管理和消息处理框架

### 2. 更好的分离关注点
- `BaseTcpServer`：专注于网络通信
- `LocalTcpServer`：专注于消息路由
- `JobManagerServer`：专注于业务逻辑

### 3. 更容易扩展
- 新的服务器类型可以轻松继承`BaseTcpServer`
- 统一的接口使得测试和维护更简单

### 4. 更好的错误处理
- 统一的错误处理机制
- 分层的异常处理

## 使用示例

### 创建自定义TCP服务器

```python
from sage.utils.network.local_tcp_server import BaseTcpServer
import json

class MyCustomServer(BaseTcpServer):
    def __init__(self):
        super().__init__(server_name="MyCustomServer")
    
    def _handle_message_data(self, message_data: bytes, client_address: tuple):
        # 处理接收到的消息
        try:
            message = json.loads(message_data.decode('utf-8'))
            # 处理业务逻辑...
            return {"status": "success", "processed": message}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _serialize_response(self, response):
        return json.dumps(response).encode('utf-8')

# 使用
server = MyCustomServer()
server.start()
# ... 处理客户端请求 ...
server.stop()
```

### 使用LocalTcpServer

```python
from sage.utils.network.local_tcp_server import LocalTcpServer

def handle_ping(message, client_address):
    return {"type": "pong", "message": "Hello from server!"}

def handle_default(message, client_address):
    return {"type": "unknown", "message": "Unknown message type"}

server = LocalTcpServer(default_handler=handle_default)
server.register_handler("ping", handle_ping)
server.start()
```

## 兼容性

重构后的代码保持了与现有客户端的兼容性：

1. **JobManagerServer** - 保持了原有的JSON消息格式和所有API接口
2. **LocalTcpServer** - 保持了原有的pickle序列化和消息处理器机制

## 测试

运行测试脚本验证重构结果：

```bash
cd /home/tjy/SAGE
python test_refactored_servers.py
```

测试覆盖：
- BaseTcpServer的基本功能
- LocalTcpServer的消息处理器机制
- 客户端-服务器通信
- 错误处理

## 总结

通过这次重构，我们成功地：

1. **消除了代码重复** - 将共同的TCP服务器逻辑提取到基类中
2. **提高了可维护性** - 清晰的继承结构和职责分离
3. **增强了可扩展性** - 新的服务器类型可以轻松添加
4. **保持了向后兼容性** - 现有的客户端代码无需修改
5. **改善了测试性** - 模块化的设计使得单元测试更容易

重构后的架构为SAGE系统的TCP通信层提供了一个坚实的基础，同时为未来的扩展留下了灵活的空间。
