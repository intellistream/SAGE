# [Feature Request] 灵活的服务任务部署配置 - 支持多机器、多线程部署策略

## 🎯 背景与需求

SAGE作为分布式流水线微服务架构，服务类（Service Class）通过Base Service Task进行通信和调度包装。为了满足不同客户的部署需求和性能要求，我们需要提供多样化的服务任务部署配置选项，让客户能够：

1. **灵活选择部署机器**：指定服务部署到特定机器或机器组
2. **自定义线程配置**：为服务内部配置不同的线程数量以优化性能
3. **动态资源分配**：根据负载和资源情况动态调整服务配置

## 🔍 当前架构分析

### 现有服务任务架构

```
Service Class (业务逻辑)
    ↓
BaseServiceTask (通信&调度包装)
    ↓
LocalServiceTask / RayServiceTask (部署实现)
    ↓
ServiceTaskFactory (创建工厂)
```

### 当前限制

1. **部署位置固定化**：服务部署位置主要通过`remote`布尔值控制（本地 vs Ray集群）
2. **线程配置缺失**：服务内部线程数量无法灵活配置
3. **资源配置单一**：缺乏细粒度的资源分配控制
4. **机器选择受限**：无法指定具体的机器或机器组进行部署

## 🎯 提案设计

### 1. 扩展服务部署配置

#### 新增`ServiceDeploymentConfig`配置类

```python
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum

class DeploymentTarget(Enum):
    LOCAL = "local"           # 本地部署
    REMOTE_ANY = "remote_any" # Ray集群任意节点
    REMOTE_SPECIFIC = "remote_specific"  # 指定Ray节点
    CLUSTER_GROUP = "cluster_group"      # 节点组

class ThreadingStrategy(Enum):
    SINGLE = "single"         # 单线程
    MULTI = "multi"           # 多线程
    POOL = "pool"             # 线程池
    ASYNC = "async"           # 异步协程

@dataclass
class ServiceDeploymentConfig:
    """服务部署配置"""
    
    # 部署位置配置
    target: DeploymentTarget = DeploymentTarget.LOCAL
    target_nodes: Optional[List[str]] = None  # 指定节点名称列表
    node_selector: Optional[Dict[str, str]] = None  # 节点选择器标签
    
    # 线程配置
    threading_strategy: ThreadingStrategy = ThreadingStrategy.SINGLE
    thread_count: int = 1                     # 线程数量
    max_thread_count: Optional[int] = None    # 最大线程数（动态扩展）
    thread_pool_size: Optional[int] = None    # 线程池大小
    
    # 资源配置
    cpu_cores: Optional[float] = None         # CPU核心数
    memory_mb: Optional[int] = None           # 内存MB
    gpu_count: Optional[int] = None           # GPU数量
    
    # 高可用配置
    replicas: int = 1                         # 副本数量
    load_balancing: bool = False              # 负载均衡
    failover_enabled: bool = False            # 故障转移
    
    # 性能配置
    queue_size: int = 1000                    # 请求队列大小
    timeout: float = 30.0                     # 请求超时时间
    batch_size: Optional[int] = None          # 批处理大小
    
    # 监控配置
    enable_metrics: bool = True               # 启用指标收集
    health_check_interval: float = 10.0       # 健康检查间隔
```

#### 扩展`ServiceTaskFactory`

