"""
SAGE Agent Finetuning Module

针对 Agent 工具调用能力的专用微调模块，包含:
- AgentSFTTrainer: Agent 对话监督微调训练器
- CoresetSelector: 智能样本选择器
- OnlineContinualLearner: 在线持续学习模块
- AgentDialogProcessor: Agent 对话数据处理器
- TrajectoryCollector: FireAct 轨迹收集器
- TrajectoryFilter: 轨迹质量筛选器
- TrajectoryToSFTConverter: 轨迹转 SFT 数据转换器
- MultiTaskMixer: AgentTuning 多任务数据混合器
- AgentCapabilityEvaluator: Agent 多维能力评估器

这些组件是难题4（高精度工具规划与调用）的核心实现。

使用示例:
    from sage.libs.finetune.agent import AgentSFTTrainer, AgentSFTConfig

    config = AgentSFTConfig(
        base_model="Qwen/Qwen2.5-7B-Instruct",
        use_coreset_selection=True,
        coreset_strategy="hybrid",
        use_online_continual=True,
    )

    trainer = AgentSFTTrainer(config)
    trainer.train()

FireAct 轨迹微调示例:
    from sage.libs.finetune.agent import (
        TrajectoryCollector, TrajectoryFilter, TrajectoryToSFTConverter
    )

    # 收集轨迹
    collector = TrajectoryCollector(agent=my_agent)
    trajectories = collector.collect(tasks)

    # 筛选高质量轨迹
    filter = TrajectoryFilter(min_reward=0.5, require_success=True)
    good_trajectories = filter.filter(trajectories)

    # 转换为 SFT 数据
    converter = TrajectoryToSFTConverter()
    sft_data = converter.convert(good_trajectories)

AgentTuning 多任务训练示例:
    from sage.libs.finetune.agent import MultiTaskMixer, MixerConfig, TaskSample

    # 配置多任务混合权重
    config = MixerConfig(task_weights={
        "tool_selection": 0.35,
        "planning": 0.30,
        "timing": 0.20,
        "general": 0.15,
    })

    # 混合多个任务数据集
    mixer = MultiTaskMixer(config)
    mixed_data = mixer.mix(task_datasets)

    # 评估多维能力
    from sage.libs.finetune.agent import AgentCapabilityEvaluator
    evaluator = AgentCapabilityEvaluator()
    report = evaluator.evaluate(model, test_sets)
    print(report.summary())

Note on SIAS Components:
    CoresetSelector and OnlineContinualLearner have been moved to `sage.libs.sias`.
    Import them from `sage.libs.sias` in new code:

        from sage.libs.sias import CoresetSelector, OnlineContinualLearner
"""

# NOTE: SIAS-specific components (CoresetSelector, OnlineContinualLearner)
# have been moved to the `sage.libs.sias` package as they are Paper 2
# contributions. They are NO LONGER re-exported here. Import them from
# `sage.libs.sias` when you need them.

from .config import AgentRewardConfig, AgentSFTConfig, RLTrainingConfig
from .dialog_processor import AgentDialogProcessor, ProcessedDialog
from .multi_task import (
    AgentCapabilityEvaluator,
    AgentTuningConfig,
    CapabilityReport,
    CapabilityScore,
    MixerConfig,
    MultiTaskMixer,
    TaskSample,
)
from .trainer import AgentSFTTrainer
from .trajectory import (
    AgentTrajectory,
    CollectorConfig,
    SFTConversionConfig,
    TrajectoryCollector,
    TrajectoryFilter,
    TrajectoryStep,
    TrajectoryToSFTConverter,
    collect_and_convert,
    load_trajectories,
)


# 延迟导入较重的模块
def __getattr__(name):
    """延迟导入重量级模块"""
    if name == "AgentEvaluator":
        from .evaluator import AgentEvaluator

        return AgentEvaluator
    if name == "RewardModel":
        from .reward_model import RewardModel

        return RewardModel
    if name == "DataFormatter":
        from .data_formatter import DataFormatter

        return DataFormatter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # 核心配置
    "AgentSFTConfig",
    "RLTrainingConfig",
    "AgentRewardConfig",
    # 训练组件
    "AgentSFTTrainer",
    # 数据处理
    "AgentDialogProcessor",
    "ProcessedDialog",
    # AgentTuning 多任务训练
    "MultiTaskMixer",
    "MixerConfig",
    "TaskSample",
    "AgentCapabilityEvaluator",
    "CapabilityScore",
    "CapabilityReport",
    "AgentTuningConfig",
    # FireAct 轨迹微调
    "AgentTrajectory",
    "TrajectoryStep",
    "TrajectoryCollector",
    "CollectorConfig",
    "TrajectoryFilter",
    "TrajectoryToSFTConverter",
    "SFTConversionConfig",
    "collect_and_convert",
    "load_trajectories",
    # 延迟导入
    "AgentEvaluator",
    "RewardModel",
    "DataFormatter",
]
