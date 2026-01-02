# SAGE 运维指南

本文档提供 SAGE 系统运维相关的最佳实践和配置指导。

## 优雅关闭机制

SAGE 系统实现了优雅关闭机制，确保在系统停止时正确处理正在执行的任务和数据。

### 关闭保证

当使用 autostop 功能时，SAGE 提供以下保证：

1. **数据完整性**: 所有 sink 操作器会在关闭前排空（drain）正在处理的消息
1. **超时控制**: 默认排空超时时间为 10 秒，可通过配置调整
1. **优雅等待**: 系统会等待正在执行的任务完成，避免数据丢失

### 配置参数

#### Sink 排空参数

可以通过以下参数控制 sink 操作器的排空行为：

```yaml
sink:
  drain_timeout: 10.0        # 排空超时时间（秒）
  drain_quiet_period: 0.3    # 静默期（秒）
```

**参数说明：**

- `drain_timeout`: 等待队列排空的最大时间，默认 10 秒
- `drain_quiet_period`: 检查队列是否为空的间隔时间，默认 0.3 秒

#### 适用场景

不同的部署环境可能需要不同的配置：

| 场景       | drain_timeout | drain_quiet_period | 说明               |
| ---------- | ------------- | ------------------ | ------------------ |
| 开发测试   | 5-10s         | 0.1-0.3s           | 快速关闭，数据量小 |
| 生产环境   | 30-60s        | 0.5-1.0s           | 确保数据完整性     |
| 大数据处理 | 60-300s       | 1.0-2.0s           | 处理大量积压数据   |
| 分布式部署 | 30-120s       | 0.5-1.0s           | 考虑网络延迟       |

### 监控和故障排除

#### 关闭日志

系统关闭时会输出详细的日志信息：

```
[INFO] Starting graceful shutdown...
[INFO] Draining sink operator: data_sink
[INFO] Waiting for queue to empty... (10 messages remaining)
[INFO] Queue drained successfully in 3.2s
[INFO] All sink operators drained, shutdown complete
```

#### 常见问题

**关闭超时**

```
[WARN] Drain timeout reached, forcing shutdown
[WARN] 5 messages may be lost
```

**解决方案：**

- 增加 `drain_timeout` 值
- 检查下游消费者是否正常
- 确认网络连接稳定

**队列积压**

```
[INFO] Large queue detected (1000+ messages)
[INFO] Consider increasing drain_timeout
```

**解决方案：**

- 调整 `drain_timeout` 和 `drain_quiet_period`
- 优化下游处理性能
- 考虑分批处理策略

### 最佳实践

1. **环境隔离**: 不同环境使用不同的超时配置
1. **监控告警**: 设置关闭时间过长的告警
1. **容量规划**: 根据业务负载调整排空参数
1. **测试验证**: 定期测试优雅关闭功能
1. **日志分析**: 收集和分析关闭日志，优化配置

## 性能调优

### 排队系统优化

```yaml
queue:
  max_size: 10000           # 队列最大长度
  batch_size: 100           # 批处理大小
  flush_interval: 1.0       # 刷新间隔（秒）
```

### 内存管理

```yaml
memory:
  gc_threshold: 0.8         # GC 触发阈值
  max_memory_usage: "2GB"   # 最大内存使用
```

### 网络配置

```yaml
network:
  connection_timeout: 30    # 连接超时
  read_timeout: 60         # 读取超时
  retry_attempts: 3        # 重试次数
```

## 故障恢复

### 自动重启

```yaml
recovery:
  auto_restart: true        # 启用自动重启
  max_restarts: 5          # 最大重启次数
  restart_delay: 10        # 重启延迟（秒）
```

### 检查点机制

```yaml
checkpoint:
  enabled: true            # 启用检查点
  interval: 300           # 检查点间隔（秒）
  max_checkpoints: 5      # 保留检查点数量
```

## 监控指标

### 关键指标

- 队列长度和延迟
- 消息处理速率
- 错误率和超时率
- 内存和 CPU 使用率
- 排空时间和成功率

### 告警规则

```yaml
alerts:
  - name: "长时间关闭"
    condition: "drain_time > 60s"
    severity: "warning"

  - name: "关闭失败"
    condition: "drain_timeout_reached"
    severity: "critical"

  - name: "队列积压"
    condition: "queue_size > 1000"
    severity: "warning"
```

## 相关文档

- [配置参考](../config/config.md)
- [CLI 工具](../../sage-tools/cli_reference.md)
- [故障排除](../faq.md)
