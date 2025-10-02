# Router 模块概览

`router` 子包提供运行时的数据路由 primitives，所有算子最终都通过 `TaskContext` 触发这里的逻辑。

## 组成部分

- `router.py`：`BaseRouter` 持有下游 `Connection` 集合，并实现 Round-Robin / Hash / Broadcast 三种策略；同时负责向所有下游队列广播 `StopSignal`。
- `connection.py`：封装下游节点的元信息和队列描述符。包含基础的缓冲区负载查询字段（`get_buffer_load` / `_load_history`），目前仅用于调试日志，不会自动调整发送速率。
- `packet.py`：定义 `Packet` 和 `StopSignal` 数据结构，用于封装 Payload 与停止事件。

## 工作流程

1. JobManager 编译执行图时，将每个边的队列描述符和目标索引写入 `Connection` 对象。
2. `TaskContext` 在构造时组装 `downstream_groups`，运行时通过 `BaseRouter` 的 `send()` 将 `Packet` 投递到对应队列：
   - **默认**：轮询同一广播组内的并行实例。
   - **Hash**：当 `packet.partition_strategy == "hash"` 且提供 `partition_key` 时，根据哈希值选择目标。
   - **Broadcast**：当策略为 `"broadcast"` 时，对广播组所有连接逐个发送。
3. 停止信号沿同一路径传播，`BaseRouter.send_stop_signal()` 会调用每个连接的队列描述符，将 `StopSignal` 写入队列。

## 常用 API

```python
from sage.kernel.runtime.communication.router.packet import Packet

packet = Packet(payload={"value": 1})
ctx.send_packet(packet)  # TaskContext 封装了 BaseRouter

stop = StopSignal("SourceDone", source="Source_1")
ctx.send_stop_signal(stop)
```

要查看当前任务的下游拓扑，可调用：

```python
info = ctx.get_routing_info()
print(info)
```

## 限制与扩展点

- **负载均衡**：`Connection` 中的负载跟踪字段尚未被 `BaseRouter` 消费，如需自适应调度需自行扩展路由逻辑。
- **错误处理**：当前实现将异常记录到日志，不会对失败的发送进行自动重试。
- **自定义策略**：可以继承 `BaseRouter` 并覆写 `_route_packet` / `_route_round_robin_packet` 等方法，然后在构建 `TaskContext` 时注入自定义实现（需要扩展 `TaskContext._get_router`）。

更多上下文：

- `../queue_descriptor/README.md`
- `../../runtime_tasks.md`
- `../../runtime_services.md`
