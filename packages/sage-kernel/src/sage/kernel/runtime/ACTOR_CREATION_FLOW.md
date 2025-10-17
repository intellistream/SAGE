## Dispatcher 中 Actor 创建的完整流程

### 概览

Dispatcher 通过调用链 `Dispatcher → Scheduler → PlacementExecutor → TaskFactory → RayTask/LocalTask` 来创建 Actor。

---

## 完整调用链

```
用户代码
  ↓
Environment.submit()
  ↓
JobManager.submit()
  ↓
Dispatcher.submit()                    ← 【入口】
  ↓ 遍历图节点
Scheduler.schedule_task()              ← 【调度决策】
  ↓
PlacementExecutor.place_task()         ← 【放置执行】
  ↓
TaskFactory.create_task()              ← 【任务创建】
  ↓
RayTask.options().remote()             ← 【Ray Actor 创建】
  ↓
ActorWrapper(ray_actor)                ← 【封装】
  ↓
返回给 Dispatcher → self.tasks[name] = task
```

---

## 详细流程分析

### 1. Dispatcher.submit() - 入口

**位置**: `packages/sage-kernel/src/sage/kernel/runtime/dispatcher.py`

```python
class Dispatcher:
    def __init__(self, graph, env):
        # 初始化调度器
        self.scheduler = env.scheduler or FIFOScheduler(platform=env.platform)
        self.tasks = {}  # 存储所有任务实例
        self.remote = env.platform == "remote"
    
    def submit(self):
        """编译图结构，创建节点并建立连接"""
        self.logger.info(f"Compiling Job for graph: {self.name}")
        
        # 第一步：调度所有服务任务
        for service_node_name, service_node in self.graph.service_nodes.items():
            service_task = self.scheduler.schedule_service(
                service_node=service_node, 
                runtime_ctx=service_ctx
            )
            self.services[service_name] = service_task
        
        # 第二步：调度所有计算任务节点
        for node_name, graph_node in self.graph.nodes.items():
            # === 关键调用：委托给 Scheduler ===
            task = self.scheduler.schedule_task(
                task_node=graph_node,      # TaskNode 对象
                runtime_ctx=graph_node.ctx # TaskContext 对象
            )
            
            # === Dispatcher 保存任务引用 ===
            self.tasks[node_name] = task  # task 是 LocalTask 或 ActorWrapper
            
            self.logger.debug(
                f"Scheduled task '{node_name}' of type '{task.__class__.__name__}'"
            )
        
        # 第三步：启动所有任务
        self.start()
```

**职责**：
- 遍历执行图中的所有节点
- 调用 Scheduler 创建任务
- 保存任务引用到 `self.tasks`
- **不直接创建 Actor**，完全委托给 Scheduler

---

### 2. Scheduler.schedule_task() - 调度决策

**位置**: `packages/sage-kernel/src/sage/kernel/scheduler/impl/simple_scheduler.py`

```python
class FIFOScheduler(BaseScheduler):
    def __init__(self, platform="local", placement_executor=None):
        super().__init__(placement_executor)
        # placement_executor 在父类中初始化
        # 如果为 None，会创建默认的 PlacementExecutor
    
    def schedule_task(self, task_node, runtime_ctx=None):
        """FIFO 调度：直接按顺序调度"""
        start_time = time.time()
        
        # === 调度策略 ===
        # FIFO: 立即调度，不等待
        # LoadAware: 检查负载，等待资源
        # Priority: 重新排序
        
        # === 节点选择（当前缺失，未来实现）===
        # target_node = self._select_node(task_node)
        
        # === 委托给 PlacementExecutor 执行放置 ===
        task = self.placement_executor.place_task(
            task_node, 
            runtime_ctx
            # target_node=target_node  # 未来传递
        )
        
        # 记录调度指标
        self.scheduled_count += 1
        self.total_latency += time.time() - start_time
        
        return task  # 返回 LocalTask 或 ActorWrapper
```

**职责**：
- 实现调度策略（何时调度）
- （未来）选择目标节点（放到哪里）
- 委托 PlacementExecutor 执行物理放置
- **不直接创建 Actor**

---

### 3. PlacementExecutor.place_task() - 放置执行

**位置**: `packages/sage-kernel/src/sage/kernel/scheduler/placement.py`

