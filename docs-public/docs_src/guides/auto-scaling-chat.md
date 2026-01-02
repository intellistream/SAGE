# 智能扩缩容聊天系统

基于 SAGE 框架构建的自动扩缩容聊天系统，展示弹性资源管理和负载均衡能力。

## 概述

自动扩缩容聊天系统演示了 SAGE 在云资源管理和弹性伸缩方面的能力。通过模拟可变的用户负载，系统自动调整服务器数量，实现资源优化和负载均衡。

## 核心功能

### 1. 用户流量模拟

- 可变负载模式（渐增、峰值、渐减）
- 可配置基准负载和峰值负载
- 真实的流量模拟

### 2. 自动扩缩容

- 基于负载阈值的扩容决策
- 自动缩容节省资源
- 冷却期防止频繁扩缩
- 可配置的最小/最大服务器数

### 3. 负载均衡

- 轮询（Round-Robin）分发
- 服务器负载跟踪
- 动态调整分发策略

### 4. 性能监控

- 实时负载监控
- 吞吐量统计
- 扩缩容事件记录
- 资源利用率分析

## 技术架构

### SAGE 算子管道

```
UserTrafficSource (BatchFunction)
    ↓
AutoScaler (MapFunction)
    ↓
LoadBalancer (MapFunction)
    ↓
RequestProcessor (MapFunction)
    ↓
MetricsCollector (SinkFunction)
```

### 算子说明

| 算子              | 类型          | 功能                   |
| ----------------- | ------------- | ---------------------- |
| UserTrafficSource | BatchFunction | 生成模拟用户请求       |
| AutoScaler        | MapFunction   | 扩缩容决策引擎         |
| LoadBalancer      | MapFunction   | 请求分发到服务器       |
| RequestProcessor  | MapFunction   | 模拟请求处理           |
| MetricsCollector  | SinkFunction  | 收集性能指标           |
| ScalingEventsSink | SinkFunction  | 记录扩缩容事件（可选） |

## 使用方法

### 基本使用

```python
from sage.apps.auto_scaling_chat import run_auto_scaling_demo

# 使用默认配置（30秒模拟）
run_auto_scaling_demo()
```

### 自定义负载模式

```python
run_auto_scaling_demo(
    duration=60,        # 模拟 60 秒
    base_rate=10,       # 基准负载：10 并发用户
    peak_rate=100,      # 峰值负载：100 并发用户
    verbose=True        # 显示详细日志
)
```

### 命令行使用

```bash
# 默认配置
python -m sage.apps.auto_scaling_chat.pipeline

# 短时高负载测试
python -m sage.apps.auto_scaling_chat.pipeline \
    --duration 20 \
    --peak-rate 80

# 长时间模拟
python -m sage.apps.auto_scaling_chat.pipeline \
    --duration 120 \
    --base-rate 5 \
    --peak-rate 60 \
    --verbose

# 使用示例脚本
python examples/apps/run_auto_scaling_chat.py --duration 30
```

## 扩缩容策略

### 默认策略

- **扩容阈值**：平均每服务器负载 > 30 用户
- **缩容阈值**：平均每服务器负载 < 10 用户
- **最小服务器数**：2
- **最大服务器数**：10
- **冷却时间**：5 秒

### 自定义策略

```python
from sage.apps.auto_scaling_chat.operators import AutoScaler

scaler = AutoScaler(
    scale_up_threshold=25,      # 更早扩容
    scale_down_threshold=5,     # 更激进缩容
    min_servers=1,              # 允许单服务器
    max_servers=20,             # 更大规模
)
```

## 输出示例

```
⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡
          SAGE Auto-Scaling Chat System Demo
⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡

======================================================================
📋 Configuration
======================================================================
   Simulation duration: 30s
   Base load: 5 concurrent users
   Peak load: 50 concurrent users
======================================================================

🚀 Starting auto-scaling simulation...

⚠️ Scaling Threshold Reached! Load: 35, Scaling up to 3 servers
📊 Load:  20 users | Servers:  2 | Requests:   10
📊 Load:  35 users | Servers:  3 | Requests:   20
⚠️ Scaling Threshold Reached! Load: 48, Scaling up to 4 servers
📊 Load:  50 users | Servers:  4 | Requests:   30
📊 Load:  45 users | Servers:  4 | Requests:   40
📊 Load:  30 users | Servers:  4 | Requests:   50
📊 Load:  15 users | Servers:  3 | Requests:   60
📊 Load:   8 users | Servers:  2 | Requests:   70

======================================================================
📊 Auto-Scaling System Metrics
======================================================================
   Total requests processed: 245
   Total duration: 30.15s
   Average throughput: 8.13 req/s
   Peak load: 50 concurrent users
   Peak servers: 4
   Scaling events: 5
   Average load: 28.3 users
   Average servers: 3.2
======================================================================

🔄 Scaling Events:
   1. 📈 SCALE_UP: 3 servers (load: 35)
   2. 📈 SCALE_UP: 4 servers (load: 48)
   3. 📉 SCALE_DOWN: 3 servers (load: 18)
   4. 📉 SCALE_DOWN: 2 servers (load: 8)
======================================================================
```

## 应用场景

### 云应用

- Web 应用弹性伸缩
- API 网关自动扩容
- 微服务架构

### 聊天系统

- 即时通讯服务
- 在线客服系统
- 游戏聊天服务器

### 流式处理

- 实时数据处理
- 事件驱动系统
- 流媒体服务

## 负载模式

### 系统内置模式

**三阶段负载**：

- 阶段 1 (0-30%)：渐增期
- 阶段 2 (30-70%)：峰值期
- 阶段 3 (70-100%)：渐减期

### 自定义模式（Future）

```python
def custom_load_pattern(progress):
    # 自定义负载曲线
    if progress < 0.2:
        return base_rate
    elif progress < 0.8:
        return peak_rate * (1 + 0.2 * sin(progress * 10))
    else:
        return base_rate
```

## 性能指标

### 系统跟踪的指标

- **请求总数**：处理的请求数量
- **平均吞吐量**：请求/秒
- **峰值负载**：最高并发用户数
- **峰值服务器数**：使用的最大服务器数
- **扩缩容次数**：策略执行次数
- **平均负载**：整体平均用户数
- **平均服务器数**：资源利用情况
- **处理延迟**：请求响应时间（Future）

## 集成云服务（Future）

### AWS 集成

```python
from sage.apps.auto_scaling_chat.cloud import AWSIntegration

# 集成 AWS Auto Scaling
aws = AWSIntegration(
    region="us-west-2",
    instance_type="t3.medium"
)

# 使用真实的 EC2 实例
run_auto_scaling_demo(cloud_provider=aws)
```

### Kubernetes 集成

```python
from sage.apps.auto_scaling_chat.cloud import K8sIntegration

# 集成 Kubernetes HPA
k8s = K8sIntegration(
    namespace="chat-system",
    deployment="chat-servers"
)
```

## 相关资源

- [源代码](https://github.com/intellistream/SAGE/tree/main/packages/sage-apps/src/sage/apps/auto_scaling_chat)
- [示例脚本](https://github.com/intellistream/SAGE/tree/main/examples/apps/run_auto_scaling_chat.py)
- [云原生最佳实践](best-practices/index.md)
- [性能调优指南](../tutorials/advanced/performance-tuning.md)

## 下一步

- 尝试 [文章监控系统](article-monitoring.md)
- 探索 [智能家居系统](smart-home.md)
- 查看更多 [应用示例](applications.md)
