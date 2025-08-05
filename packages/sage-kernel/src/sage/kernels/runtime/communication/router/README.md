# Communication Router 模块

Communication Router 负责处理运行时的数据路由和连接管理，提供高效的数据包传输和负载均衡。

## 模块架构

### 核心组件

- **`router.py`**: 路由器基类和实现
  - `BaseRouter`: 路由器抽象基类，定义路由接口
  - 管理下游连接和数据包路由逻辑
  - 支持负载均衡和故障检测

- **`connection.py`**: 连接管理
  - `Connection`: 表示节点间的连接对象
  - 支持本地任务和 Ray Actor 之间的连接
  - 提供负载监控和连接状态跟踪

- **`packet.py`**: 数据包定义
  - `Packet`: 数据传输的基本单元
  - 支持分区键和路由策略
  - 提供时间戳和追踪信息

## 核心功能

### 1. 数据路由
```python
from sage.kernels.runtime.communication.router import BaseRouter

class CustomRouter(BaseRouter):
    def route_packet(self, packet):
        # 实现自定义路由逻辑
        target = self.select_target(packet)
        self.send_to_target(target, packet)
```

### 2. 连接管理
```python
from sage.kernels.runtime.communication.router.connection import Connection

# 创建连接
connection = Connection(
    broadcast_index=0,
    parallel_index=1,
    target_name="downstream_task",
    target_handle=target_task,
    target_input_index=0,
    target_type="local"
)

# 监控连接负载
load = connection.get_buffer_load()
```

### 3. 数据包处理
```python
from sage.kernels.runtime.communication.router.packet import Packet

# 创建数据包
packet = Packet(
    payload=data,
    input_index=0,
    partition_key="key1",
    partition_strategy="hash"
)

# 检查分区信息
if packet.is_keyed():
    # 处理分区逻辑
    new_packet = packet.update_key("new_key")
```

## 路由策略

### 1. 轮询路由 (Round Robin)
- 均匀分配数据包到所有下游连接
- 适用于无状态处理场景

### 2. 键分区路由 (Key Partitioning)
- 根据分区键将数据路由到特定节点
- 保证相同键的数据发送到同一节点

### 3. 负载均衡路由
- 根据下游节点负载选择最优路径
- 动态调整路由策略以避免热点

## 性能特性

### 连接监控
- **负载跟踪**: 实时监控下游节点的缓冲区负载
- **负载历史**: 维护负载变化趋势用于预测
- **自适应调整**: 根据负载情况动态调整路由策略

### 故障处理
- **连接检测**: 检测下游连接的健康状态
- **自动重试**: 对失败的数据传输进行重试
- **降级处理**: 在部分节点故障时继续服务

### 类型支持
- **本地任务**: 支持本地进程内的任务连接
- **Ray Actor**: 支持分布式 Ray Actor 连接
- **混合模式**: 同时支持本地和远程连接

## 扩展接口

### 自定义路由器
```python
class MyCustomRouter(BaseRouter):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.custom_config = load_config()
    
    def select_downstream(self, packet):
        # 实现自定义选择逻辑
        return self.best_connection_for(packet)
```

### 连接工厂
```python
def create_connection(target_info):
    return Connection(
        broadcast_index=target_info.broadcast_idx,
        parallel_index=target_info.parallel_idx,
        target_name=target_info.name,
        target_handle=target_info.handle,
        target_input_index=target_info.input_idx
    )
```

## 参考

相关模块：
- `../queue/`: 队列通信系统
- `../../task/`: 任务执行系统
- `../../service/`: 服务调用系统
