import json
import os

from sage.benchmark.benchmark_memory.experiment.utils.path_finder import get_project_root
from sage.benchmark.benchmark_memory.experiment.utils.time_geter import get_time_filename
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

        # 获取项目根目录
        project_root = get_project_root()

        # 创建时间戳目录结构
        time_str = get_time_filename()
        self.output_dir = os.path.join(
            project_root, f".sage/benchmarks/benchmark_memory/{self.dataset}/{time_str}"
        )
        os.makedirs(self.output_dir, exist_ok=True)

        # 设置输出文件路径
        self.output_file = os.path.join(self.output_dir, f"{self.task_id}.json")
        print(f"💾 输出文件: {self.output_file}")

        # 收集所有测试结果
        self.test_results = []

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
            from sage.data.locomo.dataloader import LocomoDataLoader

            return LocomoDataLoader()
        else:
            raise ValueError(f"不支持的数据集: {dataset}")

    def execute(self, data):
        """接收并处理测试结果

        Args:
            data: 来自 PipelineCaller 的数据
                - None: 未触发测试
                - dict: 测试结果或完成信号
                    - completed: True 表示最后一个包
                    - question_range, answers: 测试数据
        """
        if not data:
            # None 表示未触发测试，直接返回
            return

        # 提取 payload（如果是 PipelineRequest）
        payload = data.payload if hasattr(data, "payload") else data

        # 检查是否包含测试结果
        if "answers" in payload:
            # 收集测试结果
            test_result = {
                "test_index": len(self.test_results) + 1,
                "question_range": payload.get("question_range"),
                "dialogs_inserted_count": payload.get("dialogs_inserted"),
                "answers": payload.get("answers", []),
            }
            self.test_results.append(test_result)
            print(f"[DEBUG] MemorySink 收集第 {test_result['test_index']} 次测试结果")

        # 检查是否完成
        if payload.get("completed", False):
            print("[DEBUG] MemorySink 接收到完成信号，准备保存结果...")
            self._save_results(payload)

    def _save_results(self, payload):
        """保存最终结果

        Args:
            payload: 包含 dataset 和 task_id 的数据
        """
        dataset = payload.get("dataset", self.dataset)
        task_id = payload.get("task_id", self.task_id)

        # 从 DataLoader 获取数据集统计信息
        dataset_stats = self.loader.get_dataset_statistics(task_id)

        # 构造输出 JSON 结构
        output_data = {
            "experiment_info": {
                "dataset": dataset,
                "task_id": task_id,
            },
            "dataset_statistics": dataset_stats,
            "test_summary": {
                "total_tests": len(self.test_results),
                "test_threshold": "1/10 of total questions",
            },
            "test_results": self._format_test_results(self.test_results),
        }

        # 保存为 JSON
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"\n✅ 测试结果已保存至: {self.output_file}")

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
