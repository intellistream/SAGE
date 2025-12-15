import json
import os

from sage.benchmark.benchmark_memory.experiment.utils import (
    get_project_root,
    get_runtime_timestamp,
    get_time_filename,
)
from sage.common.core import SinkFunction


class MemorySink(SinkFunction):
    """收集测试结果并保存为 JSON 格式的 Sink"""

    def __init__(self, config):
        """初始化 MemorySink

        Args:
            config: RuntimeConfig 对象，从中获取 dataset 和 task_id
        """
        self.dataset = config.get("dataset")
        self.task_id = config.get("task_id")
        self.test_segments = config.get("runtime.test_segments", 10)
        self.memory_name = config.get("runtime.memory_name", "default")

        # 获取项目根目录
        project_root = get_project_root()

        # 创建时间戳目录结构，包含 memory_name
        time_str = get_time_filename()
        self.output_dir = os.path.join(
            project_root,
            f".sage/benchmarks/benchmark_memory/{self.dataset}/{time_str}/{self.memory_name}",
        )
        os.makedirs(self.output_dir, exist_ok=True)

        # 设置输出文件路径（格式：task_id_HHMM.json）
        runtime_stamp = get_runtime_timestamp()
        self.output_file = os.path.join(self.output_dir, f"{self.task_id}_{runtime_stamp}.json")
        print(f"💾 输出文件: {self.output_file}")

        # 收集所有测试结果
        self.test_results = []

        # 分离存储两种 timing 数据
        self.all_insert_timings = []  # 插入阶段：每个 dialog 的 timing
        self.all_test_timings = []  # 检索阶段：每次测试的平均 timing

        # 收集记忆体统计数据
        self.all_memory_stats = []

        # 初始化 DataLoader（用于获取统计信息）
        self.loader = self._init_loader(self.dataset)

    def _init_loader(self, dataset):
        """根据数据集类型初始化 DataLoader

        Args:
            dataset: 数据集名称

        Returns:
            DataLoader 实例
        """
        if dataset == "locomo":
            from sage.data.sources.locomo.dataloader import LocomoDataLoader

            return LocomoDataLoader()
        elif dataset == "conflict_resolution":
            from sage.data.sources.memagentbench.conflict_resolution_loader import (
                ConflictResolutionDataLoader,
            )

            return ConflictResolutionDataLoader()
        elif dataset == "conflict_resolution_v1":
            from sage.data.sources.memagentbench.conflict_resolution_loader_v1 import (
                ConflictResolutionDataLoaderV1,
            )

            return ConflictResolutionDataLoaderV1()
        elif dataset == "conflict_resolution_v2":
            from sage.data.sources.memagentbench.conflict_resolution_loader_v2 import (
                ConflictResolutionDataLoaderV2,
            )

            return ConflictResolutionDataLoaderV2()
        else:
            raise ValueError(f"不支持的数据集: {dataset}")

    def execute(self, data):
        """接收并处理测试结果

        Args:
            data: 来自 PipelineCaller 的纯数据字典
                - None: 未触发测试
                - dict: 测试结果或完成信号
                    - completed: True 表示最后一个包
                    - question_range, answers: 测试数据
        """
        if not data:
            # None 表示未触发测试，直接返回
            return

        # 检查是否包含测试结果或 timing 数据
        # 注意：最后一个包可能同时有 completed=True 和 stage_timings（剩余数据）
        if "answers" in data or "stage_timings" in data:
            # 如果有 answers，收集测试结果
            if "answers" in data:
                test_result = {
                    "test_index": len(self.test_results) + 1,
                    "question_range": data.get("question_range"),
                    "dialogs_inserted_count": data.get("dialogs_inserted"),
                    "answers": data.get("answers", []),
                }
                self.test_results.append(test_result)

            # 收集时间数据（无论是否有 answers）
            if "stage_timings" in data:
                stage_timings = data["stage_timings"]
                print(f"[DEBUG MemorySink] stage_timings keys: {stage_timings.keys()}")

                # 收集插入阶段的时间（插入阶段的值是列表，需要展开后合并）
                if "insert" in stage_timings:
                    insert_timing = stage_timings["insert"]
                    print(f"[DEBUG MemorySink] insert_timing type: {type(insert_timing)}")
                    print(
                        f"[DEBUG MemorySink] insert_timing keys: {insert_timing.keys() if isinstance(insert_timing, dict) else 'not a dict'}"
                    )
                    if isinstance(insert_timing, dict) and insert_timing:
                        first_key = next(iter(insert_timing.keys()))
                        first_value = insert_timing[first_key]
                        print(
                            f"[DEBUG MemorySink] first_key={first_key}, value type={type(first_value)}, is_list={isinstance(first_value, list)}"
                        )
                        if isinstance(first_value, list):
                            print(f"[DEBUG MemorySink] list length={len(first_value)}")

                    # 将插入阶段的列表格式数据展开为单独的timing记录
                    # insert_timing = {"pre_insert_ms": [0.01, 0.01], "memory_insert_ms": [3.2, 3.5], ...}
                    # 需要转换为: [{"pre_insert_ms": 0.01, "memory_insert_ms": 3.2, ...}, ...]
                    if insert_timing:
                        # 获取列表长度（所有字段的列表长度应该相同）
                        first_key = next(iter(insert_timing.keys()))
                        if isinstance(insert_timing[first_key], list):
                            list_len = len(insert_timing[first_key])
                            # 转置：将字典的列表值转换为列表的字典值
                            for i in range(list_len):
                                single_timing = {k: v[i] for k, v in insert_timing.items()}
                                self.all_insert_timings.append(single_timing)
                            print(f"[DEBUG MemorySink] Expanded {list_len} insert timings")
                        else:
                            # 如果不是列表格式，直接添加（向后兼容）
                            self.all_insert_timings.append(insert_timing)
                            print("[DEBUG MemorySink] Added 1 insert timing (not list format)")

                # 收集测试阶段的时间（现在是每次测试的平均值字典）
                if "test" in stage_timings:
                    test_timing = stage_timings["test"]
                    if test_timing:  # 非空字典
                        # test_timing 是一个字典，包含本次测试的平均值
                        # {"pre_retrieval_ms": 0.03, "memory_retrieval_ms": 3.5, ...}
                        self.all_test_timings.append(test_timing)
                        print(
                            "[DEBUG MemorySink] Added 1 test timing (average of multiple questions)"
                        )

            # 收集记忆体统计数据（现在在 stage_timings 内部）
            if "stage_timings" in data and "memory_stats" in data["stage_timings"]:
                memory_stats = data["stage_timings"]["memory_stats"]
                if memory_stats:
                    self.all_memory_stats.append(memory_stats)
                    print("[DEBUG MemorySink] Added 1 memory_stats")

        # 检查是否完成
        print(
            f"\n[DEBUG MemorySink] 收到数据: completed={data.get('completed')}, keys={list(data.keys())}"
        )
        if data.get("completed", False):
            print("[DEBUG MemorySink] completed=True，调用 _save_results")
            self._save_results(data)
        else:
            print("[DEBUG MemorySink] completed=False，不保存")

    def _save_results(self, data):
        """保存最终结果

        Args:
            data: 包含 dataset 和 task_id 的数据
        """
        dataset = data.get("dataset", self.dataset)
        task_id = data.get("task_id", self.task_id)

        # 从 DataLoader 获取数据集统计信息
        dataset_stats = self.loader.get_dataset_statistics(task_id)

        # 分别计算 insert 和 test 的 timing_summary
        insert_timing_summary = self._calculate_timing_summary(self.all_insert_timings)
        test_timing_summary = self._calculate_timing_summary(self.all_test_timings)

        # 合并 timing_summary
        timing_summary = {**insert_timing_summary, **test_timing_summary}

        # 计算 memory_summary（保留原始的 10 条记录）
        memory_summary = self.all_memory_stats  # 不再计算平均值，直接使用列表

        # 构造输出 JSON 结构
        output_data = {
            "experiment_info": {
                "dataset": dataset,
                "task_id": task_id,
            },
            "dataset_statistics": dataset_stats,
            "test_summary": {
                "total_tests": len(self.test_results),
                "test_segments": self.test_segments,
                "test_threshold": f"1/{self.test_segments} of total questions",
            },
            "timing_summary": timing_summary,
            "memory_snapshots": memory_summary,  # 改名为 memory_snapshots，表示每次测试的快照列表
            "test_results": self._format_test_results(self.test_results),
        }

        # 保存为 JSON
        print(f"[DEBUG MemorySink] 准备保存到: {self.output_file}")
        print(f"[DEBUG MemorySink] test_results 数量: {len(self.test_results)}")
        try:
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            print(f"\n✅ 测试结果已保存至: {self.output_file}")
        except Exception as e:
            print(f"[DEBUG MemorySink] 保存失败: {e}")
            import traceback

            traceback.print_exc()

    def _format_test_results(self, test_results):
        """格式化测试结果为通用格式

        Args:
            test_results: 测试结果列表

        Returns:
            list: 格式化后的测试结果
        """
        formatted_results = []

        for test in test_results:
            formatted_test = {
                "test_index": test.get("test_index"),
                "question_range": test.get("question_range"),
                "dialogs_inserted_count": test.get("dialogs_inserted_count"),
                "questions": [],
            }

            # 格式化每个问题的答案
            for answer in test.get("answers", []):
                metadata = answer.get("metadata", {})

                question_data = {
                    "question_index": answer.get("question_index"),
                    "question_text": answer.get("question"),
                    "predicted_answer": answer.get("predicted_answer"),
                }

                # 添加参考答案（如果存在）
                if "answer" in metadata:
                    question_data["reference_answer"] = metadata["answer"]

                # 添加证据信息（如果存在）
                if "evidence" in metadata:
                    question_data["evidence"] = metadata["evidence"]

                # 添加分类信息（如果存在）
                if "category" in metadata:
                    question_data["category"] = metadata["category"]

                # 添加错误信息（如果存在）
                if "error" in answer:
                    question_data["error"] = answer["error"]

                formatted_test["questions"].append(question_data)

            formatted_results.append(formatted_test)

        return formatted_results

    def _calculate_timing_summary(
        self, all_timings: list[dict[str, float]]
    ) -> dict[str, dict[str, float]]:
        """计算各阶段的平均、最大、最小耗时

        Args:
            all_timings: 所有测试的时间数据列表
                - 插入阶段：列表（每个对话的耗时）
                - 检索阶段：float（每个问题的耗时）

        Returns:
            dict: 按阶段组织的统计数据
        """
        if not all_timings:
            return {}

        # 收集所有阶段的时间数据
        stage_data = {}
        for timing in all_timings:
            for stage_name, elapsed_ms in timing.items():
                if stage_name not in stage_data:
                    stage_data[stage_name] = []

                # 处理两种格式
                if isinstance(elapsed_ms, list):
                    # 插入阶段：展开列表，统计所有对话
                    stage_data[stage_name].extend(elapsed_ms)
                else:
                    # 检索阶段：直接添加
                    stage_data[stage_name].append(elapsed_ms)

        # 计算统计数据
        summary = {}
        for stage_name, values in stage_data.items():
            if values:
                summary[stage_name] = {
                    "avg_ms": sum(values) / len(values),
                    "min_ms": min(values),
                    "max_ms": max(values),
                    "count": len(values),
                }

        return summary

    def _calculate_memory_summary(self, all_stats: list[dict]) -> dict:
        """计算存储统计的平均值

        Args:
            all_stats: 所有测试点的记忆体统计数据

        Returns:
            dict: 存储统计汇总
        """
        if not all_stats:
            return {}

        # 提取 storage 字段
        storage_data = []
        for stats in all_stats:
            if "storage" in stats:
                storage_data.append(stats["storage"])

        if not storage_data:
            return {}

        # 计算平均值
        total_entries_sum = sum(s.get("total_entries", 0) for s in storage_data)
        total_size_sum = sum(s.get("total_size_bytes", 0) for s in storage_data)

        avg_entries = total_entries_sum / len(storage_data)
        avg_size = total_size_sum / len(storage_data)

        # 获取最后一个测试点的值作为 final 值
        final_stats = storage_data[-1]

        return {
            "total_entries": {
                "avg": avg_entries,
                "final": final_stats.get("total_entries", 0),
            },
            "total_size_bytes": {
                "avg": avg_size,
                "final": final_stats.get("total_size_bytes", 0),
            },
            "total_size_human": self._format_bytes(final_stats.get("total_size_bytes", 0)),
        }

    def _format_bytes(self, bytes_val: float) -> str:
        """格式化字节数为人类可读格式"""
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} TB"
