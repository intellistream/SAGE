# Finetune GPU 资源管理策略

## 概述

本文档说明 SAGE Studio 微调功能的 GPU 资源管理策略，以及 Studio 队列机制与 SageLLM Control Plane 的职责边界。

---

## 当前实现：Studio 本地队列

### 设计原则

**单 GPU 任务串行化**：
- 一次只运行一个微调任务
- 新任务自动进入队列（`QUEUED` 状态）
- 任务完成后自动启动下一个排队任务

### 实现机制

#### 1. 任务状态流转

```
用户提交任务
    ↓
PENDING（等待开始）
    ↓
检查 GPU 占用
    ↓
    ├─ 有任务运行 → QUEUED（排队等待）
    │                    ↓
    │            前一任务完成后自动启动
    │                    ↓
    └─ GPU 空闲 ─────→ PREPARING（准备环境）
                         ↓
                    TRAINING（训练中）
                         ↓
                    ├─ COMPLETED（成功）
                    └─ FAILED（失败）
```

#### 2. 队列管理代码

**启动任务时检查队列**：
```python
# finetune_manager.py
def start_training(self, task_id: str) -> bool:
    task = self.tasks.get(task_id)
    if not task:
        return False

    # 如果已有任务在运行，则加入队列
    if self.active_task_id:
        self.update_task_status(task_id, FinetuneStatus.QUEUED)
        self.add_task_log(
            task_id,
            f"任务已加入队列，等待 GPU 资源释放（当前运行: {self.active_task_id}）"
        )
        return True  # 返回 True 表示成功加入队列

    # GPU 空闲，立即启动
    # ... 启动训练进程
```

**任务完成时启动下一个**：
```python
def _start_next_queued_task(self):
    """启动下一个排队任务"""
    for task in sorted(self.tasks.values(), key=lambda t: t.created_at):
        if task.status == FinetuneStatus.QUEUED:
            print(f"[FinetuneManager] 启动排队任务: {task.task_id}")
            task.status = FinetuneStatus.PENDING
            self.start_training(task.task_id)
            break

def update_task_status(self, task_id: str, status: FinetuneStatus, ...):
    # ...
    if status in (FinetuneStatus.COMPLETED, FinetuneStatus.FAILED):
        if self.active_task_id == task_id:
            self.active_task_id = None
            self._start_next_queued_task()  # 自动启动下一个
```

#### 3. GPU 信息检测

**API 端点**：`GET /api/system/gpu-info`

**返回信息**：
```json
{
  "available": true,
  "count": 1,
  "devices": [
    {
      "id": 0,
      "name": "NVIDIA GeForce RTX 3060",
      "memory_gb": 12.0
    }
  ],
  "recommendation": "NVIDIA GeForce RTX 3060 (12.0GB): 推荐 Qwen 2.5 Coder 1.5B（最佳平衡）或 0.5B（最快训练）"
}
```

**前端动态显示**：
```tsx
// FinetunePanel.tsx
const [gpuInfo, setGpuInfo] = useState(null)

useEffect(() => {
    loadGpuInfo()
}, [])

const loadGpuInfo = async () => {
    const response = await fetch('http://localhost:8080/api/system/gpu-info')
    const data = await response.json()
    setGpuInfo(data)
}

// 页面显示
💡 {gpuInfo ? gpuInfo.recommendation : '正在检测 GPU...'}
```

---

## Studio 队列 vs SageLLM Control Plane

### 职责边界

| 组件 | 职责范围 | 当前实现 |
|------|---------|---------|
| **Studio 队列** | 管理 Studio 内的微调任务排队<br>防止单用户多任务挤压 GPU | ✅ 已实现 |
| **SageLLM Control Plane** | 跨用户/跨服务的 GPU 资源调度<br>生产环境的资源隔离与配额管理 | ❌ 未集成 |

### 为什么当前使用 Studio 队列？

#### 1. **使用场景差异**

