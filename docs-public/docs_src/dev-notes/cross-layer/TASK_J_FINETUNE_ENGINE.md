# Task J: Fine-tune Engine Integration

**Status**: 🆕 IN PROGRESS\
**Date**: 2025-12-28\
**Owner**: Architecture Team

______________________________________________________________________

## 🎯 Goal

Integrate existing fine-tune functionality (`sage.libs.finetune`) into Control Plane as a new
`finetune` engine kind, replacing the stub implementation and providing unified resource management.

## 📋 Background

Currently, `sage llm fine-tune` is a stub that raises `NotImplementedError`. However, SAGE already
has a complete fine-tuning implementation in:

- `packages/sage-libs/src/sage/libs/finetune/` - Training manager, service, CLI
- `packages/sage-studio/src/sage/studio/services/finetune_manager.py` - Studio integration

This task connects these implementations to Control Plane for unified management.

## 🏗️ Architecture

### Before (Current State)

```
User → sage llm fine-tune → VLLMService.fine_tune() → NotImplementedError ❌
User → Studio UI → FinetuneManager → Training ✅ (isolated)
```

### After (Target State)

```
User → sage llm engine start --engine-kind finetune
     → Control Plane
     → FinetuneEngine
     → sage.libs.finetune.manager.FinetuneManager
     → Training with resource management ✅

User → sage llm fine-tune (convenience wrapper)
     → Internally calls: sage llm engine start --engine-kind finetune
```

## 📦 Components

### 1. FinetuneEngine (New - L1 Control Plane)

**Location**: `packages/sage-llm-core/src/sage/llm/control_plane/executors/finetune_executor.py`

**Interface**:

```python
from dataclasses import dataclass
from typing import Any, Dict, Optional
from sage.libs.finetune.manager import FinetuneManager

@dataclass
class FinetuneEngineConfig:
    """Configuration for fine-tune engine"""
    base_model: str
    dataset_path: str
    output_dir: str
    lora_rank: int = 8
    lora_alpha: int = 16
    learning_rate: float = 1e-4
    num_epochs: int = 3
    batch_size: int = 4
    max_seq_length: int = 512
    use_8bit: bool = True
    resume_from_checkpoint: Optional[str] = None

class FinetuneEngine:
    """Fine-tune engine managed by Control Plane"""

    engine_kind = "finetune"

    def __init__(self, config: FinetuneEngineConfig):
        self.config = config
        self.manager = FinetuneManager()
        self.task_id: Optional[str] = None
        self.status = "not_started"

    async def start(self) -> Dict[str, Any]:
        """Start fine-tuning task"""
        # 1. Create task in FinetuneManager
        # 2. Start training process
        # 3. Return task_id and initial status

    async def stop(self) -> Dict[str, Any]:
        """Stop training and save checkpoint"""
        # 1. Signal training to stop
        # 2. Wait for checkpoint save
        # 3. Update status

    async def get_status(self) -> Dict[str, Any]:
        """Get training progress"""
        # Return: status, progress, loss, ETA, GPU usage

    async def get_logs(self, tail: int = 100) -> List[str]:
        """Get training logs"""
        # Return last N lines of training log
```

### 2. CLI Updates (L6)

**Update**: `packages/sage-cli/src/sage/cli/commands/apps/llm.py`

#### Option 1: Enhance `engine start`

```bash
# Start fine-tune as engine
sage llm engine start Qwen/Qwen2.5-0.5B-Instruct \
  --engine-kind finetune \
  --dataset ./data/train.jsonl \
  --output ./models/finetuned \
  --lora-rank 8 \
  --num-epochs 3

# Check status
sage llm engine list  # Shows finetune engine with progress

# View logs
sage llm engine logs <engine-id> --follow

# Stop training (saves checkpoint)
sage llm engine stop <engine-id>
```

#### Option 2: Keep `fine-tune` as wrapper

```bash
# Convenience command (internally calls engine start)
sage llm fine-tune \
  --base-model Qwen/Qwen2.5-0.5B-Instruct \
  --dataset ./data/train.jsonl \
  --output ./models/finetuned \
  --lora-rank 8

# Returns: "Fine-tune engine started: <engine-id>"
# Use `sage llm engine list` to monitor progress
```

### 3. Control Plane Integration

**Update**: `packages/sage-llm-core/src/sage/llm/control_plane/manager.py`

```python
# Register finetune engine kind
SUPPORTED_ENGINE_KINDS = ["llm", "embedding", "finetune"]

# In ControlPlaneManager.start_engine()
if engine_kind == "finetune":
    from sage.llm.control_plane.executors.finetune_executor import FinetuneEngine
    engine = FinetuneEngine(config)
    await engine.start()
```

### 4. Gateway API (L6)

**Existing endpoints work automatically**:

- `POST /v1/management/engines/start` - Start finetune engine
- `GET /v1/management/engines` - List with status/progress
- `DELETE /v1/management/engines/{engine_id}` - Stop and save
- `GET /v1/management/engines/{engine_id}/logs` - View logs