```python
class ServiceTaskFactory:
    """扩展的服务任务工厂"""
    
    def __init__(self, 
                 service_factory: 'ServiceFactory', 
                 deployment_config: Optional[ServiceDeploymentConfig] = None):
        self.service_factory = service_factory
        self.service_name = service_factory.service_name
        self.deployment_config = deployment_config or ServiceDeploymentConfig()
        
    def create_service_task(self, ctx: 'ServiceContext' = None):
        """根据部署配置创建服务任务"""
        if self.deployment_config.target == DeploymentTarget.LOCAL:
            return self._create_local_service_task(ctx)
        elif self.deployment_config.target in [DeploymentTarget.REMOTE_ANY, 
                                               DeploymentTarget.REMOTE_SPECIFIC,
                                               DeploymentTarget.CLUSTER_GROUP]:
            return self._create_remote_service_task(ctx)
        else:
            raise ValueError(f"Unsupported deployment target: {self.deployment_config.target}")
    
    def _create_local_service_task(self, ctx):
        """创建本地服务任务"""
        if self.deployment_config.threading_strategy == ThreadingStrategy.SINGLE:
            return LocalServiceTask(self.service_factory, ctx, self.deployment_config)
        elif self.deployment_config.threading_strategy == ThreadingStrategy.MULTI:
            return MultiThreadLocalServiceTask(self.service_factory, ctx, self.deployment_config)
        elif self.deployment_config.threading_strategy == ThreadingStrategy.POOL:
            return ThreadPoolServiceTask(self.service_factory, ctx, self.deployment_config)
        # ... 其他策略
    
    def _create_remote_service_task(self, ctx):
        """创建远程服务任务"""
        ray_options = self._build_ray_options()
        
        if self.deployment_config.threading_strategy == ThreadingStrategy.SINGLE:
            ray_task = RayServiceTask.options(**ray_options).remote(
                self.service_factory, ctx, self.deployment_config
            )
        elif self.deployment_config.threading_strategy == ThreadingStrategy.MULTI:
            ray_task = MultiThreadRayServiceTask.options(**ray_options).remote(
                self.service_factory, ctx, self.deployment_config
            )
        # ... 其他策略
        
        return ActorWrapper(ray_task)
    
    def _build_ray_options(self) -> Dict[str, Any]:
        """构建Ray部署选项"""
        options = {}
        
        # 资源配置
        if self.deployment_config.cpu_cores:
            options['num_cpus'] = self.deployment_config.cpu_cores
        if self.deployment_config.memory_mb:
            options['memory'] = self.deployment_config.memory_mb * 1024 * 1024
        if self.deployment_config.gpu_count:
            options['num_gpus'] = self.deployment_config.gpu_count
        
        # 节点选择
        if self.deployment_config.target == DeploymentTarget.REMOTE_SPECIFIC:
            if self.deployment_config.target_nodes:
                options['resources'] = {f"node:{node}": 1 for node in self.deployment_config.target_nodes}
        elif self.deployment_config.node_selector:
            options['resources'] = self.deployment_config.node_selector
        
        return options
```

### 2. 多线程服务任务实现

#### `MultiThreadLocalServiceTask`

```python
class MultiThreadLocalServiceTask(BaseServiceTask):
    """多线程本地服务任务"""
    
    def __init__(self, service_factory, ctx, deployment_config):
        super().__init__(service_factory, ctx)
        self.deployment_config = deployment_config
        self.worker_threads = []
        self.request_queue = queue.Queue(maxsize=deployment_config.queue_size)
        self.thread_pool = None
        
    def _start_service_instance(self):
        """启动多线程服务实例"""
        thread_count = self.deployment_config.thread_count
        
        if self.deployment_config.threading_strategy == ThreadingStrategy.MULTI:
            # 创建固定数量的工作线程
            for i in range(thread_count):
                thread = threading.Thread(
                    target=self._worker_thread_loop,
                    name=f"{self.service_name}_worker_{i}",
                    daemon=True
                )
                thread.start()
                self.worker_threads.append(thread)
                
        elif self.deployment_config.threading_strategy == ThreadingStrategy.POOL:
            # 使用线程池
            pool_size = self.deployment_config.thread_pool_size or thread_count
            self.thread_pool = ThreadPoolExecutor(
                max_workers=pool_size,
                thread_name_prefix=f"{self.service_name}_pool"
            )
        
        super()._start_service_instance()
        self.logger.info(f"Started {thread_count}-thread service instance: {self.service_name}")
    
    def _worker_thread_loop(self):
        """工作线程循环"""
        thread_name = threading.current_thread().name
        self.logger.debug(f"Worker thread {thread_name} started")
        
        while self.is_running:
            try:
                # 从队列获取请求（超时1秒）
                request_data = self.request_queue.get(timeout=1.0)
                self.logger.debug(f"Thread {thread_name} processing request {request_data.get('request_id')}")
                
                # 处理请求
                self._handle_service_request(request_data)
                
            except queue.Empty:
                # 超时，继续循环
                continue
            except Exception as e:
                self.logger.error(f"Error in worker thread {thread_name}: {e}")
    
    def handle_request(self, request_data: Dict[str, Any]):
        """处理服务请求（重写基类方法）"""
        try:
            if self.deployment_config.threading_strategy == ThreadingStrategy.POOL:
                # 提交到线程池
                future = self.thread_pool.submit(self._handle_service_request, request_data)
                # 可以选择是否等待结果
                if self.deployment_config.batch_size and self.deployment_config.batch_size > 1:
                    # 异步处理，不等待
                    pass
                else:
                    # 同步等待
                    future.result(timeout=self.deployment_config.timeout)
            else:
                # 放入工作队列
                self.request_queue.put(request_data, timeout=5.0)
                
        except Exception as e:
            self.logger.error(f"Failed to handle request: {e}")
            # 发送错误响应
            self._send_error_response(request_data, str(e))
```

