# Monitoring Metrics API Reference

## TaskPerformanceMetrics 属性参考

### 📊 基础统计

| 属性名                    | 类型  | 说明                         |
| ------------------------- | ----- | ---------------------------- |
| `task_name`               | str   | 任务名称                     |
| `uptime`                  | float | 任务运行时间（秒）           |
| `total_packets_processed` | int   | ✅ 成功处理的数据包总数      |
| `total_packets_failed`    | int   | ❌ 处理失败的数据包总数      |
| `packets_per_second`      | float | 📊 当前吞吐量（packets/sec） |

### ⏱️ 延迟统计（毫秒）

| 属性名        | 类型  | 说明                |
| ------------- | ----- | ------------------- |
| `min_latency` | float | 最小延迟 (ms)       |
| `max_latency` | float | 最大延迟 (ms)       |
| `avg_latency` | float | 平均延迟 (ms)       |
| `p50_latency` | float | P50 中位数延迟 (ms) |
| `p95_latency` | float | P95 延迟 (ms)       |
| `p99_latency` | float | P99 延迟 (ms)       |

### 📥 队列统计

| 属性名                      | 类型  | 说明                  |
| --------------------------- | ----- | --------------------- |
| `input_queue_depth`         | int   | 输入队列深度          |
| `input_queue_avg_wait_time` | float | 平均队列等待时间 (ms) |

### 💻 资源使用

| 属性名              | 类型  | 说明           |
| ------------------- | ----- | -------------- |
| `cpu_usage_percent` | float | CPU 使用率 (%) |
| `memory_usage_mb`   | float | 内存使用 (MB)  |

### 🚨 错误统计

| 属性名            | 类型           | 说明             |
| ----------------- | -------------- | ---------------- |
| `error_breakdown` | Dict[str, int] | 错误类型统计字典 |

### 📈 时间窗口统计

| 属性名            | 类型  | 说明              |
| ----------------- | ----- | ----------------- |
| `last_minute_tps` | float | 最近1分钟平均 TPS |
| `last_5min_tps`   | float | 最近5分钟平均 TPS |
| `last_hour_tps`   | float | 最近1小时平均 TPS |

### 🕒 元数据

| 属性名      | 类型  | 说明           |
| ----------- | ----- | -------------- |
| `timestamp` | float | 指标采集时间戳 |

______________________________________________________________________

## 使用示例

### 基础监控输出

```python
metrics = task.get_current_metrics()

print(f"📦 Packets Processed: {metrics.total_packets_processed}")
print(f"✅ Success: {metrics.total_packets_processed}")
print(f"❌ Errors: {metrics.total_packets_failed}")
print(f"📊 TPS: {metrics.packets_per_second:.2f} packets/sec")
```

### 延迟分析

```python
if metrics.p50_latency > 0:
    print(f"⏱️  Latency P50: {metrics.p50_latency:.1f}ms")
    print(f"⏱️  Latency P95: {metrics.p95_latency:.1f}ms")
    print(f"⏱️  Latency P99: {metrics.p99_latency:.1f}ms")
    print(f"⏱️  Avg Latency: {metrics.avg_latency:.1f}ms")
```

### 资源监控

```python
if metrics.cpu_usage_percent > 0:
    print(f"💻 CPU: {metrics.cpu_usage_percent:.1f}%")
    print(f"🧠 Memory: {metrics.memory_usage_mb:.1f}MB")
```

### 队列深度

```python
if metrics.input_queue_depth > 0:
    print(f"📥 Queue Depth: {metrics.input_queue_depth}")
    print(f"⏳ Avg Wait: {metrics.input_queue_avg_wait_time:.1f}ms")
```

### 错误分类

```python
if metrics.error_breakdown:
    print("❌ Error Breakdown:")
    for error_type, count in metrics.error_breakdown.items():
        print(f"  - {error_type}: {count}")
```

### 时间窗口 TPS

```python
print(f"📊 Current TPS: {metrics.packets_per_second:.2f}")
print(f"📊 Last Minute: {metrics.last_minute_tps:.2f}")
print(f"📊 Last 5 Minutes: {metrics.last_5min_tps:.2f}")
print(f"📊 Last Hour: {metrics.last_hour_tps:.2f}")
```

______________________________________________________________________

## ⚠️ 常见错误

### ❌ 错误的属性名

```python
# ❌ 错误
metrics.total_packets  # AttributeError
metrics.success_count  # AttributeError
metrics.error_count  # AttributeError
metrics.tps  # AttributeError
metrics.latency_p50  # AttributeError

# ✅ 正确
metrics.total_packets_processed
metrics.total_packets_failed
metrics.packets_per_second
metrics.p50_latency
```

### ❌ 单位混淆

```python
# ❌ 延迟单位是毫秒，不是秒
print(f"P50: {metrics.p50_latency:.3f}s")  # 错误单位

# ✅ 正确
print(f"P50: {metrics.p50_latency:.1f}ms")  # 正确单位
```

______________________________________________________________________

## 📝 完整示例

参考 `qa_monitoring_demo.py` 中的完整实现：

```python
def print_task_metrics(task_name, metrics):
    """打印任务监控指标"""
    print(f"\n🔧 Task: {task_name}")
    print(f"  📦 Packets Processed: {metrics.total_packets_processed}")
    print(f"  ✅ Success: {metrics.total_packets_processed}")
    print(f"  ❌ Errors: {metrics.total_packets_failed}")
    print(f"  📊 TPS: {metrics.packets_per_second:.2f} packets/sec")

    if metrics.p50_latency > 0:
        print(f"  ⏱️  Latency P50: {metrics.p50_latency:.1f}ms")
        print(f"  ⏱️  Latency P95: {metrics.p95_latency:.1f}ms")
        print(f"  ⏱️  Latency P99: {metrics.p99_latency:.1f}ms")
        print(f"  ⏱️  Avg Latency: {metrics.avg_latency:.1f}ms")

    if metrics.cpu_usage_percent > 0 or metrics.memory_usage_mb > 0:
        print(f"  💻 CPU: {metrics.cpu_usage_percent:.1f}%")
        print(f"  🧠 Memory: {metrics.memory_usage_mb:.1f}MB")

    if metrics.input_queue_depth > 0:
        print(f"  📥 Queue Depth: {metrics.input_queue_depth}")

    if metrics.error_breakdown:
        print(f"  ❌ Error Breakdown: {metrics.error_breakdown}")
```

______________________________________________________________________

**创建日期**: 2025-10-13\
**版本**: 1.0\
**相关文件**:

- `packages/sage-kernel/src/sage/kernel/runtime/monitoring/metrics.py`
- `packages/sage-benchmark/.../pipelines/qa_monitoring_demo.py`
