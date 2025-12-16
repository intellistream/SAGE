"""主 Pipeline 的核心处理算子

详细文档请参考: mem_docs/PipelineCaller.md
注意：修改代码时请同步更新该文档
"""

from sage.benchmark.benchmark_memory.experiment.utils import (
    ProgressBar,
    calculate_test_thresholds,
)
from sage.common.core import MapFunction
from sage.data.sources.locomo.dataloader import LocomoDataLoader
from sage.data.sources.memagentbench.conflict_resolution_loader import (
    ConflictResolutionDataLoader,
)


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

        # 获取实际的 memory service 名称（用于统计信息）
        self.memory_service_name = config.get(
            "services.register_memory_service", "short_term_memory"
        )

        # 服务调用超时时间（秒），默认 300 秒
        # 注意：这个超时必须 >= pipeline_service_timeout，否则调用方会先超时
        self.service_timeout = config.get("runtime.service_timeout", 300.0)

        # 根据数据集类型初始化加载器
        if self.dataset == "locomo":
            self.loader = LocomoDataLoader()
        elif self.dataset == "conflict_resolution":
            self.loader = ConflictResolutionDataLoader()
        else:
            raise ValueError(f"Unsupported dataset: {self.dataset}")

        # 进度条将在第一个数据包到达时初始化（因为需要从数据中获取总数）
        self.progress_bar = None

        # 问题驱动测试的状态跟踪
        self.total_questions = self.loader.get_total_valid_questions(
            self.task_id
        )  # 该task的总问题数
        self.last_tested_count = 0  # 上次测试时的问题数量

        # Calculate test thresholds based on dataset type
        if self.dataset == "conflict_resolution":
            # For conflict_resolution: test every 455 facts
            # Generate thresholds: 455, 910, 1365, 1820, 2275, 2730, 3185, 3640, 4095, 4550, 5005, 5460 (up to 5530)
            self.test_thresholds = []
            facts_per_test = 455
            current_threshold = facts_per_test
            total_facts = 5530
            while current_threshold <= total_facts:
                self.test_thresholds.append(current_threshold)
                current_threshold += facts_per_test
            self.test_based_on_facts = True
        else:
            # For other datasets (like locomo): test based on question count
            test_segments = config.get("runtime.test_segments", 10)
            self.test_thresholds = calculate_test_thresholds(self.total_questions, test_segments)
            self.test_based_on_facts = False

        self.next_threshold_idx = 0  # 下一个要触发的阈值索引

        # 测试统计
        self.total_dialogs_inserted = 0  # 累计插入的对话数

        # 累积所有 batch 的 timing 数据（不清空）
        self.accumulated_insert_timings = {
            "pre_insert_ms": [],
            "memory_insert_ms": [],
            "post_insert_ms": [],
        }

        # 跟踪已发送的 timing 位置（只返回增量）
        self.sent_insert_timing_count = 0

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

        # 判断是否为最后一个数据包（提前判断，用于异常处理）
        is_last_packet = packet_idx + 1 >= total_packets
        print(
            f"[DEBUG PipelineCaller] packet_idx={packet_idx}, total_packets={total_packets}, is_last_packet={is_last_packet}"
        )

        # 调用记忆存储服务（阻塞等待）
        # 注意：最后一包可能触发 link_evolution，可能超时
        insert_result = None
        try:
            insert_result = self.call_service(
                "memory_insert_service",
                insert_data,
                method="process",
                timeout=self.service_timeout,
            )
        except TimeoutError as e:
            print(f"[WARNING PipelineCaller] memory_insert_service 超时: {e}")
            # 如果是最后一包超时，仍然返回 completed=True 以保存结果
            if is_last_packet:
                print("[DEBUG PipelineCaller] 最后一包超时，但仍返回 completed=True 以保存结果")
                if self.progress_bar:
                    self.progress_bar.close()
                return {
                    "dataset": self.dataset,
                    "task_id": task_id,
                    "completed": True,
                    "warning": f"最后一包 memory_insert 超时: {e}",
                }
            else:
                # 非最后一包超时，重新抛出异常
                raise

        # 收集并累积插入阶段的时间数据
        if insert_result and "stage_timings" in insert_result:
            batch_timings = insert_result["stage_timings"]
            print(f"[DEBUG PipelineCaller] Batch {packet_idx + 1}: 收集 timing 数据")
            for key in ["pre_insert_ms", "memory_insert_ms", "post_insert_ms"]:
                if key in batch_timings:
                    timing_list = batch_timings[key]
                    if isinstance(timing_list, list):
                        self.accumulated_insert_timings[key].extend(timing_list)
                        print(f"[DEBUG PipelineCaller]   {key}: 累积 {len(timing_list)} 个时间点")
                    else:
                        print(f"[DEBUG PipelineCaller]   {key}: 警告 - 不是列表格式！")

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

        # 注意：is_last_packet 已在上面定义

        # 检查是否达到下一个测试阈值
        should_test = False
        next_threshold = None

        if self.next_threshold_idx < len(self.test_thresholds):
            next_threshold = self.test_thresholds[self.next_threshold_idx]

            # 根据数据集类型选择触发条件
            if self.test_based_on_facts:
                # For conflict_resolution: trigger based on facts inserted
                if self.total_dialogs_inserted >= next_threshold:
                    should_test = True
            else:
                # For other datasets: trigger based on question count
                if current_count >= next_threshold:
                    should_test = True

        # 如果未达到阈值，跳过测试
        if not should_test:
            if self.memory_test_verbose:
                if self.test_based_on_facts:
                    threshold_info = (
                        f"下一个阈值：{next_threshold} facts" if next_threshold else "无更多阈值"
                    )
                    print(f"\n>> 已插入facts数：{self.total_dialogs_inserted}")
                    print(f">> 当前可见问题数：{current_count}/{self.total_questions}")
                else:
                    threshold_info = (
                        f"下一个阈值：{next_threshold} 个问题" if next_threshold else "无更多阈值"
                    )
                    print(f"\n>> 当前可见问题数：{current_count}/{self.total_questions}")
                print(f">> 已测试问题数：{self.last_tested_count}，{threshold_info}（未触发测试）")

            # 如果是最后一个包，发送完成信号（包含剩余的 timing 数据）
            if is_last_packet:
                if self.memory_test_verbose:
                    print(">> 最后一个数据包，发送剩余 timing 数据")
                    print(f"{'=' * 60}")

                # 关闭进度条
                if self.progress_bar:
                    self.progress_bar.close()

                # 提取剩余的增量 timing 数据
                current_count = len(self.accumulated_insert_timings["pre_insert_ms"])
                remaining_count = current_count - self.sent_insert_timing_count
                print(f"[DEBUG PipelineCaller] 最后一包：剩余 {remaining_count} 个 timing 未发送")

                if remaining_count > 0:
                    # 有剩余数据，发送包含 timing 的完成信号
                    incremental_insert_timings = {
                        key: values[self.sent_insert_timing_count :]
                        for key, values in self.accumulated_insert_timings.items()
                    }

                    print("[DEBUG PipelineCaller] 返回完成信号（包含剩余 timing）")
                    return {
                        "dataset": self.dataset,
                        "task_id": task_id,
                        "completed": True,
                        "stage_timings": {
                            "insert": incremental_insert_timings,
                            "test": [],  # 最后一包没有测试结果
                        },
                    }
                else:
                    # 没有剩余数据，返回简单的完成信号
                    print("[DEBUG PipelineCaller] 返回完成信号（无剩余 timing）")
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
            if self.test_based_on_facts:
                print("【QA】：Facts数量驱动测试触发")
                print(f">> 已插入facts数：{self.total_dialogs_inserted}")
                print(f">> 当前可见问题数：{current_count}/{self.total_questions}")
                print(f">> 已测试问题数：{self.last_tested_count}")
                print(
                    f">> 触发阈值：{next_threshold} facts（第 {self.next_threshold_idx + 1}/{len(self.test_thresholds)} 个阈值）"
                )
            else:
                print("【QA】：问题驱动测试触发")
                print(f">> 当前可见问题数：{current_count}/{self.total_questions}")
                print(f">> 已测试问题数：{self.last_tested_count}")
                print(
                    f">> 触发阈值：{next_threshold}（第 {self.next_threshold_idx + 1}/{len(self.test_thresholds)} 个阈值）"
                )
            print(f">> 测试范围：问题 1 到 {current_count}")

        # 获取记忆体统计信息
        memory_stats = None
        try:
            # 调用实际的记忆体服务（如 short_term_memory）的 get_stats() 方法
            # 注意: get_stats() 不接受任何参数，所以不传递 data
            stats_result = self.call_service(
                self.memory_service_name,  # 使用实际的 memory service 名称
                method="get_stats",
                timeout=self.service_timeout,
            )
            if stats_result:
                memory_stats = stats_result
        except Exception as e:
            if self.memory_test_verbose:
                print(f">> 警告：获取记忆体统计失败: {e}")

        # 逐个问题调用记忆测试服务
        test_answers = []

        # 用于累积本次测试的 timing 数据（用于计算平均值）
        test_timing_accumulator = {
            "pre_retrieval_ms": [],
            "memory_retrieval_ms": [],
            "post_retrieval_ms": [],
        }

        for q_idx, qa in enumerate(current_questions):
            question = qa["question"]

            # 构造单个问题的测试请求
            # 注意：只传递通用字段（question），不传递数据集私有属性
            # 如果需要 metadata（如 evidence, category），由 MemoryEvaluation 从 qa 对象获取
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
                # 累积时间数据（用于计算本次测试的平均值）
                if "stage_timings" in result:
                    stage_timings = result["stage_timings"]
                    for key in ["pre_retrieval_ms", "memory_retrieval_ms", "post_retrieval_ms"]:
                        if key in stage_timings:
                            test_timing_accumulator[key].append(stage_timings[key])

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

        # 计算本次测试的平均 timing（一次测试一个值）
        avg_test_timing = {}
        for key, values in test_timing_accumulator.items():
            if values:
                avg_test_timing[key] = sum(values) / len(values)
                print(
                    f"[DEBUG PipelineCaller] {key} 平均值: {avg_test_timing[key]:.4f}ms (基于 {len(values)} 个问题)"
                )
            else:
                avg_test_timing[key] = 0.0

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

        # 添加时间统计数据（只返回自上次以来的增量）
        current_count = len(self.accumulated_insert_timings["pre_insert_ms"])
        print(f"[DEBUG PipelineCaller] 当前累积 timing 总数: {current_count}")
        print(f"[DEBUG PipelineCaller] 已发送 timing 数: {self.sent_insert_timing_count}")
        print(
            f"[DEBUG PipelineCaller] 本次返回增量: {current_count - self.sent_insert_timing_count}"
        )

        # 提取增量数据
        incremental_insert_timings = {
            key: values[self.sent_insert_timing_count :]
            for key, values in self.accumulated_insert_timings.items()
        }

        test_result["stage_timings"] = {
            "insert": incremental_insert_timings,  # 增量 insert timing（列表）
            "test": avg_test_timing,  # 本次测试的平均 retrieval timing（单个字典）
            "memory_stats": memory_stats,  # 本次测试的内存统计（单个字典）
        }

        # 更新已发送位置
        self.sent_insert_timing_count = current_count
        print(
            f"[DEBUG PipelineCaller] 更新 sent_insert_timing_count = {self.sent_insert_timing_count}"
        )

        # 更新测试状态
        self.last_tested_count = current_count
        self.next_threshold_idx += 1  # 移动到下一个阈值

        if self.memory_test_verbose:
            print(f"{'+' * 60}")

        # 关闭进度条（如果是最后一个包）
        if is_last_packet and self.progress_bar:
            self.progress_bar.close()

        # 返回本次测试结果
        print(
            f"[DEBUG PipelineCaller] 返回测试结果: completed={test_result.get('completed')}, answers={len(test_result.get('answers', []))}"
        )
        return test_result
