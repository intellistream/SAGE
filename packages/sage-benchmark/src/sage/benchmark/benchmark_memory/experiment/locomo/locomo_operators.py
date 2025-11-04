"""Locomo 实验的算子定义 - 模拟长轮对话的记忆实验

架构说明：
- 主 Pipeline: 逐轮喂入对话历史
- 服务 Pipeline: 存储历史 + 检测问题 + 生成答案（不破坏历史状态）
"""

from sage.benchmark.benchmark_memory.data.locomo.locomo_dataloader import LocomoDataLoader
from sage.common.core import MapFunction
from sage.kernel.runtime.communication.router.packet import StopSignal
from sage.middleware.operators.rag.generator import OpenAIGenerator
from sage.middleware.operators.rag.promptor import QAPromptor


class LocomoServiceMap(MapFunction):
    """服务 Pipeline 的核心算子

    职责：
    1. 存储对话历史到内部状态
    2. 检测增量触发的新问题
    3. 如果有新问题，用"问题 + 最近3轮对话"生成答案
    4. 返回结果（只返回问题和答案，不返回对话历史）
    """

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.loader = LocomoDataLoader()

        # 内部状态：存储对话历史
        self.history_dialogs = []  # 存储所有对话
        self.last_question_count = 0  # 上一次的问题数量（用于检测是否有新问题）

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

        # 打印配置用于调试
        print(f"[DEBUG] Generator 配置: {generator_config}")

        self.generator = OpenAIGenerator(generator_config)

    def execute(self, data):
        """处理单轮对话

        Args:
            data: PipelineRequest 对象，包含：
                - payload: {"sample_id": "...", "session_id": x, "dialog_idx": y, "dialogs": [...]}
                - response_queue: Queue()

        Returns:
            {"payload": result, "response_queue": queue}
        """
        if not data:
            return None

        # 透传 StopSignal
        if isinstance(data, StopSignal):
            print(f"  [LocomoServiceMap] 透传停止信号: {data}")
            return data

        # 从 PipelineRequest 提取数据
        payload = data.payload if hasattr(data, "payload") else data["payload"]
        sample_id = payload["sample_id"]
        session_id = payload["session_id"]
        dialog_idx = payload["dialog_idx"]
        dialogs = payload["dialogs"]

        # 打印【Source】部分
        print(f"\n{'=' * 60}")
        print("【Source】：")
        print(f">> Session：{session_id}，Dialog {dialog_idx}", end="")
        if len(dialogs) == 2:
            print(f" & {dialog_idx + 1}")
        else:
            print()

        for i, dialog in enumerate(dialogs):
            speaker = dialog.get("speaker", "Unknown")
            text = dialog.get("text", "")
            print(f">> Dialog {dialog_idx + i}：{speaker}")
            print(f">> {text}")

        # 1. 先保存对话历史（无论是否有问题都要保存）
        for i, dialog in enumerate(dialogs):
            self.history_dialogs.append(
                {
                    "speaker": dialog["speaker"],
                    "text": dialog["text"],
                    "session_id": session_id,
                    "dialog_idx": dialog_idx + i,
                }
            )

        # 2. 检查当前 session 和 dialog 截止是否有可见问题
        current_questions = self.loader.get_question_list(
            sample_id,
            session_x=session_id,
            dialog_y=dialog_idx + len(dialogs) - 1,
            include_no_evidence=False,
        )

        total_visible = len(current_questions)

        # 3. 判断是否有新增问题（与上一次比较）
        if total_visible == self.last_question_count:
            # 没有新问题，直接返回（不打印【QA】部分）
            print(f"{'=' * 60}\n")

            # 返回空结果
            result_payload = {
                "sample_id": sample_id,
                "session_id": session_id,
                "dialog_idx": dialog_idx,
                "answers": [],
            }
            resp_q = (
                data.response_queue if hasattr(data, "response_queue") else data["response_queue"]
            )
            return {"payload": result_payload, "response_queue": resp_q}

        # 4. 有新问题，开始生成，打印【QA】部分头
        print(f"{'+' * 60}")
        print("【QA】：")
        # 本轮生成所有可见问题（从第 1 题到第 total_visible 题）
        print(f">> QA序列：1到{total_visible}")

        # 5. for 循环提问：对所有可见问题（1 到 total_visible）进行全量生成
        answers = []
        # 获取最近3轮对话（即最近6条消息）
        recent_dialogs = (
            self.history_dialogs[-6:] if len(self.history_dialogs) >= 6 else self.history_dialogs
        )
        history_text = "\n".join([f"{d['speaker']}: {d['text']}" for d in recent_dialogs])

        # 对所有可见问题进行全量生成（不跳过任何问题）
        for q_idx, qa in enumerate(current_questions):
            question = qa["question"]

            try:
                # 生成 Prompt
                prompted = self.promptor.execute({"question": question, "history": history_text})

                # 确保 generator 有 ctx
                if not hasattr(self.generator, "ctx") or self.generator.ctx is None:
                    self.generator.ctx = self.ctx

                # 调用 LLM 生成答案（不打印中间过程）
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

        # 更新 last_question_count（用于下次比较）
        self.last_question_count = total_visible

        # 4. 返回结果（只返回问题和答案，不返回对话历史）
        result_payload = {
            "sample_id": sample_id,
            "session_id": session_id,
            "dialog_idx": dialog_idx,
            "answers": answers,  # 只返回答案（包含问题、答案、evidence、category）
        }

        # 获取 response_queue
        resp_q = data.response_queue if hasattr(data, "response_queue") else data["response_queue"]

        return {"payload": result_payload, "response_queue": resp_q}


class LocomoControllerMap(MapFunction):
    """主 Pipeline 的 Map 算子

    职责：调用服务 Pipeline 处理对话
    """

    def execute(self, data):
        """调用服务处理对话

        Args:
            data: 来自 LocomoSource 的数据
                {
                    "sample_id": "...",
                    "session_id": x,
                    "dialog_idx": y,
                    "dialogs": [...]
                }
        """
        if not data:
            return None

        # 调用服务 Pipeline（阻塞等待）
        result = self.call_service(
            "locomo_service",
            data,
            method="process",
            timeout=300.0,  # 5分钟超时
        )

        return result