```python
class PlacementExecutor:
    def __init__(self):
        self.placed_tasks = []
        self.placement_stats = {
            "total_tasks": 0,
            "local_tasks": 0,
            "remote_tasks": 0,
        }
    
    def place_task(self, task_node, runtime_ctx=None, target_node=None):
        """将任务放置到物理节点"""
        
        # 1. 确定运行时上下文
        ctx = runtime_ctx if runtime_ctx is not None else task_node.ctx
        
        # === 2. 委托给 TaskFactory 创建任务 ===
        # 这是关键步骤：实际创建 LocalTask 或 RayTask
        task = task_node.task_factory.create_task(
            name=task_node.name, 
            runtime_context=ctx
        )
        
        # 3. 记录统计
        is_remote = task_node.task_factory.remote
        self.placement_stats["total_tasks"] += 1
        if is_remote:
            self.placement_stats["remote_tasks"] += 1
        else:
            self.placement_stats["local_tasks"] += 1
        
        self.placed_tasks.append({
            "task_name": task_node.name,
            "remote": is_remote,
            "target_node": target_node,
        })
        
        return task  # 返回 LocalTask 或 ActorWrapper
```

**职责**：
- 确定运行时上下文
- 调用 TaskFactory 创建任务实例
- 记录放置统计
- （未来）构建 Ray Actor 选项，指定节点和资源
- **委托 TaskFactory 创建 Actor**

---

### 4. TaskFactory.create_task() - 任务创建

**位置**: `packages/sage-kernel/src/sage/kernel/runtime/factory/task_factory.py`

```python
class TaskFactory:
    def __init__(self, transformation):
        self.basename = transformation.basename
        self.operator_factory = transformation.operator_factory
        self.remote = transformation.remote  # 关键属性！
        # remote=True: 创建 RayTask
        # remote=False: 创建 LocalTask
    
    def create_task(self, name, runtime_context):
        """创建任务实例：LocalTask 或 RayTask"""
        
        if self.remote:
            # === 远程模式：创建 Ray Actor ===
            
            # 1. 调用 RayTask.options().remote() 创建 Ray Actor
            node = RayTask.options(
                lifetime="detached"  # Actor 生命周期：detached
            ).remote(
                runtime_context,           # 传递运行时上下文
                self.operator_factory      # 传递 operator 工厂
            )
            # node 是 ray.actor.ActorHandle
            
            # 2. 包装成 ActorWrapper
            node = ActorWrapper(node)
            # ActorWrapper 提供统一的调用接口
        else:
            # === 本地模式：创建本地任务 ===
            node = LocalTask(
                runtime_context, 
                self.operator_factory
            )
        
        return node
```

**职责**：
- 根据 `remote` 属性决定创建类型
- **实际创建 Ray Actor 或 LocalTask**
- 包装 Ray Actor 为 ActorWrapper

**关键点**：
- `self.remote` 来自 `transformation.remote`
- `RayTask.options().remote()` 是 **Ray 的 API**，创建分布式 Actor
- `ActorWrapper` 封装 Actor，提供统一接口

---

### 5. RayTask - Ray Actor 定义

**位置**: `packages/sage-kernel/src/sage/kernel/runtime/task/ray_task.py`

```python
import ray
from sage.kernel.runtime.task.base_task import BaseTask

@ray.remote  # ← Ray 装饰器，将类标记为 Actor
class RayTask(BaseTask):
    """
    基于 Ray Actor 的任务节点
    使用 Ray Queue 作为输入输出缓冲区
    """
    
    def __init__(self, runtime_context, operator_factory):
        # 调用父类初始化
        super().__init__(runtime_context, operator_factory)
        self.logger.info(f"Initialized RayTask: {self.ctx.name}")
    
    def put_packet(self, packet):
        """Ray Actor 方法：接收数据包"""
        self.input_buffer.put(packet, block=False)
        return True
    
    # 其他方法继承自 BaseTask
    # - start_running()
    # - stop()
    # - _run() - 主循环
```

**关键点**：
- `@ray.remote` 装饰器将类标记为 Ray Actor
- 继承 `BaseTask`，实现任务的通用逻辑
- 所有方法都可以远程调用

**Ray Actor 创建过程**：
```python
# 1. 定义 Actor 类
@ray.remote
class RayTask(BaseTask):
    pass

# 2. 创建 Actor 实例
actor_handle = RayTask.options(lifetime="detached").remote(ctx, factory)
#                ↑               ↑                    ↑
#            Actor类        设置选项               创建实例

# actor_handle 是 ray.actor.ActorHandle
# 这是一个引用，指向集群中某个节点上的 Actor 实例
```

