#!/usr/bin/env python3
"""
Finetune CLI - Data Models and Enums
数据模型和枚举定义
"""

from enum import Enum


class FinetuneTask(str, Enum):
    """微调任务类型"""

    CODE_UNDERSTANDING = "code"  # 代码理解（默认：SAGE代码库）
    QA_PAIRS = "qa"  # 问答对
    INSTRUCTION = "instruction"  # 指令微调
    CHAT = "chat"  # 对话微调
    CUSTOM = "custom"  # 自定义数据集


# 任务类型的中文名称映射
TASK_NAMES = {
    FinetuneTask.CODE_UNDERSTANDING: "代码理解微调",
    FinetuneTask.QA_PAIRS: "问答对微调",
    FinetuneTask.INSTRUCTION: "指令微调",
    FinetuneTask.CHAT: "对话微调",
    FinetuneTask.CUSTOM: "自定义数据集",
}
