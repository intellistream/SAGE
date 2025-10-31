"""
数据处理模块

处理各种格式的训练数据
"""

import json
from pathlib import Path

from datasets import Dataset


def load_training_data(data_path: str | Path) -> list[dict]:
    """加载训练数据

    Args:
        data_path: 数据文件路径 (.json 或 .jsonl)

    Returns:
        训练样本列表
    """
    data_path = Path(data_path)

    if not data_path.exists():
        raise FileNotFoundError(f"数据文件不存在: {data_path}")

    if data_path.suffix == ".jsonl":
        # JSONL 格式
        data = []
        with open(data_path) as f:
            for line in f:
                data.append(json.loads(line))
        return data
    elif data_path.suffix == ".json":
        # JSON 格式
        with open(data_path) as f:
            return json.load(f)
    else:
        raise ValueError(f"不支持的文件格式: {data_path.suffix}")


def format_alpaca_sample(sample: dict) -> dict:
    """格式化 Alpaca 格式的样本

    Alpaca 格式:
    {
        "instruction": "任务描述",
        "input": "可选的输入",
        "output": "期望的输出"
    }

    Args:
        sample: Alpaca 格式样本

    Returns:
        格式化后的样本 {"text": "..."}
    """
    text = f"### Instruction:\n{sample['instruction']}\n\n"
    if sample.get("input"):
        text += f"### Input:\n{sample['input']}\n\n"
    text += f"### Response:\n{sample['output']}"
    return {"text": text}


def format_conversation_sample(sample: dict) -> dict:
    """格式化对话格式的样本

    对话格式:
    {
        "conversations": [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."},
            ...
        ]
    }

    Args:
        sample: 对话格式样本

    Returns:
        格式化后的样本 {"text": "..."}
    """
    text = ""
    for msg in sample["conversations"]:
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            text += f"### User:\n{content}\n\n"
        elif role == "assistant":
            text += f"### Assistant:\n{content}\n\n"
        elif role == "system":
            text += f"### System:\n{content}\n\n"
    return {"text": text.strip()}


def format_qa_sample(sample: dict) -> dict:
    """格式化问答格式的样本

    QA 格式:
    {
        "question": "问题",
        "answer": "答案",
        "context": "可选的上下文"
    }

    Args:
        sample: QA 格式样本

    Returns:
        格式化后的样本 {"text": "..."}
    """
    text = f"### Question:\n{sample['question']}\n\n"
    if sample.get("context"):
        text += f"### Context:\n{sample['context']}\n\n"
    text += f"### Answer:\n{sample['answer']}"
    return {"text": text}


def detect_data_format(sample: dict) -> str:
    """自动检测数据格式

    Args:
        sample: 样本数据

    Returns:
        格式类型: "alpaca", "conversation", "qa", "text"
    """
    if "instruction" in sample and "output" in sample:
        return "alpaca"
    elif "conversations" in sample:
        return "conversation"
    elif "question" in sample and "answer" in sample:
        return "qa"
    elif "text" in sample:
        return "text"
    else:
        raise ValueError(f"无法识别的数据格式: {sample.keys()}")


def prepare_dataset(
    data_path: str | Path,
    tokenizer,
    max_length: int = 1024,
    format_type: str | None = None,
) -> Dataset:
    """准备训练数据集

    Args:
        data_path: 数据文件路径
        tokenizer: 分词器
        max_length: 最大序列长度
        format_type: 数据格式类型（None 表示自动检测）

    Returns:
        处理后的 Dataset
    """
    # 加载数据
    data = load_training_data(data_path)

    if len(data) == 0:
        raise ValueError("数据集为空")

    # 检测格式
    if format_type is None:
        format_type = detect_data_format(data[0])

    print(f"📊 数据格式: {format_type}")
    print(f"📊 样本数量: {len(data)}")

    # 格式化数据
    if format_type == "alpaca":
        formatted_data = [format_alpaca_sample(s) for s in data]
    elif format_type == "conversation":
        formatted_data = [format_conversation_sample(s) for s in data]
    elif format_type == "qa":
        formatted_data = [format_qa_sample(s) for s in data]
    elif format_type == "text":
        formatted_data = data
    else:
        raise ValueError(f"不支持的格式类型: {format_type}")

    # 创建 Dataset
    dataset = Dataset.from_list(formatted_data)

    # Tokenize
    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_length,
            padding="max_length",
        )

    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=["text"],
        desc="Tokenizing",
    )

    print("✅ 数据集准备完成")
    return tokenized_dataset


def create_sample_data(output_path: str | Path, format_type: str = "alpaca", num_samples: int = 10):
    """创建示例数据

    Args:
        output_path: 输出路径
        format_type: 数据格式
        num_samples: 样本数量
    """
    output_path = Path(output_path)

    if format_type == "alpaca":
        samples = [
            {
                "instruction": f"示例任务 {i}",
                "input": f"示例输入 {i}",
                "output": f"示例输出 {i}",
            }
            for i in range(num_samples)
        ]
    elif format_type == "qa":
        samples = [
            {
                "question": f"示例问题 {i}",
                "answer": f"示例答案 {i}",
                "context": f"示例上下文 {i}",
            }
            for i in range(num_samples)
        ]
    elif format_type == "conversation":
        samples = [
            {
                "conversations": [
                    {"role": "user", "content": f"用户消息 {i}"},
                    {"role": "assistant", "content": f"助手回复 {i}"},
                ]
            }
            for i in range(num_samples)
        ]
    else:
        raise ValueError(f"不支持的格式: {format_type}")

    with open(output_path, "w") as f:
        json.dump(samples, f, indent=2, ensure_ascii=False)

    print(f"✅ 创建了 {num_samples} 个示例样本: {output_path}")