**Studio 场景**（当前）：
- 单用户本地开发环境
- GPU 资源由 Studio 独占
- 任务量少（一般同时 1-3 个）
- 需要快速响应和简单逻辑

**Control Plane 场景**（未来）：
- 多用户生产环境
- GPU 资源池需要跨服务共享
- 大规模任务调度
- 需要配额、优先级、抢占等高级功能

#### 2. **架构复杂度权衡**

**Studio 队列**（轻量）：
```
User → Studio UI → FinetuneManager (本地队列) → GPU
```

**Control Plane 集成**（重量）：
```
User → Studio UI → API Gateway → Control Plane → Resource Manager
                                       ↓
                                 Task Scheduler
                                       ↓
                                 GPU Pool Manager
                                       ↓
                                   Worker Nodes
```

#### 3. **开发优先级**

**当前阶段**：
- ✅ 快速验证微调功能
- ✅ 支持单用户开发场景
- ✅ 最小化依赖和复杂度

**未来集成**：
- ⏳ 生产环境部署需求明确后
- ⏳ 多用户场景真正出现后
- ⏳ SageLLM Control Plane 成熟后

---

## 何时需要集成 SageLLM Control Plane？

### 触发条件

满足以下**任一条件**时，应考虑集成 Control Plane：

1. **多用户场景**：
   - Studio 部署为多用户服务器模式
   - 需要跨用户的资源配额管理

2. **GPU 资源竞争**：
   - GPU 资源被多个服务共享（如 vLLM 推理 + 微调）
   - 需要动态资源分配和抢占机制

3. **大规模任务调度**：
   - 单用户同时提交 10+ 个任务
   - 需要优先级队列和复杂调度策略

4. **生产环境需求**：
   - 需要任务持久化到外部存储（如 Redis）
   - 需要监控、告警、审计等企业级功能

### 集成方案

**Phase 1：轻量集成**
```python
# finetune_manager.py
class FinetuneManager:
    def __init__(self):
        # 检测是否启用 Control Plane
        if os.getenv("SAGE_STUDIO_USE_CONTROL_PLANE") == "true":
            self.scheduler = SageLLMScheduler()
        else:
            self.scheduler = LocalQueueScheduler()  # 当前实现

    def start_training(self, task_id: str):
        return self.scheduler.submit_task(task_id)
```

**Phase 2：完全托管**
- 所有微调任务通过 Control Plane API 提交
- Studio 只负责 UI 和任务监控
- GPU 资源由 Control Plane 统一管理

---

## GPU 资源分配策略

### 当前策略（Studio 本地队列）

**单任务独占 GPU**：
```python
# api.py - use-as-backend 端点
import torch

num_gpus = torch.cuda.device_count() if torch.cuda.is_available() else 0
config = {"trust_remote_code": True, "max_model_len": 2048}

if num_gpus > 0:
    config["gpu_memory_utilization"] = 0.8  # 单卡占用 80%
    if num_gpus > 1:
        config["tensor_parallel_size"] = num_gpus  # 多卡并行
```

**为什么是 0.8？**
- 预留 20% 显存给系统和其他进程
- 防止 OOM（Out of Memory）
- 支持模型加载时的临时显存峰值

### 未来策略（Control Plane 集成）

**GPU 分片（MIG）**：
- NVIDIA A100/H100 支持 MIG（Multi-Instance GPU）
- 单卡可划分为多个独立实例
- 支持多任务并行

**动态显存分配**：
- 根据模型大小动态调整 `gpu_memory_utilization`
- 小模型（0.5B）：0.3（30% 显存）
- 中等模型（1.5B-3B）：0.5-0.6
- 大模型（7B+）：0.8-0.9

---

## 常见问题

### Q1: 为什么不直接使用 Kubernetes Job Queue？

**A**: 当前 Studio 是单机应用，不依赖 Kubernetes。未来生产部署可以选择：
- Option 1: Studio 队列 + K8s Job（每个训练任务单独提交到 K8s）
- Option 2: 完全托管给 SageLLM Control Plane（Control Plane 内部使用 K8s）

