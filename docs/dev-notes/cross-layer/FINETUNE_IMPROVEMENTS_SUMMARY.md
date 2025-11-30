# GPU 检测和任务队列改进总结

**日期**：2025-11-22  
**改进范围**：GPU 信息动态显示 + 任务队列优化

---

## 问题背景

### 问题 1：显卡型号硬编码
**用户反馈**：
> "这里显卡型号是检测出的，还是硬编码的，看不出来。给个标记或者说明？"

**原问题**：
- 前端硬编码显示 "RTX 3060 推荐"
- 无法适配不同 GPU 环境
- 用户无法判断推荐是否适用于自己的硬件

### 问题 2：多任务 GPU 竞争
**用户反馈**：
> "如果有多个微调任务，那不就形成了多个任务挤压 GPU 的场景吗？这个是否应该由 sagellm 的 control plane 来搞定？"

**原问题**：
- 虽然有 `active_task_id` 限制，但多任务同时提交会静默失败
- 用户看不到排队状态
- 缺少自动队列处理机制

---

## 解决方案

### 1. GPU 信息动态检测和显示

#### 后端：添加 GPU 信息 API

**文件**：`packages/sage-studio/src/sage/studio/config/backend/api.py`

**新增端点**：
```python
@router.get("/api/system/gpu-info")
async def get_gpu_info():
    """Get GPU information for finetune recommendations"""
    import torch

    gpu_info = {
        "available": torch.cuda.is_available(),
        "count": torch.cuda.device_count(),
        "devices": [
            {
                "id": i,
                "name": torch.cuda.get_device_name(i),
                "memory_gb": round(
                    torch.cuda.get_device_properties(i).total_memory / (1024**3), 1
                )
            }
            for i in range(torch.cuda.device_count())
        ],
        "recommendation": "..."  # 根据显存动态生成
    }
    return gpu_info
```

**返回示例**：
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

**推荐策略**：
- `≥ 24GB`: Qwen 2.5 Coder 7B 或 3B
- `≥ 12GB`: Qwen 2.5 Coder 3B 或 1.5B
- `≥ 8GB`: Qwen 2.5 Coder 1.5B 或 0.5B
- `< 8GB`: Qwen 2.5 Coder 0.5B

#### 前端：动态显示 GPU 信息

**文件**：`packages/sage-studio/src/sage/studio/frontend/src/components/FinetunePanel.tsx`

**改进前**（硬编码）：
```tsx
💡 <Text strong>RTX 3060 推荐</Text>: Qwen 2.5 Coder 1.5B（最佳平衡）或 0.5B（最快训练）
```

**改进后**（动态）：
```tsx
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
💡 <Text strong>{gpuInfo ? gpuInfo.recommendation : '正在检测 GPU...'}</Text>
```

**效果**：
- ✅ 自动检测 GPU 型号和显存
- ✅ 根据硬件生成个性化推荐
- ✅ 支持多卡环境提示
- ✅ 无 GPU 环境显示警告

---

### 2. 任务队列机制改进

#### 添加 QUEUED 状态

**文件**：`packages/sage-studio/src/sage/studio/services/finetune_manager.py`

**改进前**：
```python
class FinetuneStatus(str, Enum):
    PENDING = "pending"
    PREPARING = "preparing"
    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"

def start_training(self, task_id: str):
    if self.active_task_id:
        return False  # 静默失败
```

**改进后**：
```python
class FinetuneStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"      # 新增：等待 GPU 资源
    PREPARING = "preparing"
    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"

def start_training(self, task_id: str):
    if self.active_task_id:
        # 加入队列而非失败
        self.update_task_status(task_id, FinetuneStatus.QUEUED)
        self.add_task_log(
            task_id,
            f"任务已加入队列，等待 GPU 资源释放（当前运行: {self.active_task_id}）"
        )
        return True  # 返回成功
```

#### 自动处理队列

**新增方法**：
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

