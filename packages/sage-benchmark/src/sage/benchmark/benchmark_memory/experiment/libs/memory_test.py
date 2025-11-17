"""记忆测试模块 - 负责使用 LLM 对所有可见问题进行问答测试"""

from sage.common.core import MapFunction
from sage.data.locomo.dataloader import LocomoDataLoader
from sage.middleware.operators.rag.generator import OpenAIGenerator
from sage.middleware.operators.rag.promptor import QAPromptor


class MemoryTest(MapFunction):
    """记忆测试算子
    
    职责：
    1. 检测当前可见的所有问题
    2. 如果有问题，使用历史对话 + LLM 生成答案
    3. 对所有可见问题（从第1题到最后一题）进行测试
    """

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.loader = LocomoDataLoader()

        # 初始化 LLM 组件
        self.promptor = None
        self.generator = None
        self._init_llm_components()

    def _init_llm_components(self):
        """初始化 Promptor 和 Generator"""
        promptor_config = self.config.get("promptor", {})
        if not promptor_config.get("template"):
            promptor_config["template"] = """你是一位友好的助手。请根据对话历史回答用户的问题。

对话历史:
{{ history }}

用户问题: {{ question }}

请提供简洁准确的回答："""

        self.promptor = QAPromptor(promptor_config)

        generator_config = self.config.get("generator", {}).get("vllm", {})

        # 确保有基本配置
        if not generator_config:
            raise ValueError("generator.vllm 配置缺失")

        self.generator = OpenAIGenerator(generator_config)

    def execute(self, data):
        """执行记忆测试
        
        Args:
            data: PipelineRequest 对象或字典
        
        Returns:
            在原始数据基础上添加 "answers" 字段
        """
        if not data:
            return None

        # 提取 payload（如果是 PipelineRequest）
        payload = data.payload if hasattr(data, "payload") else data

        task_id = payload.get("task_id")
        session_id = payload.get("session_id")
        dialog_id = payload.get("dialog_id")
        dialogs = payload.get("dialogs", [])
        history_text = payload.get("history_text", "")

        # 检查当前 session 和 dialog 截止是否有可见问题
        current_questions = self.loader.get_question_list(
            task_id,
            session_x=session_id,
            dialog_y=dialog_id + len(dialogs) - 1,
            include_no_evidence=False,
        )

        total_visible = len(current_questions)

        # 如果没有可见问题，返回空答案列表
        if total_visible == 0:
            payload["answers"] = []
            return data

        # 有可见问题，打印【QA】部分头
        print(f"{'+' * 60}")
        print("【QA】：")
        print(f">> QA序列：1到{total_visible}")

        # 对所有可见问题（从第1题到第total_visible题）进行测试
        answers = []
        for q_idx, qa in enumerate(current_questions):
            question = qa["question"]

            try:
                # 生成 Prompt
                prompted = self.promptor.execute({"question": question, "history": history_text})

                # 确保 generator 有 ctx
                if not hasattr(self.generator, "ctx") or self.generator.ctx is None:
                    self.generator.ctx = self.ctx

                # 调用 LLM 生成答案
                answer = self.generator.execute(prompted)

                # 提取答案文本
                if isinstance(answer, dict):
                    answer_text = answer.get("generated", str(answer))
                else:
                    answer_text = str(answer)

                answers.append(
                    {
                        "question": question,
                        "answer": answer_text,
                        "evidence": qa.get("evidence", []),
                        "category": qa.get("category", ""),
                    }
                )

                # 打印【QA】部分的问答
                print(f">> Question {q_idx + 1}：{question}")
                print(f">> Answer：{answer_text}")

            except Exception as e:
                import traceback

                traceback.print_exc()
                # 即使失败也继续处理下一个问题
                answers.append(
                    {
                        "question": question,
                        "answer": f"生成失败: {str(e)}",
                        "evidence": qa.get("evidence", []),
                        "category": qa.get("category", ""),
                    }
                )
                print(f">> Question {q_idx + 1}：{question}")
                print(f">> Answer：生成失败: {str(e)}")

        print(f"{'+' * 60}\n")

        # 添加答案到 payload 中
        payload["answers"] = answers

        return data
