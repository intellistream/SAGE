"""主 Pipeline 的核心处理算子

详细文档请参考: mem_docs/PipelineCaller.md
注意：修改代码时请同步更新该文档
"""

from sage.benchmark.benchmark_memory.experiment.utils.calculation_table import (
    calculate_test_thresholds,
)
from sage.benchmark.benchmark_memory.experiment.utils.progress_bar import ProgressBar
from sage.common.core import MapFunction
from sage.data.sources.locomo.dataloader import LocomoDataLoader


class PipelineCaller(MapFunction):
    """主 Pipeline 的核心 Map 算子

    负责协调记忆存储和记忆测试两个子 Pipeline，实现问题驱动的测试策略。

    详细说明（工作流程、服务调用、输出格式等）请参考:
    mem_docs/PipelineCaller.md
    """

    def __init__(self, config):
        """初始化 PipelineCaller

        Args:
            config: RuntimeConfig 对象，从中获取 dataset 和 task_id
        """
        super().__init__()
        self.dataset = config.get("dataset")
        self.task_id = config.get("task_id")

        # 服务调用超时时间（秒），默认 90 秒
        self.service_timeout = config.get("runtime.service_timeout", 90.0)

        # 根据数据集类型初始化加载器
        if self.dataset == "locomo":
            self.loader = LocomoDataLoader()
        else:
            raise ValueError(f"不支持的数据集: {self.dataset}")

        # 进度条将在第一个数据包到达时初始化（因为需要从数据中获取总数）
        self.progress_bar = None

        # 问题驱动测试的状态跟踪
        self.total_questions = self.loader.get_total_valid_questions(
            self.task_id
        )  # 该task的总问题数
        self.last_tested_count = 0  # 上次测试时的问题数量

        # 从配置中读取测试分段数（默认10段）
        test_segments = config.get("runtime.test_segments", 10)
        # 计算测试阈值数组
        self.test_thresholds = calculate_test_thresholds(self.total_questions, test_segments)
        self.next_threshold_idx = 0  # 下一个要触发的阈值索引

        # 测试统计
        self.total_dialogs_inserted = 0  # 累计插入的对话数

        # 调试打印开关（默认False）
        self.memory_insert_verbose = config.get("runtime.memory_insert_verbose", False)
        self.memory_test_verbose = config.get("runtime.memory_test_verbose", False)

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
        dialog_len = data.get("dialog_len", 0)
        packet_idx = data.get("packet_idx", 0)
        total_packets = data.get("total_packets", 0)

        # 初始化或更新进度条
        if self.progress_bar is None:
            self.progress_bar = ProgressBar(total=total_packets, desc="处理对话")
        self.progress_bar.update(1)

        # 打印【Memory Source】部分（使用数据中的序号）
        if self.memory_insert_verbose:
            print(f"\n{'=' * 60}")
            print(f"\033[92m[Memory Source]\033[0m (Packet {packet_idx + 1}/{total_packets})")

            prefix = ">> "
            # Session 行
            session_info = f"{prefix}Session: {session_id}, Dialog {dialog_id}"
            if len(dialogs) == 2:
                session_info += f" - {dialog_id + 1}"
            print(session_info)

            # Dialog 内容
            for i, dialog in enumerate(dialogs):
                speaker = dialog.get("speaker", "Unknown")
                text = dialog.get("text", "")
                print(f"{prefix}   Dialog {dialog_id + i} ({speaker}): {text}")
            print(f"{'=' * 60}")

        # ============================================================
        # 阶段1：记忆存储（总是执行）
        # ============================================================
        insert_data = {
            "task_id": task_id,
            "session_id": session_id,
            "dialog_id": dialog_id,
            "dialogs": dialogs,
            "packet_idx": packet_idx,
            "total_packets": total_packets,
        }

        # 调用记忆存储服务（阻塞等待）
        self.call_service(
            "memory_insert_service",
            insert_data,
            method="process",
            timeout=self.service_timeout,
        )

        # 累计插入的对话数
        self.total_dialogs_inserted += dialog_len

        # ============================================================
        # 阶段2：记忆测试（问题驱动）
        # ============================================================
        # 检查当前可见问题数量
        current_questions = self.loader.get_question_list(
            task_id,
            session_x=session_id,
            dialog_y=dialog_id + dialog_len - 1,
        )

        current_count = len(current_questions)

        # 判断是否为最后一个数据包
        is_last_packet = packet_idx + 1 >= total_packets

        # 检查是否达到下一个测试阈值
        should_test = False
        next_threshold = None

        if self.next_threshold_idx < len(self.test_thresholds):
            next_threshold = self.test_thresholds[self.next_threshold_idx]
            if current_count >= next_threshold:
                should_test = True

        # 如果未达到阈值，跳过测试
        if not should_test:
            if self.memory_test_verbose:
                threshold_info = f"下一个阈值：{next_threshold}" if next_threshold else "无更多阈值"
                print(f"\n>> 当前可见问题数：{current_count}/{self.total_questions}")
                print(f">> 已测试问题数：{self.last_tested_count}，{threshold_info}（未触发测试）")

            # 如果是最后一个包，发送完成信号
            if is_last_packet:
                if self.memory_test_verbose:
                    print(">> 最后一个数据包，发送完成信号")
                    print(f"{'=' * 60}")

                # 关闭进度条
                if self.progress_bar:
                    self.progress_bar.close()

                # 返回完成信号（不包含测试结果）
                return {
                    "dataset": self.dataset,
                    "task_id": task_id,
                    "completed": True,
                }

            if self.memory_test_verbose:
                print(f"{'=' * 60}\n")
            # 不触发测试时，不发送数据给 Sink
            return None

        # 达到阈值，触发测试
        if self.memory_test_verbose:
            print(f"\n{'+' * 60}")
            print("【QA】：问题驱动测试触发")
            print(f">> 当前可见问题数：{current_count}/{self.total_questions}")
            print(f">> 已测试问题数：{self.last_tested_count}")
            print(
                f">> 触发阈值：{next_threshold}（第 {self.next_threshold_idx + 1}/{len(self.test_thresholds)} 个阈值）"
            )
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

            # 调用记忆测试服务（阻塞等待）
            # 服务内部会：检索相关记忆 → 生成答案
            result = self.call_service(
                "memory_test_service",
                test_data,
                method="process",
                timeout=self.service_timeout,
            )

            # PipelineService 返回的是纯数据（已由 PipelineServiceSink 处理）
            if "answer" in result:
                # 构造标准化的答案记录
                answer_record = {
                    "question_index": q_idx + 1,
                    "question": question,
                    "predicted_answer": result["answer"],
                    "metadata": result.get("question_metadata", qa),
                }
                test_answers.append(answer_record)

                # 打印问答
                if self.memory_test_verbose:
                    print(f">> Question {q_idx + 1}：{question}")
                    print(f">> Answer：{result['answer']}")

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

        # 更新测试状态
        self.last_tested_count = current_count
        self.next_threshold_idx += 1  # 移动到下一个阈值

        if self.memory_test_verbose:
            print(f"{'+' * 60}")

        # 关闭进度条（如果是最后一个包）
        if is_last_packet and self.progress_bar:
            self.progress_bar.close()

        # 返回本次测试结果
        return test_result
