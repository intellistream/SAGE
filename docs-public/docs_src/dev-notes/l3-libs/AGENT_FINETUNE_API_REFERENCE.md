# Agent Fine-tuning API Reference

This document provides comprehensive API documentation for the `sage.libs.finetune.agent` module,
which implements specialized tools for fine-tuning language models on agent tasks.

**Module Path**: `sage.libs.finetune.agent`\
**Package**: `sage-libs`\
**Layer**: L3 (Libraries)

______________________________________________________________________

## Table of Contents

1. [Configuration Classes](#configuration-classes)
1. [Training Components](#training-components)
1. [Coreset Selection](#coreset-selection)
1. [Continual Learning](#continual-learning)
1. [Trajectory Collection (FireAct)](#trajectory-collection-fireact)
1. [Multi-Task Training (AgentTuning)](#multi-task-training-agenttuning)
1. [Evaluation](#evaluation)
1. [Method Registry](#method-registry)

______________________________________________________________________

## Configuration Classes

### AgentSFTConfig

Main configuration class for Agent SFT training.

```python
from sage.libs.finetune.agent import AgentSFTConfig
```

**Attributes**:

| Attribute                     | Type          | Default           | Description                                 |
| ----------------------------- | ------------- | ----------------- | ------------------------------------------- |
| `base_model`                  | `str`         | Required          | HuggingFace model ID or path                |
| `train_data`                  | `str`         | Required          | Training data path or DataManager reference |
| `eval_data`                   | `str \| None` | `None`            | Evaluation data path                        |
| `output_dir`                  | `Path`        | `.sage/finetune/` | Output directory for checkpoints            |
| `num_epochs`                  | `int`         | `3`               | Number of training epochs                   |
| `batch_size`                  | `int`         | `8`               | Per-device batch size                       |
| `learning_rate`               | `float`       | `2e-5`            | Learning rate                               |
| `gradient_accumulation_steps` | `int`         | `4`               | Gradient accumulation steps                 |
| `max_seq_length`              | `int`         | `2048`            | Maximum sequence length                     |
| `use_lora`                    | `bool`        | `True`            | Use LoRA for parameter-efficient tuning     |
| `lora_r`                      | `int`         | `16`              | LoRA rank                                   |
| `lora_alpha`                  | `int`         | `32`              | LoRA alpha                                  |
| `use_dora`                    | `bool`        | `False`           | Use DoRA (Weight-Decomposed LoRA)           |
| `use_lora_plus`               | `bool`        | `False`           | Use LoRA+ (Differentiated LR)               |
| `lora_plus_lr_ratio`          | `float`       | `16.0`            | LoRA+ B matrix LR ratio                     |
| `use_coreset_selection`       | `bool`        | `False`           | Enable coreset selection                    |
| `coreset_strategy`            | `str`         | `"hybrid"`        | Coreset strategy                            |
| `coreset_target_size`         | `int \| None` | `None`            | Target coreset size                         |
| `use_online_continual`        | `bool`        | `False`           | Enable continual learning                   |
| `continual_buffer_size`       | `int`         | `2048`            | Replay buffer size                          |
| `continual_replay_ratio`      | `float`       | `0.25`            | Replay ratio per batch                      |

**Example**:

```python
config = AgentSFTConfig(
    base_model="Qwen/Qwen2.5-1.5B-Instruct",
    train_data="agent_sft:train",
    num_epochs=2,
    use_coreset_selection=True,
    coreset_strategy="hybrid",
    use_dora=True,
)
```

______________________________________________________________________

### RLTrainingConfig

Configuration for reinforcement learning training (PPO/DPO).

```python
from sage.libs.finetune.agent import RLTrainingConfig
```

**Attributes**:

| Attribute      | Type          | Default | Description                 |
| -------------- | ------------- | ------- | --------------------------- |
| `algorithm`    | `str`         | `"ppo"` | RL algorithm ("ppo", "dpo") |
| `reward_model` | `str \| None` | `None`  | Reward model path           |
| `kl_coef`      | `float`       | `0.1`   | KL divergence coefficient   |
| `gamma`        | `float`       | `0.99`  | Discount factor             |

______________________________________________________________________

## Training Components

### AgentSFTTrainer

Main trainer class for Agent SFT.

```python
from sage.libs.finetune.agent import AgentSFTTrainer
```

**Constructor**:

```python
AgentSFTTrainer(config: AgentSFTConfig)
```

**Methods**:

| Method             | Returns          | Description           |
| ------------------ | ---------------- | --------------------- |
| `train()`          | `TrainingResult` | Execute training      |
| `evaluate(data)`   | `EvalResult`     | Evaluate on data      |
| `save_model(path)` | `None`           | Save model checkpoint |
| `load_model(path)` | `None`           | Load model checkpoint |

**Example**:

```python
config = AgentSFTConfig(
    base_model="Qwen/Qwen2.5-1.5B-Instruct",
    train_data="agent_sft:train",
)

trainer = AgentSFTTrainer(config)

# Train
result = trainer.train()
print(f"Final loss: {result.final_loss}")

# Evaluate
eval_result = trainer.evaluate("agent_sft:test")
print(f"Accuracy: {eval_result.accuracy}")

# Save
trainer.save_model("./my_agent_model")
```

______________________________________________________________________

## Coreset Selection

### CoresetSelector

Intelligently select training samples based on various strategies.

```python
from sage.libs.sias import CoresetSelector
```

**Constructor**:

```python
CoresetSelector(
    strategy: Literal["loss_topk", "diversity", "hybrid", "random"] = "hybrid",
    target_size: int = 1000,
    loss_ratio: float = 0.6,  # For hybrid strategy
)
```

**Methods**:

| Method                           | Returns       | Description               |
| -------------------------------- | ------------- | ------------------------- |
| `select(samples, model=None)`    | `list[dict]`  | Select samples from pool  |
| `compute_losses(samples, model)` | `list[float]` | Compute per-sample losses |
| `compute_diversity(samples)`     | `np.ndarray`  | Compute diversity matrix  |

**Strategies**:

| Strategy    | Description                      | Requires Model |
| ----------- | -------------------------------- | -------------- |
| `loss_topk` | Select samples with highest loss | Yes            |
| `diversity` | Select most diverse samples      | No             |
| `hybrid`    | 60% loss + 40% diversity         | Yes            |
| `random`    | Random selection (baseline)      | No             |

**Example**:

```python
selector = CoresetSelector(
    strategy="hybrid",
    target_size=1000,
    loss_ratio=0.6,
)

# Select best samples
selected = selector.select(all_samples, model=my_model)
print(f"Selected {len(selected)} samples")

# Just compute losses
losses = selector.compute_losses(all_samples, model=my_model)
```

______________________________________________________________________

## Continual Learning

### OnlineContinualLearner

Experience replay for preventing catastrophic forgetting.

```python
from sage.libs.sias import OnlineContinualLearner
```

**Constructor**:

```python
OnlineContinualLearner(
    buffer_size: int = 2048,
    replay_ratio: float = 0.25,
    selection_strategy: str = "reservoir",
)
```

**Methods**:

| Method                   | Returns | Description                   |
| ------------------------ | ------- | ----------------------------- |
| `mix_with_replay(batch)` | `dict`  | Mix batch with replay samples |
| `update_buffer(batch)`   | `None`  | Add samples to buffer         |
| `get_replay_samples(n)`  | `list`  | Sample from buffer            |
| `clear_buffer()`         | `None`  | Clear replay buffer           |

**Example**:

```python
learner = OnlineContinualLearner(
    buffer_size=2048,
    replay_ratio=0.25,
)

for batch in data_loader:
    # Mix with replay
    mixed_batch = learner.mix_with_replay(batch)

    # Train step
    loss = train_step(mixed_batch)

    # Update buffer
    learner.update_buffer(batch)
```

______________________________________________________________________

## Trajectory Collection (FireAct)

Implements trajectory-based fine-tuning from Chen et al., 2023.

### AgentTrajectory

Data class representing an agent execution trajectory.

```python
from sage.libs.finetune.agent import AgentTrajectory, TrajectoryStep
```

**TrajectoryStep Attributes**:

| Attribute      | Type    | Description          |
| -------------- | ------- | -------------------- |
| `thought`      | `str`   | Agent's reasoning    |
| `action`       | `str`   | Action/tool name     |
| `action_input` | `dict`  | Action parameters    |
| `observation`  | `str`   | Environment feedback |
| `reward`       | `float` | Step reward          |

**AgentTrajectory Attributes**:

| Attribute      | Type                   | Description               |
| -------------- | ---------------------- | ------------------------- |
| `task_id`      | `str`                  | Unique task identifier    |
| `instruction`  | `str`                  | Original task instruction |
| `steps`        | `list[TrajectoryStep]` | Execution steps           |
| `success`      | `bool`                 | Whether task succeeded    |
| `total_reward` | `float`                | Cumulative reward         |

______________________________________________________________________

### TrajectoryCollector

Collect agent execution trajectories.

```python
from sage.libs.finetune.agent import TrajectoryCollector, CollectorConfig
```

**CollectorConfig Attributes**:

| Attribute           | Type   | Default | Description                          |
| ------------------- | ------ | ------- | ------------------------------------ |
| `max_steps`         | `int`  | `10`    | Max steps per trajectory             |
| `require_success`   | `bool` | `True`  | Only collect successful trajectories |
| `save_intermediate` | `bool` | `True`  | Save intermediate observations       |

**TrajectoryCollector Methods**:

| Method                 | Returns                 | Description                    |
| ---------------------- | ----------------------- | ------------------------------ |
| `collect(tasks)`       | `list[AgentTrajectory]` | Collect trajectories for tasks |
| `collect_single(task)` | `AgentTrajectory`       | Collect single trajectory      |

**Example**:

```python
config = CollectorConfig(max_steps=10, require_success=True)
collector = TrajectoryCollector(agent=my_agent, config=config)

# Collect trajectories
trajectories = collector.collect(task_list)
print(f"Collected {len(trajectories)} trajectories")
```

______________________________________________________________________

### TrajectoryFilter

Filter trajectories by quality criteria.

```python
from sage.libs.finetune.agent import TrajectoryFilter
```

**Constructor**:

```python
TrajectoryFilter(
    min_reward: float = 0.5,
    require_success: bool = True,
    max_steps: Optional[int] = None,
)
```

**Methods**:

| Method                    | Returns                 | Description              |
| ------------------------- | ----------------------- | ------------------------ |
| `filter(trajectories)`    | `list[AgentTrajectory]` | Filter trajectories      |
| `get_stats(trajectories)` | `dict`                  | Get filtering statistics |

**Example**:

```python
filter = TrajectoryFilter(min_reward=0.5, require_success=True)

# Filter trajectories
good_trajectories = filter.filter(all_trajectories)

# Get statistics
stats = filter.get_stats(all_trajectories)
print(f"Kept {stats['kept']} / {stats['total']} trajectories")
```

______________________________________________________________________

### TrajectoryToSFTConverter

Convert trajectories to SFT training format.

```python
from sage.libs.finetune.agent import TrajectoryToSFTConverter, SFTConversionConfig
```

**SFTConversionConfig Attributes**:

| Attribute             | Type          | Default    | Description                        |
| --------------------- | ------------- | ---------- | ---------------------------------- |
| `format`              | `str`         | `"chatml"` | Output format ("chatml", "alpaca") |
| `include_observation` | `bool`        | `True`     | Include observations in output     |
| `system_prompt`       | `str \| None` | `None`     | Custom system prompt               |

**Methods**:

| Method                       | Returns      | Description               |
| ---------------------------- | ------------ | ------------------------- |
| `convert(trajectories)`      | `list[dict]` | Convert to SFT format     |
| `convert_single(trajectory)` | `dict`       | Convert single trajectory |

**Example**:

```python
config = SFTConversionConfig(format="chatml", include_observation=True)
converter = TrajectoryToSFTConverter(config)

# Convert trajectories
sft_data = converter.convert(trajectories)

# Save to file
with open("sft_data.jsonl", "w") as f:
    for sample in sft_data:
        f.write(json.dumps(sample) + "\n")
```

______________________________________________________________________

### Convenience Functions

```python
from sage.libs.finetune.agent import collect_and_convert, load_trajectories

# One-step collection and conversion
sft_data = collect_and_convert(
    agent=my_agent,
    tasks=task_list,
    min_reward=0.5,
    require_success=True,
)

# Load trajectories from file
trajectories = load_trajectories("trajectories.jsonl")
```

______________________________________________________________________

## Multi-Task Training (AgentTuning)

Implements multi-task agent training from Zeng et al., 2023.

### MultiTaskMixer

Mix multiple task datasets with configurable weights.

```python
from sage.libs.finetune.agent import MultiTaskMixer, MixerConfig, TaskSample
```

**MixerConfig Attributes**:

| Attribute      | Type               | Default      | Description          |
| -------------- | ------------------ | ------------ | -------------------- |
| `task_weights` | `dict[str, float]` | Required     | Per-task weights     |
| `strategy`     | `str`              | `"weighted"` | Mixing strategy      |
| `shuffle`      | `bool`             | `True`       | Shuffle after mixing |

**TaskSample Attributes**:

| Attribute   | Type          | Description   |
| ----------- | ------------- | ------------- |
| `task_type` | `str`         | Task category |
| `data`      | `dict`        | Sample data   |
| `source`    | `str \| None` | Data source   |

**Methods**:

| Method                           | Returns            | Description     |
| -------------------------------- | ------------------ | --------------- |
| `mix(task_datasets)`             | `list[TaskSample]` | Mix datasets    |
| `get_task_distribution(samples)` | `dict[str, int]`   | Get task counts |

**Example**:

```python
config = MixerConfig(
    task_weights={
        "tool_selection": 0.35,
        "planning": 0.30,
        "timing": 0.20,
        "general": 0.15,
    },
    strategy="weighted",
)

mixer = MultiTaskMixer(config)

# Mix datasets
mixed_data = mixer.mix({
    "tool_selection": tool_selection_samples,
    "planning": planning_samples,
    "timing": timing_samples,
    "general": general_samples,
})

# Check distribution
dist = mixer.get_task_distribution(mixed_data)
print(f"Task distribution: {dist}")
```

______________________________________________________________________

### AgentCapabilityEvaluator

Evaluate multi-dimensional agent capabilities.

```python
from sage.libs.finetune.agent import (
    AgentCapabilityEvaluator, CapabilityScore, CapabilityReport
)
```

**Capabilities Evaluated**:

| Capability              | Description                 |
| ----------------------- | --------------------------- |
| `tool_use`              | Tool calling accuracy       |
| `planning`              | Multi-step planning quality |
| `reasoning`             | Reasoning chain coherence   |
| `instruction_following` | Instruction adherence       |

**Methods**:

| Method                                  | Returns            | Description       |
| --------------------------------------- | ------------------ | ----------------- |
| `evaluate(model, test_sets)`            | `CapabilityReport` | Full evaluation   |
| `evaluate_capability(model, cap, data)` | `CapabilityScore`  | Single capability |

**CapabilityScore Attributes**:

| Attribute     | Type    | Description       |
| ------------- | ------- | ----------------- |
| `capability`  | `str`   | Capability name   |
| `score`       | `float` | Score (0-1)       |
| `num_samples` | `int`   | Samples evaluated |
| `details`     | `dict`  | Detailed metrics  |

**CapabilityReport Methods**:

| Method                  | Returns | Description         |
| ----------------------- | ------- | ------------------- |
| `summary()`             | `str`   | Text summary        |
| `to_dict()`             | `dict`  | Dict representation |
| `get_score(capability)` | `float` | Get single score    |

**Example**:

```python
evaluator = AgentCapabilityEvaluator()

# Full evaluation
report = evaluator.evaluate(model, {
    "tool_use": tool_test_data,
    "planning": planning_test_data,
    "reasoning": reasoning_test_data,
})

# Print summary
print(report.summary())
# Output:
# Agent Capability Report
# -----------------------
# Tool Use: 0.92 (n=500)
# Planning: 0.78 (n=300)
# Reasoning: 0.85 (n=400)
# Overall: 0.85

# Access individual scores
tool_score = report.get_score("tool_use")
```

______________________________________________________________________

## Method Registry

### MethodRegistry

Registry of predefined training methods for systematic comparison.

```python
from sage.benchmark.benchmark_agent.experiments.method_comparison import (
    MethodRegistry, MethodConfig
)
```

**Class Methods**:

| Method                | Returns                   | Description              |
| --------------------- | ------------------------- | ------------------------ |
| `get_all_methods()`   | `dict[str, MethodConfig]` | All predefined methods   |
| `get_quick_methods()` | `dict[str, MethodConfig]` | Subset for quick testing |

**MethodConfig Attributes**:

| Attribute                   | Type   | Description               |
| --------------------------- | ------ | ------------------------- |
| `name`                      | `str`  | Display name              |
| `description`               | `str`  | Method description        |
| `use_coreset`               | `bool` | Enable coreset selection  |
| `coreset_strategy`          | `str`  | Coreset strategy          |
| `use_continual`             | `bool` | Enable continual learning |
| `use_dora`                  | `bool` | Enable DoRA               |
| `use_lora_plus`             | `bool` | Enable LoRA+              |
| `use_trajectory_collection` | `bool` | Enable FireAct            |
| `use_multi_task`            | `bool` | Enable AgentTuning        |

**Predefined Methods**:

| ID                     | Name                | Key Features           |
| ---------------------- | ------------------- | ---------------------- |
| `A_baseline`           | Baseline            | Standard SFT           |
| `B1_coreset_loss`      | Coreset (Loss)      | Loss-based selection   |
| `B2_coreset_diversity` | Coreset (Diversity) | Diversity selection    |
| `B3_coreset_hybrid`    | Coreset (Hybrid)    | Combined selection     |
| `C_continual`          | Continual           | Experience replay      |
| `D_combined`           | Combined            | Coreset + Continual    |
| `E_fireact`            | FireAct             | Trajectory fine-tuning |
| `F_agenttuning`        | AgentTuning         | Multi-task training    |
| `G_dora`               | DoRA                | Weight-decomposed LoRA |
| `H_lora_plus`          | LoRA+               | Differentiated LR      |

**Example**:

```python
# Get all methods
all_methods = MethodRegistry.get_all_methods()
print(f"Available: {list(all_methods.keys())}")

# Get specific method config
fireact_config = all_methods["E_fireact"]
print(f"FireAct: {fireact_config.description}")

# Create custom method
custom = MethodConfig(
    name="My Method",
    description="Custom combination",
    use_dora=True,
    use_continual=True,
    continual_buffer_size=4096,
)
```

______________________________________________________________________

## See Also

- [Benchmark Agent README](../../../../packages/sage-benchmark/src/sage/benchmark/benchmark_agent/README.md)
- [Data Paths Documentation](../../../../packages/sage-benchmark/src/sage/benchmark/benchmark_agent/DATA_PATHS.md)
- [FireAct Paper](https://arxiv.org/abs/2310.05915) - Chen et al., 2023
- [AgentTuning Paper](https://arxiv.org/abs/2310.12823) - Zeng et al., 2023
- [DoRA Paper](https://arxiv.org/abs/2402.09353) - Liu et al., 2024
- [LoRA+ Paper](https://arxiv.org/abs/2402.12354) - Hayou et al., 2024
