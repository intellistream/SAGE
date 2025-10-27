# SAGE Performance Monitoring System

完整的性能监控和状态汇报系统，用于SAGE流计算任务和服务的性能分析和优化。

## 功能特性

### ✅ P0 级别功能（已实现）

- ✅ **包级别性能监控**：监测每个数据包在任务中的处理时间
- ✅ **任务级别性能汇总**：
  - 吞吐量统计（TPS/QPS）
  - 延迟分析（最小、最大、平均、P50/P95/P99延迟）
  - 错误统计和分类
- ✅ **时间窗口统计**：支持最近1分钟、5分钟、1小时的性能趋势
- ✅ **资源使用监控**：CPU和内存使用情况（需要psutil）
- ✅ **性能指标查询接口**：实时获取和导出性能指标
- ✅ **多种导出格式**：JSON、Prometheus、CSV、人类可读格式

### 📊 核心组件

1. **MetricsCollector**：性能指标收集器

   - 包级别性能监控
   - 百分位数计算
   - 时间窗口统计
   - 错误分类统计

1. **ResourceMonitor**：资源使用监控器

   - CPU使用率监控
   - 内存使用量监控
   - 进程级别资源统计
   - 系统级资源信息

1. **MetricsReporter**：性能指标汇报器

   - 定期汇报
   - 多种导出格式
   - 自定义汇报回调

## 安装

### 基础安装

```bash
pip install isage-kernel
```

### 安装资源监控支持

```bash
pip install isage-kernel[monitoring]
# 或
pip install psutil
```

## 使用方法

### 1. 在 BaseTask 中启用监控

```python
from sage.kernel.runtime.context.task_context import TaskContext

# 创建带监控的任务上下文
ctx = TaskContext(
    name="my_task",
    enable_monitoring=True,  # 启用监控
    metrics_window_size=10000,  # 滑动窗口大小
    enable_detailed_tracking=True,  # 启用详细跟踪
    resource_sampling_interval=1.0,  # 资源采样间隔（秒）
    enable_auto_report=True,  # 启用自动汇报
    report_interval=60,  # 汇报间隔（秒）
)
```

### 2. 获取性能指标

```python
# 获取当前性能指标
metrics = task.get_current_metrics()

if metrics:
    print(f"Task: {metrics.task_name}")
    print(f"TPS: {metrics.packets_per_second:.2f}")
    print(f"Avg Latency: {metrics.avg_latency:.2f}ms")
    print(f"P99 Latency: {metrics.p99_latency:.2f}ms")
    print(f"CPU: {metrics.cpu_usage_percent:.2f}%")
    print(f"Memory: {metrics.memory_usage_mb:.2f}MB")
```

### 3. 导出性能指标

```python
# 导出为 JSON 格式
json_metrics = task.export_metrics(format="json")

# 导出为 Prometheus 格式
prom_metrics = task.export_metrics(format="prometheus")

# 导出为人类可读格式
human_metrics = task.export_metrics(format="human")
print(human_metrics)
```

### 4. 直接使用监控组件

```python
from sage.kernel.runtime.monitoring import (
    MetricsCollector,
    ResourceMonitor,
    MetricsReporter,
)

# 创建收集器
collector = MetricsCollector(
    name="my_component",
    window_size=1000,
)

# 记录包处理
packet_id = collector.record_packet_start(packet_size=100)
# ... 处理逻辑 ...
collector.record_packet_end(packet_id, success=True)

# 获取指标
metrics = collector.get_real_time_metrics()

# 创建资源监控器
monitor = ResourceMonitor(
    sampling_interval=1.0,
    enable_auto_start=True,
)

# 获取资源使用情况
cpu, memory = monitor.get_current_usage()

# 创建报告器
reporter = MetricsReporter(
    metrics_collector=collector,
    resource_monitor=monitor,
    report_interval=60,
    enable_auto_report=True,
)
```

## 数据结构

