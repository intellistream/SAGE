# SAGE 作业管理器 (JobManager)

JobManager是SAGE框架的核心调度组件，负责分布式环境下作业的提交、调度、执行和监控，提供高可用、高性能的作业管理服务。

## 模块概述

JobManager模块实现了完整的分布式作业管理系统，支持作业的生命周期管理、资源调度、故障恢复和性能监控，是SAGE框架分布式计算能力的核心。

## 核心组件

### `job_manager.py`
作业管理器核心：
- 作业生命周期管理（提交、调度、执行、完成）
- 分布式作业调度算法
- 资源分配和负载均衡
- 作业依赖关系处理
- 故障检测和自动恢复

### `job_manager_server.py`
作业管理器服务端：
- 提供作业管理的RPC服务接口
- 处理客户端的作业提交请求
- 实现作业状态查询和控制
- 支持实时作业监控和日志流
- 提供系统健康检查和统计信息

### `jobmanager_client.py`
作业管理器客户端：
- 提供简洁的作业提交API
- 支持作业状态查询和控制
- 实现作业监控和日志获取
- 提供批量作业操作接口
- 支持异步和同步操作模式

### `execution_graph.py`
执行图管理：
- 将逻辑作业图转换为执行图
- 支持作业依赖关系和优先级
- 实现图优化和并行化分析
- 提供执行进度跟踪和可视化
- 支持动态图修改和重调度

### `job_info.py`
作业信息管理：
- 定义作业元数据结构
- 管理作业状态和生命周期信息
- 提供作业序列化和持久化
- 支持作业历史记录和审计
- 实现作业信息的查询和统计

### [工具模块](./utils/)
JobManager相关的辅助工具和服务。

### [测试模块](./tests/)
完整的JobManager功能测试覆盖。

## 主要特性

- **高可用性**: 主备模式，自动故障转移
- **高性能**: 支持大规模并发作业调度
- **弹性扩展**: 动态资源分配和集群扩缩容
- **容错机制**: 作业故障自动重试和恢复
- **实时监控**: 全方位的作业和系统监控

## 架构设计

### 系统架构
```
┌─────────────────┐    ┌─────────────────┐
│   SAGE CLI      │    │   Web Dashboard │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          └──────────┬───────────┘
                     │
          ┌─────────────────┐
          │  JobManager     │
          │    Server       │
          └─────────┬───────┘
                    │
     ┌──────────────┼──────────────┐
     │              │              │
┌────▼────┐   ┌────▼────┐   ┌────▼────┐
│ Worker  │   │ Worker  │   │ Worker  │
│  Node   │   │  Node   │   │  Node   │
└─────────┘   └─────────┘   └─────────┘
```

### 作业生命周期
```
SUBMITTED → PENDING → RUNNING → COMPLETED
     │         │         │         │
     │         │         ├─→ FAILED
     │         │         │
     │         └─→ CANCELLED
     │
     └─→ REJECTED
```

## 使用场景

### 批处理作业
- 大规模数据处理任务
- 机器学习模型训练
- 科学计算和仿真
- 数据分析和挖掘

### 流式处理
- 实时数据流处理
- 事件驱动的计算任务
- 在线推理和预测
- 实时监控和告警

### 混合工作负载
- 批流混合处理
- 交互式查询分析
- A/B测试和实验
- 多租户资源隔离

## 快速开始

### 启动JobManager服务
```python
from sage.jobmanager import JobManagerServer

# 创建并启动JobManager服务
server = JobManagerServer(
    host="0.0.0.0",
    port=19001,
    ray_address="auto"  # 或具体的Ray集群地址
)

server.start()
```

### 提交作业
```python
from sage.jobmanager import JobManagerClient

# 连接到JobManager
client = JobManagerClient("localhost:19001")

# 提交Python脚本作业
job_id = client.submit_script(
    script_path="my_analysis.py",
    args=["--input", "data.csv", "--output", "result.json"],
    resources={"cpu": 4, "memory": "8GB"}
)

# 监控作业状态
status = client.get_job_status(job_id)
print(f"Job {job_id} status: {status}")

# 获取作业结果
if status == "COMPLETED":
    result = client.get_job_result(job_id)
    print(f"Job result: {result}")
```

### 提交SAGE管道作业
```python
from sage.api.env import RemoteEnvironment

# 创建远程执行环境
env = RemoteEnvironment(
    "data_pipeline",
    jobmanager_address="localhost:19001"
)

# 构建数据流管道
source_stream = env.source(FileSource, path="input.csv")
processed_stream = source_stream.map(ProcessFunction)
processed_stream.sink(FileSink, path="output.json")

# 提交并执行管道
job_id = env.submit()
env.wait_for_completion(job_id)
```

## 高级特性

### 作业依赖管理
```python
# 定义作业依赖关系
job1 = client.submit_script("preprocess.py")
job2 = client.submit_script("train_model.py", dependencies=[job1])
job3 = client.submit_script("evaluate.py", dependencies=[job2])

# JobManager会自动按依赖顺序执行
```

### 资源管理
```python
# 指定资源需求
job_id = client.submit_script(
    "heavy_computation.py",
    resources={
        "cpu": 16,
        "memory": "32GB",
        "gpu": 2,
        "custom_resources": {"TPU": 1}
    }
)
```

### 故障恢复
```python
# 配置重试策略
job_id = client.submit_script(
    "fault_tolerant.py",
    retry_policy={
        "max_retries": 3,
        "retry_delay": 60,  # 秒
        "retry_exponential_base": 2
    }
)
```

## 配置选项

### 服务器配置
```yaml
jobmanager:
  host: "0.0.0.0"
  port: 19001
  max_jobs: 1000
  job_timeout: 3600
  heartbeat_interval: 30
  
ray:
  address: "auto"
  dashboard_host: "0.0.0.0"
  dashboard_port: 8265

storage:
  type: "local"  # local, s3, hdfs
  path: "/tmp/sage_storage"
  
logging:
  level: "INFO"
  file: "/var/log/sage/jobmanager.log"
```

### 客户端配置
```python
client_config = {
    "timeout": 30,
    "retry_attempts": 3,
    "connection_pool_size": 10,
    "heartbeat_interval": 60
}

client = JobManagerClient(
    "jobmanager.example.com:19001",
    config=client_config
)
```

## 监控和运维

### 性能指标
- 作业提交吞吐量
- 作业平均执行时间
- 资源利用率
- 系统负载和延迟

### 健康检查
```python
# 检查JobManager健康状态
health = client.health_check()
print(f"JobManager health: {health}")

# 获取系统统计信息
stats = client.get_statistics()
print(f"Active jobs: {stats['active_jobs']}")
print(f"Total jobs: {stats['total_jobs']}")
```

### 日志和调试
```python
# 获取作业日志
logs = client.get_job_logs(job_id)
for log_entry in logs:
    print(f"[{log_entry.timestamp}] {log_entry.message}")

# 实时日志流
for log_entry in client.stream_job_logs(job_id):
    print(f"[{log_entry.timestamp}] {log_entry.message}")
```

## 最佳实践

1. **资源规划**: 合理估算作业资源需求
2. **错误处理**: 实现完善的错误处理和重试逻辑
3. **监控告警**: 设置合适的监控指标和告警规则
4. **数据管理**: 正确处理输入输出数据的存储和传输
5. **安全考虑**: 实施访问控制和数据加密

JobManager为SAGE框架提供了强大的分布式作业管理能力，使得大规模数据处理和机器学习任务的部署和管理变得简单高效。