#### `AsyncServiceTask`

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncServiceTask(BaseServiceTask):
    """异步协程服务任务"""
    
    def __init__(self, service_factory, ctx, deployment_config):
        super().__init__(service_factory, ctx)
        self.deployment_config = deployment_config
        self.event_loop = None
        self.loop_thread = None
        self.request_queue = asyncio.Queue(maxsize=deployment_config.queue_size)
        
    def _start_service_instance(self):
        """启动异步服务实例"""
        # 在单独线程中运行事件循环
        self.loop_thread = threading.Thread(
            target=self._run_async_loop,
            name=f"{self.service_name}_async_loop",
            daemon=True
        )
        self.loop_thread.start()
        
        # 等待事件循环启动
        time.sleep(0.1)
        
        super()._start_service_instance()
        self.logger.info(f"Started async service instance: {self.service_name}")
    
    def _run_async_loop(self):
        """运行异步事件循环"""
        self.event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.event_loop)
        
        try:
            # 创建多个协程worker
            worker_count = self.deployment_config.thread_count
            workers = [
                self.event_loop.create_task(self._async_worker(f"worker_{i}"))
                for i in range(worker_count)
            ]
            
            self.event_loop.run_until_complete(asyncio.gather(*workers))
            
        except Exception as e:
            self.logger.error(f"Error in async event loop: {e}")
        finally:
            self.event_loop.close()
    
    async def _async_worker(self, worker_name: str):
        """异步工作协程"""
        self.logger.debug(f"Async worker {worker_name} started")
        
        while self.is_running:
            try:
                # 从异步队列获取请求
                request_data = await asyncio.wait_for(
                    self.request_queue.get(), 
                    timeout=1.0
                )
                
                self.logger.debug(f"Worker {worker_name} processing request {request_data.get('request_id')}")
                
                # 异步处理请求
                await self._handle_service_request_async(request_data)
                
            except asyncio.TimeoutError:
                # 超时，继续循环
                continue
            except Exception as e:
                self.logger.error(f"Error in async worker {worker_name}: {e}")
    
    async def _handle_service_request_async(self, request_data: Dict[str, Any]):
        """异步处理服务请求"""
        try:
            # 如果服务方法是协程，直接await
            method_name = request_data.get('method_name')
            if hasattr(self.service_instance, method_name):
                method = getattr(self.service_instance, method_name)
                if asyncio.iscoroutinefunction(method):
                    result = await method(*request_data.get('args', ()), **request_data.get('kwargs', {}))
                else:
                    # 在线程池中运行同步方法
                    executor = ThreadPoolExecutor(max_workers=1)
                    result = await self.event_loop.run_in_executor(
                        executor, 
                        method, 
                        *request_data.get('args', ()), 
                        **request_data.get('kwargs', {})
                    )
                
                # 发送响应
                self._send_response_sync(request_data, result, None)
            else:
                raise AttributeError(f"Method {method_name} not found")
                
        except Exception as e:
            self.logger.error(f"Error in async request handling: {e}")
            self._send_response_sync(request_data, None, str(e))
    
    def handle_request(self, request_data: Dict[str, Any]):
        """处理服务请求（重写基类方法）"""
        if self.event_loop and not self.event_loop.is_closed():
            # 将请求放入异步队列
            asyncio.run_coroutine_threadsafe(
                self.request_queue.put(request_data), 
                self.event_loop
            )
        else:
            self.logger.error("Event loop not available for request handling")
```

### 3. 客户端API扩展

#### 环境注册API扩展

```python
# 当前API
env.register_service("kv_service", KVService, backend="memory")

# 新的配置化API
deployment_config = ServiceDeploymentConfig(
    target=DeploymentTarget.REMOTE_SPECIFIC,
    target_nodes=["node-gpu-01", "node-gpu-02"],
    threading_strategy=ThreadingStrategy.POOL,
    thread_count=4,
    thread_pool_size=8,
    cpu_cores=2.0,
    memory_mb=4096,
    replicas=2,
    load_balancing=True,
    queue_size=2000,
    timeout=60.0
)

env.register_service_with_config(
    "kv_service", 
    KVService, 
    deployment_config=deployment_config,
    backend="memory"
)

# 简化配置API
env.register_service_on_nodes(
    "vdb_service", 
    VDBService,
    nodes=["node-memory-01"],
    threads=6,
    memory_mb=8192
)

