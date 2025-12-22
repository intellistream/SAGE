"""记忆评估模块 - 负责使用 LLM 对所有可见问题进行问答评估"""

import time

from sage.benchmark.benchmark_memory.experiment.utils import LLMGenerator
from sage.common.core import MapFunction


class MemoryEvaluation(MapFunction):
    """记忆评估算子

    职责：
    1. 使用历史对话 + LLM 生成答案
    2. 这是一个通用算子，不依赖特定数据集的私有属性
    """

    def __init__(self, config):
        super().__init__()
        self.config = config

        # 获取数据集类型（用于数据集特定的处理）
        self.dataset = config.get("runtime.dataset", "locomo")

        # 从配置中读取 prompt_template（阶段二：统一Prompt）
        self.question_answer_prompt = self.config.get(
            "runtime.prompt_template",
            """Based on the above context, answer the following question concisely using exact words from the context whenever possible. If the information is not mentioned in the conversation, respond with "Not mentioned in the conversation".

Question: {question}
Answer:""",
        )

        # 第五类问题专用 prompt（更简洁，适合选择题）
        self.question_answer_prompt_category5 = self.config.get(
            "runtime.prompt_template_category5",
            """Based on the above context, answer the following question.

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
        start_time = time.perf_counter()
        if not data:
            return None

        question = data.get("question")
        history_text = data.get("history_text", "")  # 来自PostRetrieval（阶段一）
        question_metadata = data.get("question_metadata", {})

        # 如果没有问题，返回空
        if not question:
            data["answer"] = None
            return data

        # ============================================================
        # 数据集特定处理：locomo 第五类问题（张冠李戴测试）
        # 强制将第五类问题格式化为选择题，以避免分数虚高
        # ============================================================
        # 默认使用标准 prompt
        selected_prompt = self.question_answer_prompt

        if self.dataset == "locomo":
            category = question_metadata.get("category")

            if category == 5:
                # 从 question_metadata 获取 adversarial_answer
                adversarial_answer = question_metadata.get("adversarial_answer", "")
                if adversarial_answer:
                    # 拼装选择题格式
                    question = (
                        f"{question} Select the correct answer: "
                        f"(a) {adversarial_answer} "
                        f"(b) Not mentioned in the conversation."
                    )
                    # 第五类问题使用专用 prompt
                    selected_prompt = self.question_answer_prompt_category5

        # 构建完整Prompt：history_text（阶段一） + question_answer_prompt（阶段二）
        full_prompt = history_text
        if full_prompt:
            full_prompt += "\n\n"

        # 拼接问答部分（阶段二）
        question_prompt = selected_prompt.replace("{question}", question)
        full_prompt += question_prompt

        prompt = full_prompt

        # ============ DEBUG: Prompt和答案打印 ============
        print("\n" + "=" * 80)
        print("📝 [MemoryEvaluation] 生成答案")
        print("=" * 80)
        print(f"问题: {question}")
        print(f"Prompt 长度: {len(prompt)} 字符")
        # print("\n完整 Prompt:")
        # print("-" * 80)
        # print(prompt)
        # print("-" * 80)
        # ============ DEBUG END ============

        # 调用 LLM 生成答案
        llm_start = time.perf_counter()
        answer_text = self.generator.generate(prompt)
        llm_elapsed = (time.perf_counter() - llm_start) * 1000
        print(f"⏱️  [MemoryEvaluation] LLM 答案生成耗时: {llm_elapsed:.2f}ms")

        # ============ DEBUG: 答案打印 ============
        print(f"\n✅ 生成的答案: {answer_text}")
        print("=" * 80)
        # ============ DEBUG END ============

        # answer_text = "yes"

        # 返回答案和元数据
        data["answer"] = answer_text
        data["question_metadata"] = question_metadata

        # 记录阶段耗时
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        data.setdefault("stage_timings", {})["memory_evaluation_ms"] = elapsed_ms
        print(f"⏱️  [MemoryEvaluation] 总耗时: {elapsed_ms:.2f}ms (包含 LLM: {llm_elapsed:.2f}ms)")
        print("=" * 80 + "\n")

        return data
