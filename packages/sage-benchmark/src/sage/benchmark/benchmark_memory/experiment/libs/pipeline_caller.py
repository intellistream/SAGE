from sage.benchmark.benchmark_memory.experiment.utils.progress_bar import ProgressBar
from sage.common.core import MapFunction
from sage.data.locomo.dataloader import LocomoDataLoader


class PipelineCaller(MapFunction):
    """主 Pipeline 的 Map 算子

    职责：
    1. 调用记忆存储服务（总是执行）
    2. 问题驱动测试：每当可见问题数增加超过总问题数的1/10时，触发一次测试
    3. 测试时测试从开始到当前位置的所有问题
    """

    def __init__(self, config):
        """初始化 PipelineCaller

        Args:
            config: RuntimeConfig 对象，从中获取 dataset 和 task_id
        """
        super().__init__()
        self.dataset = config.get("dataset")
        self.task_id = config.get("task_id")

        # 根据数据集类型初始化加载器
        if self.dataset == "locomo":
            self.loader = LocomoDataLoader()
        else:
            raise ValueError(f"不支持的数据集: {self.dataset}")

        # 进度条将在第一个数据包到达时初始化（因为需要从数据中获取总数）
        self.progress_bar = None

        # 问题驱动测试的状态跟踪
        self.total_questions = self._get_total_questions()  # 该task的总问题数
        self.last_tested_count = 0  # 上次测试时的问题数量
        self.test_threshold = max(1, self.total_questions // 10)  # 测试阈值（1/10）

        # 测试统计
        self.total_dialogs_inserted = 0  # 累计插入的对话数

    def _get_total_questions(self):
        """获取当前task的总问题数（排除没有evidence的问题）

        Returns:
            int: 总问题数
        """
        if self.dataset == "locomo":
            # 调用 dataloader 的方法获取有效问题总数
            return self.loader.get_total_valid_questions(self.task_id, include_no_evidence=False)
        return 0

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
        packet_idx = data.get("packet_idx", 0)
        total_packets = data.get("total_packets", 0)

        # 初始化或更新进度条
        if self.progress_bar is None:
            self.progress_bar = ProgressBar(total=total_packets, desc="处理对话")
        self.progress_bar.update(1)

        # 打印【Memory Source】部分（使用数据中的序号）
        print(f"\n{'=' * 60}")
        print(f"\033[92m【Memory Source】\033[0m（{packet_idx + 1}/{total_packets}）")
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

        # 累计插入的对话数
        self.total_dialogs_inserted += len(dialogs)

        # ============================================================
        # 阶段2：记忆测试（问题驱动）
        # ============================================================
        # 检查当前可见问题数量
        current_questions = self.loader.get_question_list(
            task_id,
            session_x=session_id,
            dialog_y=dialog_id + len(dialogs) - 1,
            include_no_evidence=False,
        )

        current_count = len(current_questions)

        # 计算自上次测试以来新增的问题数
        increment = current_count - self.last_tested_count

        # 判断是否为最后一个数据包
        is_last_packet = packet_idx + 1 >= total_packets

        # 如果新增问题数未达到阈值，且不是最后一个包，跳过测试
        if increment < self.test_threshold and not is_last_packet:
            print(f">> 当前可见问题数：{current_count}/{self.total_questions}")
            print(f">> 距上次测试新增：{increment}，阈值：{self.test_threshold}（未触发测试）")
            print(f"{'=' * 60}\n")
            # 不触发测试时，不发送数据给 Sink
            return None

        # 如果是最后一个包但增量不足，也要发送完成信号
        if increment < self.test_threshold and is_last_packet:
            print(f">> 当前可见问题数：{current_count}/{self.total_questions}")
            print(f">> 距上次测试新增：{increment}，阈值：{self.test_threshold}（未触发测试）")
            print(">> 最后一个数据包，发送完成信号")
            print(f"{'=' * 60}\n")

            # 关闭进度条
            if self.progress_bar:
                self.progress_bar.close()

            # 返回完成信号（不包含测试结果）
            return {
                "dataset": self.dataset,
                "task_id": task_id,
                "completed": True,
            }

        # 达到阈值或最后一个包，触发测试
        print(f"{'+' * 60}")
        if is_last_packet and increment < self.test_threshold:
            print("【QA】：最后一批数据，强制测试")
        else:
            print("【QA】：问题驱动测试触发")
        print(f">> 当前可见问题数：{current_count}/{self.total_questions}")
        print(f">> 距上次测试新增：{increment}，阈值：{self.test_threshold}")
        print(f">> 测试范围：问题 1 到 {current_count}")

        # 逐个问题调用记忆测试服务
        test_answers = []
        for q_idx, qa in enumerate(current_questions):
            question = qa["question"]

            # 构造单个问题的测试请求
            # 注意：只传递通用字段（question），不传递数据集私有属性
            # 如果需要 metadata（如 evidence, category），由 MemoryTest 从 qa 对象获取
            test_data = {
                "task_id": task_id,
                "session_id": session_id,
                "dialog_id": dialog_id,
                "dialogs": dialogs,
                "question": question,
                "question_idx": q_idx + 1,
                "question_metadata": qa,  # 传递完整的 qa 对象作为 metadata
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
                    # 构造标准化的答案记录
                    answer_record = {
                        "question_index": q_idx + 1,
                        "question": question,
                        "predicted_answer": answer_data["answer"],
                        "metadata": answer_data.get("question_metadata", qa),
                    }
                    test_answers.append(answer_record)

                    # 打印问答
                    print(f">> Question {q_idx + 1}：{question}")
                    print(f">> Answer：{answer_data['answer']}")

            except Exception as e:
                # 服务调用失败（可能是超时、服务关闭等）
                print(f">> Question {q_idx + 1}：{question}")
                print(f">> Answer：[服务调用失败: {str(e)}]")
                # 记录失败的答案
                test_answers.append(
                    {
                        "question_index": q_idx + 1,
                        "question": question,
                        "predicted_answer": "[ERROR]",
                        "error": str(e),
                        "metadata": qa,
                    }
                )
                # 继续处理下一个问题（而不是中断整个批次）

        # 构造本次测试结果
        test_result = {
            "dataset": self.dataset,
            "task_id": task_id,
            "question_range": {
                "start": 1,
                "end": current_count,
            },
            "dialogs_inserted": self.total_dialogs_inserted,
            "answers": test_answers,
            "completed": is_last_packet,  # 标记是否为最后一个包
        }

        # 更新上次测试的问题数量
        self.last_tested_count = current_count

        print(f"{'+' * 60}\n")
        print(f"{'=' * 60}\n")

        # 关闭进度条（如果是最后一个包）
        if is_last_packet and self.progress_bar:
            self.progress_bar.close()

        # 返回本次测试结果
        return test_result
