# Runtime Task 模块

Runtime Task 模块提供 SAGE 框架的任务执行抽象，支持本地和分布式任务执行模式。

## 模块架构

### 核心组件

- **`base_task.py`**: 任务基类
  - `BaseTask`: 所有任务类型的抽象基类
  - 定义统一的任务接口和生命周期管理
  - 提供通用的任务功能如路由、监控等

- **`local_task.py`**: 本地任务实现
  - `LocalTask`: 本地进程内的任务执行
  - 使用 SageQueue 高性能共享队列
  - 支持多线程并行处理

- **`ray_task.py`**: 分布式任务实现
  - `RayTask`: 基于 Ray Actor 的分布式任务
  - 使用 Ray Queue 进行跨节点通信
  - 支持集群环境下的任务执行

## 核心功能

### 1. 任务生命周期管理
```python
from sage.runtime.task.local_task import LocalTask

# 创建任务
task = LocalTask(runtime_context, operator_factory)

# 启动任务
task.start_running()

# 监控任务状态
status = task.get_status()

# 停止任务
task.stop()
```

### 2. 数据包处理
```python
from sage.runtime.communication.router.packet import Packet

# 创建数据包
packet = Packet(payload=data, input_index=0)

# 发送数据包到任务
task.put_packet(packet)

# 处理数据包（内部实现）
task.process_packet(packet)
```

### 3. 路由集成
```python
# 添加下游连接
task.router.add_connection(downstream_connection)

# 发送数据到下游
task.router.route(packet)
```

## 任务类型

### 本地任务 (LocalTask)

**特性**：
- 单进程内执行，适合开发和测试
- 使用 SageQueue 高性能队列
- 多线程工作模式
- 低延迟数据传输

**使用场景**：
- 本地开发和调试
- 单机小规模数据处理
- 需要低延迟的实时处理

**配置示例**：
```python
local_task = LocalTask(
    runtime_context=ctx,
    operator_factory=op_factory,
    max_buffer_size=30000,
    queue_maxsize=50000
)
```

### Ray 任务 (RayTask)

**特性**：
- 基于 Ray Actor 的分布式执行
- 支持跨节点数据传输
- 自动故障恢复和负载均衡
- 可扩展的集群计算

**使用场景**：
- 大规模分布式计算
- 需要水平扩展的场景
- 集群环境下的数据处理

**配置示例**：
```python
@ray.remote
class RayTask(BaseTask):
    def __init__(self, runtime_context, operator_factory):
        super().__init__(runtime_context, operator_factory)
```

## 任务执行模型

### 工作线程模式
- **独立线程**: 每个任务运行在独立的工作线程中
- **非阻塞**: 避免阻塞主线程或 Ray Actor 事件循环
- **并发处理**: 支持多个数据包的并发处理

### 事件驱动
- **数据驱动**: 基于数据到达事件触发处理
- **异步处理**: 支持异步数据处理模式
- **背压控制**: 自动处理上游数据积压

### 状态管理
- **任务状态**: 跟踪任务的运行状态
- **性能指标**: 收集处理计数、错误统计等
- **资源监控**: 监控内存和 CPU 使用情况

## 队列和缓冲

### 输入缓冲区
```python
# 使用队列适配器创建缓冲区
self.input_buffer = create_queue(name=self.ctx.name)

# 配置队列参数
if hasattr(self.input_buffer, 'logger'):
    self.input_buffer.logger = self.ctx.logger
```

### 队列类型支持
- **SageQueue**: 高性能共享内存队列
- **Ray Queue**: 分布式队列支持
- **Local Queue**: 标准 Python 队列

### 缓冲区管理
- **大小控制**: 配置缓冲区最大大小
- **背压处理**: 缓冲区满时的背压机制
- **内存优化**: 避免内存泄漏和过度消耗

## 路由集成

### 路由器注入
```python
# 创建并注入路由器
self.router = BaseRouter(runtime_context)
self.operator.inject_router(self.router)
```

### 连接管理
- **下游连接**: 管理到下游任务的连接
- **负载均衡**: 智能选择下游目标
- **故障转移**: 处理连接故障和恢复

### 数据路由
- **包路由**: 根据路由策略分发数据包
- **分区支持**: 支持基于键的数据分区
- **广播模式**: 支持数据的广播传输

## 性能监控

### 执行指标
```python
# 性能计数器
self._processed_count = 0  # 已处理数据包数量
self._error_count = 0      # 错误计数
```

### 监控功能
- **吞吐量监控**: 实时监控数据处理速率
- **延迟监控**: 测量端到端处理延迟
- **错误率监控**: 跟踪处理错误率

### 调试支持
- **日志记录**: 详细的任务执行日志
- **状态查询**: 查询任务当前状态
- **性能分析**: 性能瓶颈分析工具

## 故障处理

### 异常处理
```python
try:
    self.operator = operator_factory.create_operator(self.ctx)
    self.operator.task = self
    self.operator.inject_router(self.router)
except Exception as e:
    self.logger.error(f"Failed to initialize node {self.name}: {e}", exc_info=True)
    raise
```

### 恢复机制
- **任务重启**: 支持任务的自动重启
- **状态恢复**: 恢复任务的运行状态
- **数据恢复**: 处理未完成的数据包

### 容错设计
- **优雅关闭**: 支持任务的优雅停止
- **资源清理**: 自动清理任务资源
- **依赖检查**: 验证任务依赖的可用性

## 配置选项

### 任务配置
```yaml
task:
  local:
    max_buffer_size: 30000
    queue_maxsize: 50000
    worker_threads: 1
  
  ray:
    lifetime: "detached"
    resources: {"CPU": 1}
    memory: "1GB"
```

### 性能调优
```yaml
performance:
  batch_processing: true
  batch_size: 100
  processing_timeout: 30
  monitoring_interval: 5
```

## 扩展接口

### 自定义任务类型
```python
class CustomTask(BaseTask):
    def __init__(self, runtime_context, operator_factory):
        super().__init__(runtime_context, operator_factory)
        # 自定义初始化逻辑
    
    def custom_process(self, packet):
        # 自定义处理逻辑
        return self.operator.process(packet)
```

### 任务插件
- **前处理插件**: 在数据处理前执行的插件
- **后处理插件**: 在数据处理后执行的插件
- **监控插件**: 提供额外监控功能的插件

## 参考

相关模块：
- `../communication/`: 通信系统
- `../factory/`: 工厂模式创建
- `../service/`: 服务调用框架
- `../../core/operator/`: 算子实现