env.register_local_service_pool(
    "llm_service",
    LLMService,
    pool_size=3,
    max_threads=12,
    gpu_count=1
)
```

#### 配置文件支持

```yaml
# service_deployment.yaml
services:
  kv_service:
    deployment:
      target: remote_specific
      target_nodes: ["node-storage-01", "node-storage-02"]
      threading_strategy: multi
      thread_count: 4
      replicas: 2
      load_balancing: true
    resources:
      cpu_cores: 2.0
      memory_mb: 4096
    performance:
      queue_size: 2000
      timeout: 60.0
      batch_size: 10

  llm_service:
    deployment:
      target: remote_any
      threading_strategy: pool
      thread_pool_size: 8
      replicas: 1
    resources:
      cpu_cores: 8.0
      memory_mb: 16384
      gpu_count: 1
    performance:
      queue_size: 100
      timeout: 120.0

  memory_service:
    deployment:
      target: local
      threading_strategy: async
      thread_count: 6
    resources:
      cpu_cores: 4.0
      memory_mb: 8192
```

```python
# 从配置文件加载
env.load_service_deployment_config("service_deployment.yaml")
```

### 4. 监控与管理

#### 服务状态监控

```python
class ServiceMetrics:
    """服务指标收集"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.request_count = 0
        self.error_count = 0
        self.active_threads = 0
        self.queue_size = 0
        self.avg_response_time = 0.0
        self.cpu_usage = 0.0
        self.memory_usage = 0
        
class ServiceMonitor:
    """服务监控器"""
    
    def __init__(self, deployment_config: ServiceDeploymentConfig):
        self.deployment_config = deployment_config
        self.metrics = ServiceMetrics(deployment_config.service_name)
        self.health_check_thread = None
        
    def start_monitoring(self):
        """启动监控"""
        if self.deployment_config.enable_metrics:
            self.health_check_thread = threading.Thread(
                target=self._health_check_loop,
                daemon=True
            )
            self.health_check_thread.start()
    
    def _health_check_loop(self):
        """健康检查循环"""
        interval = self.deployment_config.health_check_interval
        
        while True:
            try:
                self._collect_metrics()
                self._check_health()
                time.sleep(interval)
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "service_name": self.metrics.service_name,
            "deployment_config": self.deployment_config,
            "metrics": self.metrics,
            "health": self._get_health_status()
        }
```

## 🎯 实现计划

### Phase 1: 核心配置框架 (2-3周)
- [ ] 实现`ServiceDeploymentConfig`配置类
- [ ] 扩展`ServiceTaskFactory`以支持配置
- [ ] 更新`BaseEnvironment`注册API
- [ ] 基础单元测试

### Phase 2: 多线程任务实现 (3-4周)
- [ ] 实现`MultiThreadLocalServiceTask`
- [ ] 实现`ThreadPoolServiceTask`
- [ ] 实现`AsyncServiceTask`
- [ ] Ray远程多线程支持
- [ ] 性能测试

### Phase 3: 高级部署功能 (2-3周)
- [ ] 节点选择和资源配置
- [ ] 负载均衡和故障转移
- [ ] 动态扩缩容支持
- [ ] 集成测试

### Phase 4: 监控与管理 (2周)
- [ ] 服务指标收集
- [ ] 健康检查机制
- [ ] 管理API接口
- [ ] 可视化dashboard

### Phase 5: 文档与示例 (1周)
- [ ] 配置文档编写
- [ ] API使用示例
- [ ] 最佳实践指南
- [ ] 迁移指南

## 📊 预期收益

1. **灵活部署**：客户可根据需求选择最佳部署策略
2. **性能优化**：多线程配置提升服务处理能力
3. **资源利用**：精确的资源配置提高集群利用率
4. **运维友好**：统一的监控和管理接口
5. **向前兼容**：现有代码无需修改即可使用

## 🧪 测试策略

1. **单元测试**：各配置类和工厂类功能测试
2. **集成测试**：多线程服务任务端到端测试
3. **性能测试**：不同配置下的性能基准测试
4. **稳定性测试**：长期运行和故障恢复测试
5. **兼容性测试**：现有服务的向前兼容测试

## 🔗 相关Issue

- #SERVICE_TO_SERVICE_COMMUNICATION_ISSUE - 服务间通信功能
- #CALL_SERVICE_REFACTORING_ISSUE - 服务调用重构

---

通过这个特性，SAGE将为客户提供企业级的服务部署灵活性，满足从开发测试到生产环境的各种部署需求。