### TaskPerformanceMetrics

```python
@dataclass
class TaskPerformanceMetrics:
    task_name: str
    uptime: float
    total_packets_processed: int
    total_packets_failed: int
    packets_per_second: float

    # 延迟统计（毫秒）
    min_latency: float
    max_latency: float
    avg_latency: float
    p50_latency: float
    p95_latency: float
    p99_latency: float

    # 队列统计
    input_queue_depth: int
    input_queue_avg_wait_time: float

    # 资源使用
    cpu_usage_percent: float
    memory_usage_mb: float

    # 错误统计
    error_breakdown: Dict[str, int]

    # 时间窗口统计
    last_minute_tps: float
    last_5min_tps: float
    last_hour_tps: float
```

### ServicePerformanceMetrics

```python
@dataclass
class ServicePerformanceMetrics:
    service_name: str
    uptime: float
    total_requests_processed: int
    total_requests_failed: int
    requests_per_second: float

    # 响应时间统计（毫秒）
    min_response_time: float
    max_response_time: float
    avg_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float

    # 资源使用
    cpu_usage_percent: float
    memory_usage_mb: float

    # 并发统计
    concurrent_requests: int
    max_concurrent_requests: int
```

## 配置选项

在 TaskContext 或 ServiceContext 中可配置：

```python
# 监控配置
enable_monitoring: bool = False  # 是否启用监控
metrics_window_size: int = 10000  # 滑动窗口大小
enable_detailed_tracking: bool = True  # 是否启用详细跟踪
resource_sampling_interval: float = 1.0  # 资源采样间隔（秒）

# 汇报配置
enable_auto_report: bool = False  # 是否启用自动汇报
report_interval: int = 60  # 汇报间隔（秒）
```

## 示例

查看完整示例：

```bash
python packages/sage-kernel/examples/monitoring_example.py
```

示例输出：

```
================================================================================
Performance Report: integrated_task
================================================================================
Timestamp: 2025-10-13 12:34:56
Uptime: 5.23s

Throughput:
  Total Processed: 50
  Total Failed: 5
  Success Rate: 90.00%
  Current TPS: 9.56
  Last Minute TPS: 9.56

Latency (milliseconds):
  Min: 10.12
  Max: 18.95
  Avg: 13.45
  P50: 13.21
  P95: 17.89
  P99: 18.76

Resources:
  CPU: 45.67%
  Memory: 234.56 MB

Errors:
  SimulatedError: 5
================================================================================
```

## 性能影响

- **监控开销**：< 1% CPU（默认配置）
- **内存占用**：约 10-50MB（取决于window_size）
- **推荐配置**：
  - 开发/调试：`enable_detailed_tracking=True`
  - 生产环境：`enable_detailed_tracking=False`（仅统计汇总数据）

## API 文档

### BaseTask API

```python
# 获取当前性能指标
def get_current_metrics() -> Optional[TaskPerformanceMetrics]

# 重置性能指标
def reset_metrics() -> None

# 导出性能指标
def export_metrics(format: str = "json") -> Optional[str]
```

### BaseServiceTask API

```python
# 获取当前性能指标
def get_current_metrics() -> Optional[ServicePerformanceMetrics]

# 重置性能指标
def reset_metrics() -> None

# 导出性能指标
def export_metrics(format: str = "json") -> Optional[str]
```

## 故障排除

### psutil 未安装

如果看到警告：

```
psutil not available, resource monitoring disabled
```

解决方法：

```bash
pip install psutil
```

### 监控未启用

确保在创建 TaskContext 时设置：

```python
ctx = TaskContext(
    name="my_task",
    enable_monitoring=True,  # 必须设置为 True
)
```

## 贡献

欢迎贡献！查看 [CONTRIBUTING.md](../../../CONTRIBUTING.md) 了解更多信息。

## 许可证

MIT License - 查看 [LICENSE](../../../LICENSE) 文件了解详情。