**工作流程**：
```
用户提交 3 个任务
    ↓
Task 1: PENDING → PREPARING → TRAINING
Task 2: PENDING → QUEUED（等待 Task 1）
Task 3: PENDING → QUEUED（等待 Task 1, 2）
    ↓
Task 1 完成
    ↓
Task 2: QUEUED → PREPARING → TRAINING
Task 3: QUEUED（继续等待）
    ↓
Task 2 完成
    ↓
Task 3: QUEUED → PREPARING → TRAINING
```

#### 前端显示队列状态

**文件**：`packages/sage-studio/src/sage/studio/frontend/src/components/FinetunePanel.tsx`

**改进**：
```tsx
// 类型定义
type FinetuneTask = {
    status: 'pending' | 'queued' | 'preparing' | 'training' | 'completed' | 'failed' | 'cancelled'
    // ...
}

// 状态标签配置
const statusConfig = {
    pending: { color: 'default', icon: <Clock />, text: '等待中' },
    queued: { color: 'warning', icon: <Clock />, text: '排队中' },  // 新增
    preparing: { color: 'processing', icon: <Cpu />, text: '准备中' },
    training: { color: 'processing', icon: <Cpu />, text: '训练中' },
    // ...
}
```

**UI 效果**：
- `排队中` 显示为**黄色**标签
- 鼠标悬停显示等待原因（日志中）

---

## Studio 队列 vs Control Plane

### 当前架构（Studio 本地队列）

**职责**：
- 管理 Studio 内的微调任务排队
- 防止单用户多任务同时占用 GPU
- 适用于单机开发环境

**实现**：
```
User → Studio UI → FinetuneManager (本地队列) → GPU
```

**优势**：
- ✅ 简单高效
- ✅ 无外部依赖
- ✅ 适合单用户场景

**限制**：
- ❌ 不支持多用户
- ❌ 不支持跨服务 GPU 共享（如 vLLM + 微调）

### 未来集成（SageLLM Control Plane）

**触发条件**（满足任一即需集成）：
1. Studio 部署为多用户服务器模式
2. GPU 被多个服务共享（vLLM 推理 + 微调）
3. 单用户同时提交 10+ 个任务
4. 需要企业级监控、配额、优先级等功能

**集成方案**：
```python
class FinetuneManager:
    def __init__(self):
        if os.getenv("SAGE_STUDIO_USE_CONTROL_PLANE") == "true":
            self.scheduler = SageLLMScheduler()  # 未来
        else:
            self.scheduler = LocalQueueScheduler()  # 当前
```

**迁移成本**：低（接口已预留）

---

## 文件变更清单

### 后端

1. **`packages/sage-studio/src/sage/studio/config/backend/api.py`**
   - ➕ 新增 `GET /api/system/gpu-info` 端点
   - 检测 GPU 型号、数量、显存
   - 生成动态推荐配置

2. **`packages/sage-studio/src/sage/studio/services/finetune_manager.py`**
   - ➕ 新增 `FinetuneStatus.QUEUED` 状态
   - 🔧 修改 `start_training()`：多任务加入队列
   - ➕ 新增 `_start_next_queued_task()`：自动处理队列
   - 🔧 修改 `update_task_status()`：任务完成时启动下一个

### 前端

3. **`packages/sage-studio/src/sage/studio/frontend/src/components/FinetunePanel.tsx`**
   - ➕ 新增 `gpuInfo` 状态
   - ➕ 新增 `loadGpuInfo()` 方法
   - 🔧 修改页面描述：硬编码 → 动态 GPU 推荐
   - ➕ 新增 `queued` 状态标签配置

### 文档

4. **`docs/dev-notes/cross-layer/finetune-gpu-resource-management.md`** (NEW)
   - 完整的 GPU 资源管理策略文档
   - Studio 队列 vs Control Plane 对比
   - 未来集成方案和最佳实践

5. **`docs/dev-notes/cross-layer/finetune-improvements-summary.md`** (NEW, 本文件)
   - 改进总结和测试指南

