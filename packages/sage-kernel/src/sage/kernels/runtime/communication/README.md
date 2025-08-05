# Communication 通信模块

Communication 模块提供 SAGE 运行时的统一通信框架，支持多种通信模式和数据路由策略。

## 模块架构

### 队列通信系统 (`queue/`)
提供统一的队列抽象和多种队列实现。

**核心组件**：
- **队列描述符**: 统一的多态队列描述符系统
- **队列桩**: 各种队列类型的封装和转换
- **描述符扩展**: 队列描述符的基础设施支持

**主要特性**：
- 支持本地队列、共享内存队列、Ray Actor 队列等
- 统一的队列接口和序列化支持
- 跨进程队列描述符传递

### 路由系统 (`router/`)
处理数据包路由、连接管理和负载均衡。

**核心组件**：
- **路由器**: 负责数据包的智能路由和分发
- **连接管理**: 管理节点间的通信连接
- **数据包**: 定义通信的基本数据单元

**主要特性**：
- 多种路由策略（轮询、键分区、负载均衡）
- 实时负载监控和自适应调整
- 支持本地和分布式混合连接

## 通信模式

### 1. 点对点通信
```python
from sage.runtime.communication.queue_descriptor import QueueDescriptor
from sage.runtime.communication.router import Connection

# 创建队列描述符
descriptor = QueueDescriptor(
    queue_id="p2p_queue",
    queue_type="local",
    metadata={"maxsize": 1000}
)

# 建立连接
connection = Connection(
    broadcast_index=0,
    parallel_index=0,
    target_name="receiver",
    target_handle=receiver_task,
    target_input_index=0
)
```

### 2. 广播通信
```python
# 创建广播路由器
router = BroadcastRouter(ctx)

# 添加多个下游连接
for i, target in enumerate(targets):
    connection = Connection(
        broadcast_index=i,
        parallel_index=0,
        target_name=f"target_{i}",
        target_handle=target,
        target_input_index=0
    )
    router.add_connection(connection)
```

### 3. 分区通信
```python
from sage.runtime.communication.router.packet import Packet

# 创建带分区键的数据包
packet = Packet(
    payload=data,
    partition_key=user_id,
    partition_strategy="hash"
)

# 路由器根据分区键选择目标
router.route(packet)
```

## 队列类型支持

### 本地队列 (Local Queue)
- **适用场景**: 单进程内线程间通信
- **特点**: 低延迟，高性能
- **实现**: 基于 Python `queue.Queue`

### 共享内存队列 (Shared Memory Queue)
- **适用场景**: 多进程间通信
- **特点**: 高效的跨进程数据传输
- **实现**: 基于共享内存机制

### Ray Actor 队列
- **适用场景**: 分布式计算环境
- **特点**: 跨节点通信，自动容错
- **实现**: 基于 Ray 分布式框架

### SAGE 队列
- **适用场景**: 高性能流处理
- **特点**: 专为 SAGE 优化的高性能队列
- **实现**: 自定义实现，支持背压和流控

## 性能优化

### 负载均衡
- **动态负载监控**: 实时跟踪下游节点负载
- **自适应路由**: 根据负载情况动态调整路由策略
- **负载预测**: 基于历史数据预测负载趋势

### 内存管理
- **零拷贝传输**: 在可能的情况下避免数据拷贝
- **缓冲区管理**: 智能缓冲区大小调整
- **内存池**: 复用内存对象减少 GC 压力

### 网络优化
- **连接复用**: 复用网络连接减少开销
- **批量传输**: 合并小数据包提高传输效率
- **压缩传输**: 对大数据进行压缩传输

## 故障处理

### 连接故障
- **健康检查**: 定期检查连接健康状态
- **自动重连**: 连接断开时自动重新建立
- **故障转移**: 将流量转移到健康的连接

### 数据丢失防护
- **确认机制**: 可选的消息确认机制
- **重传策略**: 失败消息的重传处理
- **持久化**: 关键数据的持久化存储

## 监控和调试

### 通信指标
- **吞吐量**: 消息传输速率统计
- **延迟**: 端到端消息延迟测量
- **队列状态**: 队列大小和利用率监控

### 调试支持
- **消息追踪**: 跟踪消息的完整传输路径
- **性能分析**: 通信性能瓶颈分析
- **日志记录**: 详细的通信日志记录

## 配置选项

### 队列配置
```yaml
communication:
  queue:
    default_type: "local"
    max_size: 10000
    timeout: 30
  
  router:
    strategy: "load_balance"
    health_check_interval: 5
    max_retries: 3
```

### 性能调优
```yaml
performance:
  batch_size: 100
  compression: true
  zero_copy: true
  memory_pool_size: 1024
```

## 参考

相关模块：
- `../task/`: 任务执行系统
- `../service/`: 服务调用框架
- `../../core/`: 核心执行引擎
