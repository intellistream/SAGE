"""记忆测试模块 - 负责使用 LLM 对所有可见问题进行问答测试"""

from sage.benchmark.benchmark_memory.experiment.utils.llm_generator import LLMGenerator
from sage.benchmark.benchmark_memory.experiment.utils.prompt_builder import build_prompt
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

        # 从配置中读取 prompt 模板
        self.prompt_template = self.config.get("runtime.prompt_template")
        if not self.prompt_template:
            # 默认模板
            self.prompt_template = """You are a helpful assistant. Answer the user's question based on the conversation history.

Conversation History:
{history}

User Question: {question}

Provide a brief and accurate answer in 2-3 sentences maximum:"""

        # 从配置中读取 generator 参数并初始化
        api_key = self.config.get("runtime.api_key")
        base_url = self.config.get("runtime.base_url")
        model_name = self.config.get("runtime.model_name")
        max_tokens = self.config.get("runtime.max_tokens", 512)
        temperature = self.config.get("runtime.temperature", 0.7)
        seed = self.config.get("runtime.seed")

        # 验证必需参数
        if not all([api_key, base_url, model_name]):
            raise ValueError("缺少必需的 LLM 配置: api_key, base_url, model_name")

        # 初始化 LLM 生成器
        self.generator = LLMGenerator(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            seed=seed,
        )

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
        history_text = data.get("history_text", "")
        question_metadata = data.get("question_metadata", {})

        # 如果没有问题，返回空
        if not question:
            data["answer"] = None
            return data

        # 构建 Prompt
        prompt = build_prompt(
            self.prompt_template,
            question=question,
            history=history_text,
        )

        # 调用 LLM 生成答案
        answer_text = self.generator.generate(prompt)
        # answer_text = "yes"

        # 返回答案和元数据
        data["answer"] = answer_text
        data["question_metadata"] = question_metadata

        return data
