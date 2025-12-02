# Feature: 微调引擎集成到 sageLLM Control Plane

## 问题背景

当前 SAGE Studio 的微调功能存在以下问题：

1. **GPU 资源竞争**: 微调任务和 vLLM/Embedding 推理服务共享 GPU，导致 OOM 或显存不足
2. **没有统一调度**: 微调进程独立运行，与 Control Plane 的资源管理脱节
3. **进度监控不完善**: 缺乏实时进度回传机制
4. **状态检测不准确**: 僵尸进程导致任务状态停留在"准备中"

## 设计目标

将微调功能作为一种"引擎"集成到 sageLLM Control Plane，实现统一的 GPU 资源管理。

## 架构设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                    sageLLM Control Plane (核心)                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  ResourceManager (GPU 资源统一管理)                          │   │
│   │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │   │
│   │  │ LLM Engine  │ │ Embed Engine│ │ Finetune Engine     │   │   │
│   │  │ (vLLM)      │ │ (BGE-M3)    │ │ (LoRA/PEFT)         │   │   │
│   │  │ 推理模式    │ │ Embedding   │ │ 训练模式            │   │   │
│   │  └─────────────┘ └─────────────┘ └─────────────────────┘   │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│   调度策略:                                                          │
│   - 微调任务需要 GPU 时，可选择：                                    │
│     a) 暂停/卸载推理引擎，释放显存                                   │
│     b) 使用较小的 GPU 配额（如 30%）                                │
│   - 微调完成后，自动重新加载推理引擎                                 │
│   - 支持任务优先级调度                                               │
└─────────────────────────────────────────────────────────────────────┘
```

## 核心功能

### 1. FinetuneEngine 类

```python
class FinetuneEngine:
    """微调引擎 - 集成到 Control Plane"""

    engine_kind = "finetune"

    def __init__(self, config: FinetuneEngineConfig):
        self.model_name = config.model_name
        self.dataset_path = config.dataset_path
        self.lora_config = config.lora_config

    async def start(self) -> None:
        """启动微调任务"""
        # 1. 请求 Control Plane 分配 GPU 资源
        # 2. 可选：暂停推理引擎释放显存
        # 3. 启动 LoRA 训练

    async def stop(self) -> None:
        """停止微调任务"""
        # 1. 保存 checkpoint
        # 2. 释放 GPU 资源
        # 3. 通知 Control Plane 资源已释放

    def get_progress(self) -> FinetuneProgress:
        """获取训练进度"""
        return FinetuneProgress(
            current_step=self.current_step,
            total_steps=self.total_steps,
            current_epoch=self.current_epoch,
            loss=self.current_loss,
        )
```

### 2. Control Plane 调度策略

```python
class FinetuneSchedulingPolicy:
    """微调任务调度策略"""

    # 策略选项
    PREEMPT_INFERENCE = "preempt"      # 暂停推理引擎
    SHARED_GPU = "shared"              # 共享 GPU（低配额）
    QUEUE_WAIT = "queue"               # 排队等待资源

    def schedule_finetune(self, task: FinetuneTask) -> ScheduleDecision:
        # 检查当前 GPU 使用情况
        # 根据策略决定如何调度
```

### 3. CLI 支持

```bash
# 通过 Control Plane 启动微调
sage llm engine start Qwen/Qwen2.5-0.5B-Instruct \
    --engine-kind finetune \
    --dataset /path/to/data.json \
    --preempt-inference  # 可选：暂停推理服务

# 查看微调进度
sage llm engine status <finetune-engine-id>

# 停止微调
sage llm engine stop <finetune-engine-id>
```

## 实现步骤

### Phase 1: 基础集成
- [ ] 创建 `FinetuneEngine` 类
- [ ] 实现 GPU 资源申请/释放 API
- [ ] 添加进度回调机制

### Phase 2: Control Plane 集成
- [ ] 在 `EngineManager` 中注册 finetune 引擎类型
- [ ] 实现 `FinetuneSchedulingPolicy`
- [ ] 支持暂停/恢复推理引擎

### Phase 3: Studio UI 集成
- [ ] 更新 Studio 使用 Control Plane API
- [ ] 实时进度展示
- [ ] GPU 资源使用可视化

## 相关文件

- `packages/sage-common/src/sage/common/components/sage_llm/sageLLM/control_plane/`
- `packages/sage-studio/src/sage/studio/services/finetune_manager.py`
- `packages/sage-libs/src/sage/libs/finetune/`

## 参考

- vLLM 不支持微调，只支持推理
- 微调需要 gradient、optimizer state 等，与推理内存模型不同
- 可参考 HuggingFace TRL、PEFT 的实现

## 优先级

Medium - 当前可通过手动停止推理服务来规避 GPU 冲突

## Labels

- enhancement
- sageLLM
- control-plane
- finetune