---

## 测试验证

### 测试 1：GPU 信息检测

**步骤**：
1. 启动 Studio：`sage studio start`
2. 打开浏览器：`http://localhost:4200`
3. 进入 "模型微调" 页面

**预期结果**：
- ✅ 页面顶部显示实际 GPU 型号和显存
- ✅ 推荐配置根据硬件自动生成
- ✅ 无 GPU 环境显示警告

**示例输出**：
```
💡 NVIDIA GeForce RTX 3060 (12.0GB): 推荐 Qwen 2.5 Coder 1.5B（最佳平衡）或 0.5B（最快训练）
```

### 测试 2：任务队列机制

**步骤**：
1. 快速提交 3 个微调任务（可以使用相同配置）
2. 观察任务列表状态变化

**预期结果**：
```
Task 1: pending → preparing → training
Task 2: pending → queued（黄色标签）
Task 3: pending → queued（黄色标签）

（等待 Task 1 完成后）
Task 1: completed（绿色）
Task 2: queued → preparing → training
Task 3: queued（继续等待）

（等待 Task 2 完成后）
Task 2: completed（绿色）
Task 3: queued → preparing → training
```

**日志检查**：
```bash
# 查看后端日志
tail -f ~/.sage/logs/studio.log

# 预期输出
[FinetuneManager] 启动排队任务: finetune_1732262400_1
任务已加入队列，等待 GPU 资源释放（当前运行: finetune_1732262400_0）
```

### 测试 3：GPU 信息 API

**步骤**：
```bash
curl http://localhost:8080/api/system/gpu-info | jq
```

**预期输出**：
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

---

## 已知限制和未来改进

### 当前限制

1. **不检测外部 GPU 占用**
   - 如果其他程序占用 GPU，微调任务可能 OOM
   - **缓解方案**：用户手动检查 `nvidia-smi`

2. **vLLM 推理和微调冲突**
   - 两者同时运行会竞争显存
   - **缓解方案**：微调前停止推理服务
   - **正式方案**：集成 Control Plane 统一管理

3. **队列无优先级**
   - 严格按提交时间 FIFO
   - **未来**：支持高优先级任务插队

4. **无任务超时机制**
   - 异常长时间任务会一直占用 GPU
   - **未来**：添加可配置超时（默认 6 小时）

### 未来改进方向

#### Phase 1（短期）
- [ ] 添加 GPU 可用性预检（启动前测试分配显存）
- [ ] 任务超时自动取消
- [ ] 队列长度告警（超过 5 个任务提示用户）

#### Phase 2（中期）
- [ ] 支持任务优先级
- [ ] 多 GPU 并行训练多个小任务
- [ ] MIG 支持（A100/H100 单卡多实例）

#### Phase 3（长期）
- [ ] 集成 SageLLM Control Plane
- [ ] 跨服务 GPU 资源共享
- [ ] 企业级监控和配额管理

---

## 相关文档

- [finetune-process-persistence.md](./finetune-process-persistence.md) - 进程持久化机制
- [finetune-backend-integration.md](./finetune-backend-integration.md) - vLLM 集成说明
- [finetune-gpu-resource-management.md](./finetune-gpu-resource-management.md) - GPU 资源管理策略（详细版）

---

## 总结

本次改进解决了两个关键问题：

1. **GPU 信息透明化**：
   - ✅ 用户能清楚看到实际硬件配置
   - ✅ 推荐配置根据环境自动调整
   - ✅ 避免因硬编码导致的误导

2. **任务队列优化**：
   - ✅ 多任务提交不再静默失败
   - ✅ 用户能看到排队状态
   - ✅ 自动处理任务调度，无需人工干预

**架构思路**：
- 当前实现满足单用户开发场景
- 为未来 Control Plane 集成预留接口
- 在复杂度和实用性之间取得平衡

**下一步**：
- 测试完整流程
- 收集用户反馈
- 根据生产需求决定是否集成 Control Plane
