# Issue: PythonQueueDescriptor.clone() 导致服务响应队列通信失败

## 问题描述

在使用 `PipelineService` 包装的 Pipeline 内部调用其他服务时，会间歇性地出现服务调用超时问题。具体表现为：
- 服务端成功处理请求并发送响应
- 客户端等待响应超时（默认10秒）
- 错误信息：`TimeoutError: Service call timeout after 10.0s: short_term_memory.retrieve`

**关键特征：** 这是一个**间歇性问题**（竞态条件），相同代码有时成功，有时失败。

## 复现场景

### 架构设置
```
主 Pipeline:
  PipelineCaller → 调用 memory_test_service

服务 Pipeline (memory_test_service):
  PipelineServiceSource → MemoryRetrieval → ...
  
MemoryRetrieval 内部:
  调用 short_term_memory.retrieve() 服务
```

### 复现步骤
1. 创建一个作为服务运行的 Pipeline（通过 PipelineService + PipelineBridge）
2. 在该 Pipeline 的算子中调用另一个服务（如 `self.call_service("short_term_memory", method="retrieve")`）
3. 多次运行，观察到间歇性超时

## 根本原因分析

### 问题定位

`PythonQueueDescriptor.clone()` 方法的设计缺陷导致服务端和客户端使用不同的队列实例。

**源码位置：** `packages/sage-platform/src/sage/platform/queue/python_queue_descriptor.py`

```python
def clone(self, new_queue_id: Optional[str] = None) -> "PythonQueueDescriptor":
    """克隆描述符（不包含队列实例）"""
    return PythonQueueDescriptor(
        maxsize=0,
        use_multiprocessing=self.use_multiprocessing,
        queue_id=new_queue_id,
    )

@property
def queue_instance(self) -> Any:
    """获取队列实例，如果未初始化则创建"""
    if not self._initialized:
        self._queue_instance = Queue(maxsize=self.maxsize)  # 每次创建新Queue!
        self._initialized = True
    return self._queue_instance
```

### 问题机制

1. **服务端**通过原始 `QueueDescriptor` 访问 `queue_instance` → 创建 `Queue A`
2. **客户端**在 `service_caller.py` 中调用 `self.context.response_qd.clone()` → 创建新的描述符
3. 客户端访问 clone 后的 `queue_instance` → 创建 `Queue B`
4. **结果**：服务端发送响应到 `Queue A`，客户端在 `Queue B` 等待 → 永远收不到

### 相关代码调用链

**客户端（service_caller.py:121-128）：**
```python
def _get_response_queue(self):
    """从TaskContext获取响应队列"""
    if self._response_queue is None:
        if self.context:
            if hasattr(self.context, "response_qd") and self.context.response_qd:
                self._response_queue = self.context.response_qd.clone()  # ← 问题点
                self.logger.debug(f"Using response queue: {self._response_queue_name}")
```

**响应监听线程循环调用：**
```python
def _response_listener(self):
    while not self._shutdown:
        response_queue = self._get_response_queue()  # 每次循环都调用
        response_data = response_queue.get(timeout=1.0)
```

## 日志证据

### 失败案例（session_20251118_031016）

**服务端日志（service_short_term_memory_info.log）：**
```
2025-11-18 03:10:16 | [SERVICE_TASK] Received request #3: retrieve (request_id: 95934d57...)
2025-11-18 03:10:16 | [SERVICE_TASK] Service method retrieve succeeded
2025-11-18 03:10:16 | [SERVICE_TASK] Response sent successfully to queue service_response_MemoryRetrieval_0
```

**客户端日志（MemoryRetrieval_0_debug.log）：**
```
2025-11-18 03:10:16 | Using response queue: service_response_MemoryRetrieval_0
2025-11-18 03:10:16 | [SERVICE_CALL] Waiting for response (timeout: 10.0s)
2025-11-18 03:10:17 | Response listener: Getting response queue  # 持续轮询
2025-11-18 03:10:18 | Response listener: Getting response queue
...
2025-11-18 03:10:26 | [SERVICE_CALL] TIMEOUT after 10.000s  # 超时！
```

### 成功案例（session_20251118_020625 / 033616）

