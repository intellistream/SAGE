from sage.common.core import MapFunction
from sage.data.locomo.dataloader import LocomoDataLoader
from sage.benchmark.benchmark_memory.experiment.utils.progress_bar import ProgressBar


class PipelineCaller(MapFunction):
    """主 Pipeline 的 Map 算子

    职责：
    1. 调用记忆存储服务（总是执行）
    2. 检测是否有可见问题
    3. 如果有问题，调用记忆测试服务
    """

    def __init__(self, dataset: str, task_id: str):
        """初始化 PipelineCaller
        
        Args:
            dataset: 数据集名称 ('locomo', 等)
            task_id: 任务/样本ID
        """
        super().__init__()
        self.dataset = dataset
        self.task_id = task_id
        
        # 根据数据集类型初始化加载器
        if dataset == "locomo":
            self.loader = LocomoDataLoader()
            # 计算总对话数
            turns = self.loader.get_turn(task_id)
            self.total_dialogs = sum((max_dialog_idx + 1) for _, max_dialog_idx in turns)
        else:
            raise ValueError(f"不支持的数据集: {dataset}")
        
        # 初始化进度条
        self.progress_bar = ProgressBar(total=self.total_dialogs, desc="处理对话")
    
    def execute(self, data):
        """调用服务处理对话

        Args:
            data: 来自 MemorySource 的数据
                {
                    "task_id": "...",
                    "session_id": x,
                    "dialog_id": y,
                    "dialogs": [...]
                }
        """
        if not data:
            return None

        task_id = data.get("task_id")
        session_id = data.get("session_id")
        dialog_id = data.get("dialog_id")
        dialogs = data.get("dialogs", [])
        
        # 更新进度条
        self.progress_bar.update(1)
        
        # 打印【Memory Source】部分
        print(f"\n{'=' * 60}")
        print(f"\033[92m【Memory Source】\033[0m（{self.progress_bar.current}/{self.total_dialogs}）")
        print(f">> Session：{session_id}，Dialog {dialog_id}", end="")
        if len(dialogs) == 2:
            print(f" - {dialog_id + 1}")
        else:
            print()

        for i, dialog in enumerate(dialogs):
            speaker = dialog.get("speaker", "Unknown")
            text = dialog.get("text", "")
            print(f">> Dialog {dialog_id + i}({speaker}): {text}")
        print(f"\n{'=' * 60}")

        # ============================================================
        # 阶段1：记忆存储（总是执行）
        # ============================================================
        insert_data = {
            "task_id": task_id,
            "session_id": session_id,
            "dialog_id": dialog_id,
            "dialogs": dialogs,
        }

        # 调用记忆存储服务（阻塞等待）
        self.call_service(
            "memory_insert_service",
            insert_data,
            method="process",
            timeout=30.0,
        )

        # ============================================================
        # 阶段2：记忆测试（检测问题，如果有则测试）
        # ============================================================
        # 检查当前是否有可见问题
        current_questions = self.loader.get_question_list(
            task_id,
            session_x=session_id,
            dialog_y=dialog_id + len(dialogs) - 1,
            include_no_evidence=False,
        )

        total_visible = len(current_questions)

        # 如果没有可见问题，跳过测试阶段
        if total_visible == 0:
            print(f"{'=' * 60}\n")
            return {
                "task_id": task_id,
                "session_id": session_id,
                "dialog_id": dialog_id,
                "answers": [],
            }

        # 有可见问题，打印【QA】头部
        print(f"{'+' * 60}")
        print("【QA】：")
        print(f">> QA序列：1到{total_visible}")

        # 逐个问题调用记忆测试服务
        all_answers = []
        for q_idx, qa in enumerate(current_questions):
            question = qa["question"]
            evidence = qa.get("evidence", [])
            category = qa.get("category", "")

            # 构造单个问题的测试请求
            test_data = {
                "task_id": task_id,
                "session_id": session_id,
                "dialog_id": dialog_id,
                "dialogs": dialogs,
                "question": question,
                "question_idx": q_idx + 1,
                "evidence": evidence,
                "category": category,
            }

            try:
                # 调用记忆测试服务（阻塞等待）
                # 服务内部会：检索相关记忆 → 生成答案
                result = self.call_service(
                    "memory_test_service",
                    test_data,
                    method="process",
                    timeout=300.0,
                )

                # 提取答案结果
                answer_data = result.payload if hasattr(result, "payload") else result
                if "answer" in answer_data:
                    all_answers.append(answer_data)

                    # 打印问答
                    print(f">> Question {q_idx + 1}：{question}")
                    print(f">> Answer：{answer_data['answer']}")

            except Exception as e:
                # 服务调用失败（可能是超时、服务关闭等）
                print(f">> Question {q_idx + 1}：{question}")
                print(f">> Answer：[服务调用失败: {str(e)}]")
                # 记录失败的答案
                all_answers.append({
                    "question": question,
                    "answer": "[ERROR]",
                    "evidence": evidence,
                    "category": category,
                    "error": str(e),
                })
                # 继续处理下一个问题（而不是中断整个批次）

        print(f"{'+' * 60}\n")
        print(f"{'=' * 60}\n")
        
        # 如果处理完成，关闭进度条
        if self.progress_bar.current >= self.total_dialogs:
            self.progress_bar.close()

        # 返回所有问题的答案
        return {
            "task_id": task_id,
            "session_id": session_id,
            "dialog_id": dialog_id,
            "answers": all_answers,
        }