## 🔧 Implementation Steps

### Phase 1: Core Engine (Priority)

1. ✅ Create `FinetuneEngineConfig` dataclass
1. ✅ Create `FinetuneEngine` class skeleton
1. ✅ Implement `start()` - connect to `FinetuneManager.start_training()`
1. ✅ Implement `stop()` - save checkpoint logic
1. ✅ Implement `get_status()` - read training metrics
1. ✅ Implement `get_logs()` - tail training log file

### Phase 2: Control Plane Integration

1. ✅ Register `finetune` in supported engine kinds
1. ✅ Add finetune-specific validation in `ControlPlaneManager`
1. ✅ Handle GPU resource coordination (optional: pause inference)
1. ✅ Emit metrics to monitoring system

### Phase 3: CLI Updates

1. ✅ Add `--engine-kind finetune` support to `sage llm engine start`
1. ✅ Add fine-tune specific arguments (dataset, output, lora config)
1. ✅ Update `sage llm fine-tune` to call engine start internally
1. ✅ Add helpful error messages and progress indicators

### Phase 4: Testing & Documentation

1. ✅ Write unit tests for `FinetuneEngine`
1. ✅ Write integration test: start → monitor → stop → load model
1. ✅ Update CLI help text and examples
1. ✅ Update user documentation with fine-tune workflow
1. ✅ Add smoke test to verification suite

## 📊 Success Criteria

### Functional Requirements

- ✅ `sage llm engine start --engine-kind finetune` launches training
- ✅ Training appears in `sage llm engine list` with real-time status
- ✅ `sage llm engine logs <id>` shows training logs
- ✅ `sage llm engine stop <id>` saves checkpoint gracefully
- ✅ Fine-tuned model can be loaded: `sage llm engine start <path> --engine-kind llm`

### Non-Functional Requirements

- ✅ Training metrics visible in Control Plane dashboard
- ✅ GPU memory tracked and managed
- ✅ Checkpoints saved to XDG user paths (`~/.local/share/sage/models/finetuned/`)
- ✅ Training survives Gateway restart (task persistence)

### Integration Test

```bash
# 1. Start fine-tune
ENGINE_ID=$(sage llm engine start Qwen/Qwen2.5-0.5B-Instruct \
  --engine-kind finetune \
  --dataset ./examples/data/sample_train.jsonl \
  --output ./test_finetune \
  --num-epochs 1 \
  | grep -oP 'engine-\w+')

# 2. Monitor progress
sage llm engine list  # Should show "running", progress%

# 3. View logs
sage llm engine logs $ENGINE_ID --tail 20

# 4. Stop (or wait for completion)
sage llm engine stop $ENGINE_ID  # Saves checkpoint

# 5. Load fine-tuned model
sage llm engine start ./test_finetune --engine-kind llm

# 6. Verify inference works
curl -X POST http://localhost:8889/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"sage-default","messages":[{"role":"user","content":"test"}]}'
```

## 🚧 Implementation Notes

### GPU Resource Coordination

When fine-tuning starts, Control Plane can optionally:

1. Check available GPU memory
1. If insufficient, pause/scale-down inference engines
1. Resume inference after training completes

This is optional for v1 - users can manually stop inference first.

### Checkpoint Management

- Checkpoints saved to: `get_user_paths().models_dir / "finetuned" / <task-id> / checkpoint-<step>`
- Final model saved to: `output_dir` specified by user
- Intermediate checkpoints configurable via `--save-steps`

### Progress Tracking

FinetuneEngine reads metrics from training log:

- Parse loss, accuracy from log file
- Estimate ETA based on steps/epoch
- Track GPU memory usage via nvidia-smi
- Expose via Control Plane API

## 📚 Related Documents

- Existing: `docs-public/docs_src/dev-notes/cross-layer/finetune-engine-integration.md`
- Existing: `packages/sage-libs/src/sage/libs/finetune/README.md`
- Existing: `packages/sage-studio/src/sage/studio/services/finetune_manager.py`

## 🔗 Dependencies

- `sage.libs.finetune` - Existing training implementation (✅ already available)
- `sage.llm.control_plane` - Engine management framework (✅ already available)
- PEFT library - LoRA implementation (✅ already in dependencies)
- Datasets library - Data loading (✅ already in dependencies)

## ⏱️ Estimated Effort

- **Phase 1** (Core Engine): 4-6 hours
- **Phase 2** (Control Plane): 2-3 hours
- **Phase 3** (CLI): 2-3 hours
- **Phase 4** (Testing): 3-4 hours
- **Total**: ~12-16 hours

## 🚀 Next Steps

1. Create `finetune_executor.py` skeleton
1. Implement basic `start()` connecting to FinetuneManager
1. Test with minimal training run
1. Add progress tracking
1. Integrate into CLI
1. Write tests and documentation

______________________________________________________________________

**Status Updates**:

- 2025-12-28: Task created, design documented
- 2025-12-28: Implementation started (Phase 1 in progress)
