# SAGE 网络通信模块

本模块提供网络通信的基础设施，包括TCP客户端和服务端的实现。

## 概述

网络通信模块为SAGE框架提供可靠的网络通信能力，支持分布式环境下的数据传输和服务通信。

## 核心组件

### `base_tcp_client.py`
TCP客户端基础类：
- 提供TCP连接管理
- 支持重连机制和连接池
- 实现消息发送和接收
- 包含错误处理和超时控制
- 支持异步和同步操作模式

### `local_tcp_server.py`
本地TCP服务器：
- 实现高性能TCP服务器
- 支持多客户端并发连接
- 提供消息路由和处理
- 包含连接状态管理
- 支持服务优雅关闭

## 主要特性

- **高可靠性**: 完善的错误处理和重连机制
- **高性能**: 支持异步I/O和连接复用
- **易扩展**: 模块化设计，便于功能扩展
- **监控友好**: 提供连接状态和性能指标

## 使用场景

- **分布式通信**: 节点间的数据交换
- **服务发现**: 服务注册和发现机制
- **任务调度**: 任务分发和状态同步
- **数据传输**: 大数据量的可靠传输

## 快速开始

```python
# TCP客户端
from sage.utils.network.base_tcp_client import BaseTCPClient

client = BaseTCPClient(host="localhost", port=8080)
client.connect()
client.send_message("Hello Server")
response = client.receive_message()
client.disconnect()

# TCP服务器
from sage.utils.network.local_tcp_server import LocalTCPServer

def message_handler(client_socket, message):
    # 处理接收到的消息
    return "Response: " + message

server = LocalTCPServer(port=8080, handler=message_handler)
server.start()
# 服务器在后台运行
server.stop()
```

## 协议设计

### 消息格式
- 采用长度前缀的消息格式
- 支持JSON和二进制数据传输
- 包含消息类型和序号字段
- 提供校验和机制

### 连接管理
- 心跳检测机制
- 自动重连策略
- 连接超时控制
- 优雅断开连接

## 配置选项

支持丰富的配置参数：
- `connection_timeout`: 连接超时时间
- `read_timeout`: 读取超时时间
- `buffer_size`: 缓冲区大小
- `max_connections`: 最大连接数
- `heartbeat_interval`: 心跳间隔

## 错误处理

完善的异常处理机制：
- 网络连接异常
- 数据传输错误
- 协议解析错误
- 资源耗尽处理

## 性能优化

- 连接池管理
- 数据压缩传输
- 批量消息处理
- 内存使用优化