### Q2: 多个任务同时启动会发生什么？

**A**: 只有第一个任务会实际启动，其余任务进入 `QUEUED` 状态：

```
Task 1: PENDING → PREPARING → TRAINING
Task 2: PENDING → QUEUED（等待 Task 1）
Task 3: PENDING → QUEUED（等待 Task 1, 2）
```

任务完成顺序：Task 1 完成 → Task 2 启动 → Task 2 完成 → Task 3 启动

### Q3: 如果 GPU 被其他程序占用怎么办？

**A**: 当前实现不检测外部 GPU 占用。解决方案：

**短期**（手动）：
- 用户手动检查 `nvidia-smi`
- 确保 GPU 空闲后再提交任务

**中期**（检测）：
```python
def check_gpu_available():
    import torch
    try:
        torch.cuda.empty_cache()
        # 尝试分配小块显存测试
        test_tensor = torch.zeros(1).cuda()
        del test_tensor
        return True
    except RuntimeError:
        return False
```

**长期**（Control Plane）：
- Control Plane 统一管理所有 GPU 使用者
- 动态资源分配和抢占

### Q4: vLLM 推理服务和微调任务会冲突吗？

**A**: 会！当前架构下，两者会竞争 GPU 显存。

**临时方案**：
1. 微调任务启动前，提示用户停止 vLLM 服务
2. 或使用 CPU 推理模式（性能低）

**正式方案**（需要 Control Plane）：
- vLLM 和微调任务都向 Control Plane 申请资源
- Control Plane 根据优先级分配 GPU
- 支持动态卸载和重新加载模型

---

## 最佳实践

### 对于用户

1. **检查 GPU 状态**：
   ```bash
   nvidia-smi
   ```

2. **合理选择模型大小**：
   - 根据页面显示的 GPU 推荐配置选择模型
   - 不要超过显存限制

3. **避免同时运行多个重型任务**：
   - 微调任务会独占 GPU
   - 训练期间暂停推理服务可加快速度

### 对于开发者

1. **监控任务队列长度**：
   ```python
   queued_count = sum(1 for t in tasks if t.status == FinetuneStatus.QUEUED)
   if queued_count > 5:
       print("警告：队列任务过多")
   ```

2. **添加任务超时机制**：
   ```python
   MAX_TRAINING_TIME = 3600 * 6  # 6 小时

   def _monitor_process(self, task_id):
       start_time = time.time()
       while self._is_process_running(task.process_id):
           if time.time() - start_time > MAX_TRAINING_TIME:
               # 强制终止
               os.kill(task.process_id, signal.SIGTERM)
               break
   ```

3. **准备 Control Plane 集成接口**：
   - 保持 `FinetuneManager` 的接口稳定
   - 未来只需替换内部实现

---

## 总结

### 当前架构（Studio 本地队列）

**优势**：
- ✅ 简单高效
- ✅ 适合单用户开发场景
- ✅ 无外部依赖
- ✅ 快速迭代验证

**限制**：
- ❌ 不支持多用户
- ❌ 不支持跨服务 GPU 共享
- ❌ 缺少高级调度策略

### 未来演进（Control Plane 集成）

**时机**：
- 生产环境多用户部署
- GPU 资源需要跨服务共享
- 需要企业级调度和监控

**迁移成本**：
- 低（接口已预留）
- 只需替换调度器实现
- 前端 UI 无需变化

**建议**：
- 当前保持 Studio 队列实现
- 密切关注 SageLLM Control Plane 进展
- 在生产需求明确时再集成

---

## 参考资料

- [finetune-process-persistence.md](./finetune-process-persistence.md) - 进程持久化机制
- [finetune-backend-integration.md](./finetune-backend-integration.md) - vLLM 集成说明
- SageLLM Control Plane 文档（待补充）