---

### 6. ActorWrapper - 统一封装

**位置**: `packages/sage-kernel/src/sage/kernel/utils/ray/actor.py`

```python
class ActorWrapper:
    """
    万能包装器：统一本地对象和 Ray Actor 的接口
    """
    
    def __init__(self, obj):
        self._obj = obj  # 原始对象（LocalTask 或 ActorHandle）
        self._execution_mode = self._detect_execution_mode()
        # "ray_actor" 或 "local"
    
    def _detect_execution_mode(self):
        """检测执行模式"""
        if isinstance(self._obj, ray.actor.ActorHandle):
            return "ray_actor"
        return "local"
    
    def __getattr__(self, name):
        """透明代理属性访问"""
        original_attr = getattr(self._obj, name)
        
        if callable(original_attr):
            if self._execution_mode == "ray_actor":
                # Ray Actor 方法：同步调用包装器
                def ray_method_wrapper(*args, **kwargs):
                    future = original_attr.remote(*args, **kwargs)
                    result = ray.get(future)  # 等待结果
                    return result
                return ray_method_wrapper
            else:
                # 本地方法：直接返回
                return original_attr
        else:
            return original_attr
    
    def call_async(self, method_name, *args, **kwargs):
        """异步调用 Ray Actor 方法，返回 ObjectRef"""
        method = getattr(self._obj, method_name)
        return method.remote(*args, **kwargs)
    
    def kill_actor(self, no_restart=True):
        """终止 Ray Actor"""
        if self._execution_mode == "ray_actor":
            ray.kill(self._obj, no_restart=no_restart)
            return True
        return False
```

**职责**：
- 统一本地对象和 Ray Actor 的调用接口
- 自动处理同步/异步调用
- 提供 Actor 管理方法（kill、cleanup）

**使用示例**：
```python
# 对于 Ray Actor
wrapper = ActorWrapper(ray_actor_handle)
wrapper.start_running()  # 自动转换为 ray.get(actor.start_running.remote())

# 对于本地对象
wrapper = ActorWrapper(local_task)
wrapper.start_running()  # 直接调用 local_task.start_running()
```

---

## Ray Actor 创建的关键步骤

### Ray 内部流程

```python
# 用户代码
actor = RayTask.options(lifetime="detached").remote(ctx, factory)

# Ray 内部执行：
# 1. 选择一个 Worker 节点（根据负载均衡策略）
# 2. 在该节点上启动 Actor 进程
# 3. 调用 RayTask.__init__(ctx, factory)
# 4. 返回 ActorHandle（远程引用）
```

### Ray Actor 的选项

```python
RayTask.options(
    lifetime="detached",     # Actor 生命周期
    num_cpus=1,             # CPU 资源需求
    num_gpus=0,             # GPU 资源需求
    memory=1024**3,         # 内存需求（字节）
    scheduling_strategy=..., # 调度策略（节点亲和性等）
).remote(...)
```

**当前使用的选项**：
- `lifetime="detached"`: Actor 不会在创建者退出后自动销毁

**未来可扩展的选项**：
- `num_cpus`: 指定 CPU 需求
- `num_gpus`: 指定 GPU 需求
- `memory`: 指定内存需求
- `scheduling_strategy`: 指定节点亲和性

---

## 完整示例代码

### 从 Dispatcher 到 Actor 的完整流程

