"""记忆测试模块 - 负责使用 LLM 对所有可见问题进行问答测试"""

from sage.benchmark.benchmark_memory.experiment.utils.llm_generator import LLMGenerator
from sage.common.core import MapFunction


class MemoryTest(MapFunction):
    """记忆测试算子

    职责：
    1. 使用历史对话 + LLM 生成答案
    2. 这是一个通用算子，不依赖特定数据集的私有属性
    """

    def __init__(self, config):
        super().__init__()
        self.config = config

        # 从配置中读取 prompt_template（阶段二：统一Prompt）
        self.question_answer_prompt = self.config.get(
            "runtime.prompt_template",
            """Based on the above context, answer the following question concisely using exact words from the context whenever possible. If the information is not mentioned in the conversation, respond with "Not mentioned in the conversation".

Question: {question}
Answer:""",
        )

        # 初始化 LLM 生成器
        self.generator = LLMGenerator.from_config(config)

    def execute(self, data):
        """执行记忆测试（生成答案）

        Args:
            data: 纯数据字典（已由 PipelineServiceSource 解包）

        Returns:
            在原始数据基础上添加 "answers" 字段
        """
        if not data:
            return None

        question = data.get("question")
        history_text = data.get("history_text", "")  # 来自PostRetrieval（阶段一）
        question_metadata = data.get("question_metadata", {})

        # 如果没有问题，返回空
        if not question:
            data["answer"] = None
            return data

        # 构建完整Prompt：history_text（阶段一） + question_answer_prompt（阶段二）
        full_prompt = history_text
        if full_prompt:
            full_prompt += "\n\n"

        # 拼接问答部分（阶段二）
        question_prompt = self.question_answer_prompt.replace("{question}", question)
        full_prompt += question_prompt

        prompt = full_prompt

        # 调用 LLM 生成答案
        answer_text = self.generator.generate(prompt)
        # answer_text = "yes"

        # 返回答案和元数据
        data["answer"] = answer_text
        data["question_metadata"] = question_metadata

        return data