**客户端日志：**
```
2025-11-18 02:06:25 | [SERVICE_CALL] Response received after 0.001s
2025-11-18 02:06:25 | [SERVICE_CALL] SUCCESS: short_term_memory.retrieve completed in 0.001s
```

**对比统计：**
- 失败运行：只成功 2 次 retrieve 后超时
- 成功运行：完成 7 次 retrieve，响应时间 0.001-0.003s

## 为什么是间歇性问题？

这是典型的**竞态条件**（Race Condition）：

### 成功场景（运气好）
```
时间线：
T1: 客户端响应监听线程启动
T2: 客户端调用 clone() → 创建新描述符（未初始化）
T3: 服务端接收请求，访问原始描述符.queue_instance → 创建 Queue
T4: ??? (可能存在某种内部队列共享机制，或队列名称查找)
T5: 客户端和服务端恰好使用了同一个 Queue 实例
T6: ✅ 通信成功
```

### 失败场景（运气差）
```
时间线：
T1: 服务端先接收请求
T2: 服务端访问原始描述符.queue_instance → 创建 Queue A
T3: 客户端调用 clone()，访问 queue_instance → 创建 Queue B
T4: 服务端发送响应到 Queue A
T5: 客户端在 Queue B 等待
T6: ❌ 10秒后超时
```

## 影响范围

这个问题影响所有在 **PipelineService 内部的算子调用其他服务** 的场景：

- ✅ 主 Pipeline 直接调用服务 - **正常**
- ✅ 普通算子调用服务 - **正常**
- ❌ PipelineService 包装的 Pipeline 内部算子调用服务 - **间歇性失败**

## 建议的修复方案

### 方案 1：clone() 共享队列实例（推荐）

修改 `PythonQueueDescriptor.clone()` 方法，让克隆后的描述符共享原始队列实例：

```python
def clone(self, new_queue_id: Optional[str] = None) -> "PythonQueueDescriptor":
    """克隆描述符，共享队列实例"""
    cloned = PythonQueueDescriptor(
        maxsize=self.maxsize,  # 保持原始 maxsize
        use_multiprocessing=self.use_multiprocessing,
        queue_id=new_queue_id or self.queue_id,
    )
    
    # 如果原始描述符已初始化，共享队列实例
    if self._initialized:
        cloned._queue_instance = self._queue_instance
        cloned._initialized = True
    
    return cloned
```

### 方案 2：缓存响应队列（备选）

在 `ServiceManager.__init__()` 中立即初始化并缓存响应队列，而不是延迟到第一次调用：

```python
def __init__(self, context, logger=None):
    # ... existing code ...
    
    # 立即初始化响应队列并缓存队列实例
    if self.context is not None:
        if hasattr(self.context, "response_qd") and self.context.response_qd:
            self._response_queue = self.context.response_qd.clone()
            # 强制初始化队列实例
            _ = self._response_queue.queue_instance
```

### 方案 3：全局队列注册表（长期方案）

实现基于 queue_id 的全局队列注册表，确保相同 queue_id 返回相同队列实例。

## 临时绕过方案

对于受影响的代码，可以临时使用直接实例传递而不是服务调用：

```python
# 临时方案：直接传递服务实例
class MemoryRetrieval(MapFunction):
    def __init__(self, memory_service):
        super().__init__()
        self.memory_service = memory_service
    
    def execute(self, data):
        # 直接调用实例方法，避免服务调用
        memory_data = self.memory_service.retrieve()
```

## 测试建议

1. 创建单元测试验证 `clone()` 后的队列实例共享
2. 创建集成测试模拟 PipelineService 内部调用服务的场景
3. 压力测试验证竞态条件是否修复

## 环境信息

- 发现时间：2025-11-18
- 分支：refactor/memory-pipeline-3-tier-architecture
- 相关 PR：#1110
- Python 版本：3.11+
- 复现率：约 30-50%（间歇性）

## 相关文件

- `packages/sage-platform/src/sage/platform/queue/python_queue_descriptor.py` - 问题根源
- `packages/sage-kernel/src/sage/kernel/runtime/service/service_caller.py` - 使用 clone() 的地方
- `packages/sage-kernel/src/sage/kernel/api/service/pipeline_service/pipeline_service.py` - PipelineService 实现

---

**优先级：高** - 影响服务通信可靠性，虽然是间歇性问题，但会导致生产环境不稳定。
