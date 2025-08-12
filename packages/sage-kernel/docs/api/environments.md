# 环境管理 (Environments)

环境 (Environment) 是 SAGE Kernel 的核心概念，它定义了数据流应用的执行上下文。环境负责管理计算资源、调度任务、处理服务注册等。

## 🌍 环境类型

### 1. LocalEnvironment (本地环境)

适用于单机开发、测试和小规模数据处理。

```python
from sage.core.api.local_environment import LocalEnvironment

# 创建本地环境
env = LocalEnvironment("my_local_app")

# 配置选项
env = LocalEnvironment(
    name="my_app",
    config={
        "parallelism": 4,          # 并行度
        "buffer_size": 10000,      # 缓冲区大小
        "checkpoint_interval": 30  # 检查点间隔(秒)
    }
)
```

### 2. RemoteEnvironment (远程环境)

适用于生产环境和分布式集群部署。

```python
from sage.core.api.remote_environment import RemoteEnvironment

# 创建远程环境
env = RemoteEnvironment(
    name="my_cluster_app",
    config={
        "jobmanager_host": "cluster-master",
        "jobmanager_port": 8081,
        "taskmanager_slots": 8
    }
)
```

## 🔧 环境配置

### 基础配置

```python
config = {
    # 执行配置
    "parallelism": 4,              # 默认并行度
    "max_parallelism": 128,        # 最大并行度
    "buffer_size": 10000,          # 数据缓冲区大小
    
    # 容错配置
    "restart_strategy": "fixed-delay",
    "restart_attempts": 3,
    "restart_delay": "10s",
    
    # 检查点配置
    "checkpointing_enabled": True,
    "checkpoint_interval": "30s",
    "checkpoint_timeout": "10m",
    
    # 日志配置
    "log_level": "INFO",
    "log_file": "./logs/sage.log"
}

env = LocalEnvironment("my_app", config=config)
```

### 高级配置

```python
# 性能调优配置
performance_config = {
    "network_buffer_size": "64mb",
    "sort_buffer_size": "64mb", 
    "hash_table_size": "1gb",
    "managed_memory_fraction": 0.7,
    "network_memory_fraction": 0.1,
    "jvm_heap_size": "2g"
}

# 安全配置  
security_config = {
    "security_enabled": True,
    "kerberos_principal": "sage@REALM.COM",
    "ssl_enabled": True,
    "ssl_keystore": "./ssl/keystore.jks"
}
```

## 📊 数据源创建

### 批处理数据源

```python
# 从集合创建
stream = env.from_batch([1, 2, 3, 4, 5])

# 从文件创建
stream = env.from_text_file("./data/input.txt")

# 从多个文件创建
stream = env.from_text_files("./data/*.txt")
```

### 流数据源

```python
# Kafka数据源
stream = env.from_kafka_source(
    bootstrap_servers="localhost:9092",
    topic="my_topic",
    group_id="my_consumer_group",
    auto_offset_reset="latest"
)

# Socket数据源
stream = env.from_socket_text_stream("localhost", 9999)

# 自定义数据源
class MySource(SourceFunction[str]):
    def run(self, ctx):
        for i in range(100):
            ctx.emit(f"Message {i}")
            time.sleep(1)

stream = env.add_source(MySource())
```

## 🛠️ 服务管理

### 服务注册

```python
# 注册服务类
env.register_service("cache", RedisCacheService, 
                    host="localhost", port=6379)

# 注册服务工厂
from sage.middleware import create_kv_service_factory

kv_factory = create_kv_service_factory("my_kv", backend_type="memory")
env.register_service_factory("my_kv", kv_factory)
```

### 服务使用

```python
# 在处理函数中使用服务
class ProcessFunction(MapFunction[str, str]):
    def map(self, value: str) -> str:
        # 获取服务代理
        cache = self.get_runtime_context().get_service("cache")
        
        # 使用服务
        result = cache.get(value)
        if result is None:
            result = expensive_computation(value)
            cache.put(value, result)
        
        return result

stream.map(ProcessFunction())
```

## 🚀 任务提交和管理

### 提交任务

```python
# 同步提交 (阻塞)
env.submit()

# 异步提交 (非阻塞)
job_id = env.submit_async()

# 带参数提交
env.submit(
    job_name="my_processing_job",
    save_point_path="./savepoints/sp_001",
    allow_non_restored_state=False
)
```

### 任务控制

```python
# 停止任务
env.stop()

# 取消任务
env.cancel()

# 暂停任务
env.pause()

# 恢复任务
env.resume()

# 创建保存点
savepoint_path = env.create_savepoint()

# 从保存点恢复
env.restore_from_savepoint("./savepoints/sp_001")
```

## 📊 监控和调试

### 性能监控

```python
# 启用指标收集
env.enable_metrics(
    reporters=["jmx", "prometheus"],
    interval="10s"
)

# 自定义指标
counter = env.get_metric_group().counter("my_counter")
histogram = env.get_metric_group().histogram("my_histogram")

class MyMapFunction(MapFunction[str, str]):
    def map(self, value: str) -> str:
        counter.inc()  # 增加计数器
        
        start_time = time.time()
        result = process(value)
        histogram.update(time.time() - start_time)  # 记录处理时间
        
        return result
```

### 日志配置

```python
# 配置日志
env.set_log_level("DEBUG")
env.set_log_file("./logs/my_app.log")

# 结构化日志
logger = env.get_logger("MyFunction")
logger.info("Processing record", extra={"record_id": 123})
```

## 🔧 最佳实践

### 1. 环境生命周期管理

```python
def main():
    env = None
    try:
        env = LocalEnvironment("my_app")
        
        # 构建数据流管道
        stream = env.from_batch(data)
        stream.map(process).sink(output)
        
        # 提交执行
        env.submit()
        
    except Exception as e:
        logger.error(f"Job failed: {e}")
    finally:
        if env:
            env.close()  # 确保资源清理
```

### 2. 配置外部化

```python
# config.yaml
parallelism: 4
buffer_size: 10000
checkpoint_interval: 30s

# Python代码
import yaml

with open("config.yaml") as f:
    config = yaml.safe_load(f)

env = LocalEnvironment("my_app", config=config)
```

### 3. 错误处理

```python
# 设置重启策略
env.set_restart_strategy(
    strategy="exponential-delay",
    max_attempts=5,
    initial_delay="1s",
    max_delay="1m",
    backoff_multiplier=2.0
)

# 自定义错误处理
class ErrorHandler(ProcessFunction[str, str]):
    def process(self, value: str, ctx: ProcessContext) -> str:
        try:
            return risky_operation(value)
        except Exception as e:
            # 发送到错误流
            ctx.output_to_side("errors", f"Error: {e}, Value: {value}")
            return None  # 过滤掉错误数据

main_stream, error_stream = stream.process(ErrorHandler()).split()
```

### 4. 资源优化

```python
# 合理设置并行度
env.set_parallelism(min(cpu_count(), len(input_partitions)))

# 启用对象重用
env.enable_object_reuse()

# 配置内存管理
env.set_managed_memory_fraction(0.7)
env.set_network_memory_fraction(0.1)
```

## 📚 相关文档

- [数据流处理](datastreams.md) - 数据流操作详解
- [函数接口](functions.md) - 用户自定义函数
- [分布式部署](../guides/distributed-deployment.md) - 集群部署指南
- [性能优化](../guides/performance.md) - 性能调优技巧
