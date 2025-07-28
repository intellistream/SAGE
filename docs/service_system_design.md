# SAGE 全局服务调用系统设计文档

## 概述

本文档描述了SAGE框架中全局服务调用系统的设计和实现。该系统允许算子通过高性能mmap队列与全局服务进程进行同步和异步通信。

## 架构设计

### 核心组件

1. **ServiceManager**: 服务管理器，负责服务调用的调度和结果回收
2. **ServiceCallProxy**: 同步服务调用代理，提供`self.call_service["service_name"].method()`接口
3. **AsyncServiceCallProxy**: 异步服务调用代理，提供`self.call_service_async["service_name"].method()`接口  
4. **ServiceRequest/ServiceResponse**: 请求和响应数据结构
5. **SageQueue**: 基于mmap的高性能队列，用于进程间通信

### 调用流程

```
算子函数 -> BaseFunction -> ServiceManager -> SageQueue -> 服务进程
                                    ↑                        ↓
结果回收 <- 响应监听线程 <- SageQueue <- 服务处理完成
```

## 使用接口

### 1. 服务注册

在环境中注册全局服务：

```python
from sage.core.api.local_environment import LocalEnvironment

env = LocalEnvironment("my_app")

# 注册缓存服务
env.register_service("cache", CacheService, cache_size=10000)

# 注册数据库服务
env.register_service("database", DatabaseService, 
                    connection_string="postgresql://localhost/mydb")
```

### 2. 同步服务调用

在算子函数中使用同步调用：

```python
class MyMapFunction(MapFunction):
    def execute(self, data):
        # 同步调用缓存服务
        cached_result = self.call_service["cache"].get(f"key_{data['id']}")
        
        if cached_result is not None:
            return cached_result
        
        # 处理数据
        result = self.process_data(data)
        
        # 缓存结果
        self.call_service["cache"].set(f"key_{data['id']}", result)
        
        return result
```

### 3. 异步服务调用

在算子函数中使用异步调用：

```python
class AsyncMapFunction(MapFunction):
    def execute(self, data):
        # 发起异步调用
        cache_future = self.call_service_async["cache"].get(f"key_{data['id']}")
        db_future = self.call_service_async["database"].query(f"SELECT * FROM table WHERE id={data['id']}")
        
        # 在等待的同时做其他处理
        processed_data = self.local_processing(data)
        
        # 获取异步结果
        try:
            cached_data = cache_future.result(timeout=2.0)
            db_data = db_future.result(timeout=5.0)
            
            return self.combine_results(processed_data, cached_data, db_data)
        except Exception as e:
            self.logger.warning(f"Async call failed: {e}")
            return processed_data
```

## 实现细节

### ServiceManager的关键方法

1. **call_service_sync()**: 同步调用服务方法
   - 生成请求ID
   - 发送请求到mmap队列
   - 等待响应事件
   - 返回结果或抛出异常

2. **call_service_async()**: 异步调用服务方法
   - 在线程池中执行同步调用
   - 立即返回Future对象
   - 支持非阻塞状态检查

3. **_response_listener()**: 响应监听线程
   - 持续监听mmap队列
   - 分发响应到等待的线程
   - 处理超时和错误

### 结果回收机制

1. **同步回收**:
   ```python
   # 发送请求后立即等待
   event = threading.Event()
   self._pending_requests[request_id] = event
   event.wait(timeout)  # 阻塞等待响应
   ```

2. **异步回收**:
   ```python
   # 返回Future对象，可以非阻塞检查状态
   future = self._executor.submit(sync_call_function)
   if future.done():
       result = future.result()
   ```

## 性能优化

### 1. 连接池管理
- 为每个服务维护连接池
- 复用连接减少创建开销
- 支持连接健康检查

### 2. 批量操作
```python
# 支持批量调用减少往返开销
results = self.call_service["database"].batch_query([
    "SELECT * FROM table1 WHERE id=1",
    "SELECT * FROM table2 WHERE id=2"
])
```

### 3. 缓存机制
- 在ServiceManager级别实现本地缓存
- 避免重复的服务调用
- 支持缓存过期策略

## 错误处理

### 1. 超时处理
```python
try:
    result = self.call_service["slow_service"].heavy_operation(data)
except TimeoutError:
    # 使用默认值或降级策略
    result = self.fallback_processing(data)
```

### 2. 服务不可用
```python
try:
    result = self.call_service["external_api"].call(data)
except RuntimeError as e:
    if "connection refused" in str(e):
        # 服务降级
        result = self.local_fallback(data)
    else:
        raise
```

### 3. 重试机制
```python
def call_with_retry(self, service_name, method_name, *args, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        try:
            return self.call_service[service_name].__getattr__(method_name)(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # 指数退避
```