```python
# ============ 1. Dispatcher.submit() ============
class Dispatcher:
    def submit(self):
        for node_name, graph_node in self.graph.nodes.items():
            # Dispatcher 调用 Scheduler
            task = self.scheduler.schedule_task(
                task_node=graph_node,
                runtime_ctx=graph_node.ctx
            )
            self.tasks[node_name] = task

# ============ 2. Scheduler.schedule_task() ============
class FIFOScheduler:
    def schedule_task(self, task_node, runtime_ctx):
        # Scheduler 调用 PlacementExecutor
        task = self.placement_executor.place_task(
            task_node, 
            runtime_ctx
        )
        return task

# ============ 3. PlacementExecutor.place_task() ============
class PlacementExecutor:
    def place_task(self, task_node, runtime_ctx, target_node=None):
        ctx = runtime_ctx or task_node.ctx
        
        # PlacementExecutor 调用 TaskFactory
        task = task_node.task_factory.create_task(
            task_node.name, 
            ctx
        )
        return task

# ============ 4. TaskFactory.create_task() ============
class TaskFactory:
    def create_task(self, name, runtime_context):
        if self.remote:
            # === 创建 Ray Actor ===
            node = RayTask.options(lifetime="detached").remote(
                runtime_context,
                self.operator_factory
            )
            # node 是 ray.actor.ActorHandle
            
            # === 包装为 ActorWrapper ===
            node = ActorWrapper(node)
        else:
            # === 创建本地任务 ===
            node = LocalTask(runtime_context, self.operator_factory)
        
        return node

# ============ 5. Ray 内部处理 ============
# Ray 接收到 RayTask.remote() 调用后：
# 1. 选择一个 Worker 节点（默认负载均衡）
# 2. 在该节点上序列化参数（runtime_context, operator_factory）
# 3. 启动 Actor 进程
# 4. 调用 RayTask.__init__(runtime_context, operator_factory)
# 5. 返回 ActorHandle 给调用者

# ============ 6. Dispatcher 使用 Actor ============
class Dispatcher:
    def start(self):
        for task in self.tasks.values():
            # 对于 ActorWrapper 包装的 Ray Actor
            task.start_running()
            # ActorWrapper 自动转换为：
            # ray.get(actor_handle.start_running.remote())
```

---

## 数据流

```
┌──────────────────┐
│   Dispatcher     │
│  self.tasks = {} │
└────────┬─────────┘
         │ for each node
         ▼
┌──────────────────┐
│    Scheduler     │
│  调度策略决策      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ PlacementExecutor│
│  统计+记录        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   TaskFactory    │
│ self.remote=True │  ← 决定创建类型
└────────┬─────────┘
         │
         ├─ remote=True ─────────────┐
         │                           ▼
         │                   ┌──────────────────┐
         │                   │ RayTask.remote() │
         │                   │  创建 Ray Actor   │
         │                   └────────┬─────────┘
         │                            │
         │                            ▼
         │                   ┌──────────────────┐
         │                   │  ActorHandle     │
         │                   │  (远程引用)       │
         │                   └────────┬─────────┘
         │                            │
         │                            ▼
         │                   ┌──────────────────┐
         │                   │  ActorWrapper    │
         │                   │  (封装)          │
         │                   └────────┬─────────┘
         │                            │
         └─ remote=False ───┐         │
                            ▼         │
                   ┌──────────────────┐
                   │   LocalTask      │
                   │  (本地线程)       │
                   └────────┬─────────┘
                            │
                            ▼
         ┌──────────────────────────┐
         │  返回给 Dispatcher        │
         │  self.tasks[name] = task │
         └──────────────────────────┘
```

---

## 关键理解

### 1. Dispatcher 不直接创建 Actor
- Dispatcher 只负责**协调和管理**
- 实际创建由 `TaskFactory` 完成

### 2. Ray Actor 创建在 TaskFactory
```python
# 这一行代码创建了 Ray Actor
node = RayTask.options(lifetime="detached").remote(ctx, factory)
```

### 3. ActorWrapper 提供统一接口
- 封装 Ray Actor 和本地对象
- Dispatcher 不需要区分对待
- 调用方式完全一致

### 4. remote 属性控制创建类型
```python
# 在 Transformation 定义时设置
transformation = MapTransformation(
    operator_factory=MyOperator,
    remote=True  # ← 控制创建 RayTask 还是 LocalTask
)
```

### 5. 调用链的职责分离
- **Dispatcher**: 遍历节点、保存引用、启动任务
- **Scheduler**: 调度策略、节点选择
- **PlacementExecutor**: 执行放置、记录统计
- **TaskFactory**: 实际创建任务
- **ActorWrapper**: 统一接口

---

## 总结

**Actor 创建的核心代码**：
```python
# TaskFactory.create_task()
node = RayTask.options(lifetime="detached").remote(runtime_context, operator_factory)
node = ActorWrapper(node)
```

**完整调用链**：
```
Dispatcher → Scheduler → PlacementExecutor → TaskFactory → RayTask.remote() → ActorWrapper
```

**Dispatcher 的角色**：
- 不直接创建 Actor
- 通过调用 Scheduler 间接创建
- 保存任务引用（LocalTask 或 ActorWrapper）
- 管理任务生命周期（start、stop、cleanup）
