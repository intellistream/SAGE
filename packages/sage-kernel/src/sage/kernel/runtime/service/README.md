# Runtime Service 模块

Runtime Service 模块提供服务任务的执行框架，支持本地和分布式服务调用机制。

## 快速开始

### 本地服务任务
```python
from sage.kernel.runtime.service.local_service_task import LocalServiceTask

# 创建并启动本地服务
service_task = LocalServiceTask(service_factory, runtime_context)
service_task.start_service()
```

### 服务调用
```python
from sage.kernel.runtime.service.service_caller import ServiceManager

# 同步调用服务
service_manager = ServiceManager(environment)
response = service_manager.call_service_sync(
    service_name="my_service",
    method="process_data",
    args=(data,),
    kwargs={"timeout": 30}
)
```

## 核心组件

- **`BaseServiceTask`**: 服务任务基类，集成 mmap 队列监听和消息处理
- **`LocalServiceTask`**: 本地进程内的服务任务执行
- **`RayServiceTask`**: 基于 Ray Actor 的分布式服务
- **`ServiceManager`**: 统一的服务调用管理器

## 服务类型

### 本地服务 vs 分布式服务

| 特性 | LocalServiceTask | RayServiceTask |
|------|-----------------|----------------|
| 部署 | 单机进程内 | 分布式集群 |
| 延迟 | 低 | 中等 |
| 扩展性 | 有限 | 水平可扩展 |
| 适用场景 | 开发测试 | 生产环境 |

## 📖 详细文档

更多详细的架构设计、通信机制和高级配置，请参阅：

**[📚 Runtime Services 完整文档](../../../docs-public/docs_src/kernel/runtime_services.md)**

包含完整的：
- 架构设计和组件说明
- 服务通信机制详解
- 高性能特性和优化
- 配置管理和扩展接口
- 最佳实践指南

@dataclass
class ServiceResponse:
    success: bool
    result: Any = None
    error: str = None
```

### 队列通信
- **请求队列**: 接收服务调用请求
- **响应队列**: 返回服务调用结果
- **队列命名**: 基于服务名和实例的唯一队列命名

### 消息处理流程
1. **请求接收**: 从请求队列接收调用请求
2. **参数解析**: 解析调用方法和参数
3. **服务执行**: 调用具体的服务方法
4. **结果返回**: 将结果发送到响应队列

## 高性能特性

### mmap 队列集成
```python
# 使用高性能队列适配器
self._request_queue = create_queue(
    name=self._request_queue_name
)
```

### 队列监听优化
- **独立线程**: 使用专门的线程监听队列
- **非阻塞模式**: 支持超时和中断机制
- **批量处理**: 支持批量请求处理

### 连接池管理
- **队列缓存**: 缓存常用的服务队列连接
- **连接复用**: 复用队列连接减少开销
- **资源清理**: 自动清理不活跃的连接

## 服务发现和注册

### 服务注册
```python
# 服务自动注册到环境
service_task = LocalServiceTask(service_factory, ctx)
environment.register_service(service_name, service_task)
```

### 服务发现
```python
# 通过服务管理器发现服务
service_manager = ServiceManager(environment)
service_queue = service_manager.get_service_queue(service_name)
```

### 健康检查
- **服务状态监控**: 定期检查服务健康状态
- **故障检测**: 检测服务故障和恢复
- **负载监控**: 监控服务的请求负载

## 并发和线程安全

### 线程池执行
```python
self._executor = ThreadPoolExecutor(
    max_workers=10, 
    thread_name_prefix="ServiceCall"
)
```

### 同步原语
- **线程锁**: 保护共享资源的访问
- **事件对象**: 用于请求/响应同步
- **原子操作**: 确保计数器等操作的原子性

### 异步支持
- **Future 对象**: 支持异步服务调用
- **回调机制**: 支持异步回调处理
- **超时控制**: 提供调用超时控制

## 错误处理和监控

### 异常处理
```python
try:
    result = self.service_instance.call_method(method_name, *args, **kwargs)
    response = ServiceResponse(success=True, result=result)
except Exception as e:
    self.logger.error(f"Service method execution failed: {e}")
    response = ServiceResponse(success=False, error=str(e))
```

### 性能监控
- **请求计数**: 跟踪服务请求数量
- **错误统计**: 统计服务调用错误
- **响应时间**: 测量服务响应时间
- **活跃度监控**: 监控服务最后活跃时间

### 日志记录
- **请求日志**: 记录所有服务请求
- **错误日志**: 详细记录服务错误
- **性能日志**: 记录性能相关指标

## 配置管理

### 服务配置
```yaml
service:
  local:
    max_workers: 10
    queue_timeout: 30
    request_queue_size: 10000
    
  ray:
    resources: {"CPU": 2}
    lifetime: "detached"
    max_restarts: 3
```

### 调用配置
```yaml
service_call:
  default_timeout: 30
  max_retries: 3
  retry_interval: 1
  async_pool_size: 20
```

## 扩展接口

### 自定义服务任务
```python
class CustomServiceTask(BaseServiceTask):
    def __init__(self, service_factory, ctx):
        super().__init__(service_factory, ctx)
        # 自定义初始化
    
    def custom_handle_request(self, request):
        # 自定义请求处理逻辑
        return self.service.process(request)
```

### 服务中间件
```python
class ServiceMiddleware:
    def before_call(self, request):
        # 调用前的处理逻辑
        pass
    
    def after_call(self, response):
        # 调用后的处理逻辑
        pass
```

## 最佳实践

### 服务设计
- **无状态设计**: 尽量设计无状态的服务
- **幂等性**: 确保服务操作的幂等性
- **资源管理**: 合理管理服务的资源使用

### 性能优化
- **批量处理**: 支持批量请求处理
- **缓存机制**: 适当使用缓存提高性能
- **连接复用**: 复用连接减少开销

### 故障处理
- **优雅降级**: 在部分故障时提供降级服务
- **重试机制**: 合理的重试策略
- **监控告警**: 及时发现和处理问题

## 参考

相关模块：
- `../task/`: 任务执行系统
- `../communication/`: 通信框架
- `../factory/`: 工厂创建模式
- `../../core/`: 核心服务定义