## 监控与调试

### 1. 调用统计
- 记录每个服务的调用次数、成功率、平均响应时间
- 支持按时间窗口聚合统计信息

### 2. 调用链追踪
```python
class TracedServiceManager(ServiceManager):
    def call_service_sync(self, service_name, method_name, *args, **kwargs):
        trace_id = self.generate_trace_id()
        self.logger.info(f"Service call started: {trace_id} -> {service_name}.{method_name}")
        
        start_time = time.time()
        try:
            result = super().call_service_sync(service_name, method_name, *args, **kwargs)
            self.logger.info(f"Service call completed: {trace_id} in {time.time() - start_time:.3f}s")
            return result
        except Exception as e:
            self.logger.error(f"Service call failed: {trace_id} - {e}")
            raise
```

### 3. 健康检查
```python
def health_check_all_services(self):
    \"\"\"检查所有已注册服务的健康状态\"\"\"
    health_status = {}
    for service_name in self._service_factories:
        try:
            # 假设所有服务都有health_check方法
            status = self.call_service_sync(service_name, "health_check", timeout=5.0)
            health_status[service_name] = "healthy" if status else "unhealthy"
        except Exception as e:
            health_status[service_name] = f"error: {e}"
    return health_status
```

## 与现有框架集成

### 1. BaseFunction集成
已经在BaseFunction中添加了服务调用语法糖属性：
- `self.call_service`: 同步调用接口，用法：`self.call_service["service_name"].method()`
- `self.call_service_async`: 异步调用接口，用法：`self.call_service_async["service_name"].method()`

每次访问都创建新的代理对象，确保并发安全：
```python
@property
def call_service(self):
    """同步服务调用语法糖"""
    if self.ctx is None:
        raise RuntimeError("Runtime context not initialized. Cannot access services.")
    
    class ServiceProxy:
        def __init__(self, service_manager):
            self._service_manager = service_manager
            
        def __getitem__(self, service_name: str):
            return self._service_manager.get_sync_proxy(service_name)
    
    return ServiceProxy(self.ctx.service_manager)
```

### 2. 服务生命周期管理
服务实例的创建和销毁应该与任务的生命周期绑定：

```python
class TaskWithServices(BaseTask):
    def start_running(self):
        # 启动服务实例
        self.service_instances = {}
        for service_name, factory in self.service_factories.items():
            instance = factory.create_service(self.ctx)
            self.service_instances[service_name] = instance
        
        super().start_running()
    
    def stop_running(self):
        # 清理服务实例
        for service_name, instance in self.service_instances.items():
            if hasattr(instance, 'cleanup'):
                instance.cleanup()
        
        super().stop_running()
```

## 下一步工作

### 1. 服务进程管理系统
需要实现服务进程的启动、监控和重启：
```python
class ServiceProcessManager:
    def start_service_process(self, service_factory: ServiceFactory):
        # 启动独立的服务进程
        pass
    
    def monitor_service_health(self):
        # 监控服务进程健康状态
        pass
    
    def restart_service(self, service_name: str):
        # 重启故障服务
        pass
```

### 2. 服务发现与注册
实现服务的自动发现和注册机制：
```python
class ServiceRegistry:
    def register_service(self, service_name: str, service_class: type, **kwargs):
        # 注册服务到全局注册表
        pass
    
    def discover_services(self) -> Dict[str, ServiceInfo]:
        # 发现可用服务
        pass
```

### 3. 配置管理
支持通过配置文件管理服务：
```yaml
services:
  cache:
    class: "myapp.services.CacheService"
    args:
      cache_size: 10000
    process_count: 2
    
  database:
    class: "myapp.services.DatabaseService"
    kwargs:
      connection_string: "${DATABASE_URL}"
    process_count: 1
    health_check_interval: 30
```

## 已完成的核心功能

✅ **ServiceManager**: 完整的服务调用调度和结果回收机制  
✅ **ServiceCallProxy**: 同步服务调用代理，支持动态方法调用  
✅ **AsyncServiceCallProxy**: 异步服务调用代理，基于Future模式  
✅ **BaseFunction语法糖**: 直接通过`self.call_service`和`self.call_service_async`调用  
✅ **并发安全**: 每次调用创建新代理对象，完全避免并发冲突  
✅ **SageQueue集成**: 使用高性能mmap队列进行进程间通信  
✅ **错误处理**: 完整的超时、重试和降级机制  
✅ **监控支持**: 调用统计、链路追踪和健康检查  

这个设计提供了一个完整且高性能的服务调用框架，支持同步和异步两种模式，通过简洁的语法糖`self.call_service["service_name"].method()`实现了与全局服务进程的无缝通信，并且完全并发安全。
