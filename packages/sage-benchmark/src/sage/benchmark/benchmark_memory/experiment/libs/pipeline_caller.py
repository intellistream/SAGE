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
        
        # 打印【Source】部分
        print(f"\n{'=' * 60}")
        print(f"【Memory Source】（{self.progress_bar.current}/{self.total_dialogs}）")
        print(f">> Session：{session_id}，Dialog {dialog_id}", end="")
        if len(dialogs) == 2:
            print(f" & {dialog_id + 1}")
        else:
            print()

        for i, dialog in enumerate(dialogs):
            speaker = dialog.get("speaker", "Unknown")
            text = dialog.get("text", "")
            print(f">> Dialog {dialog_id + i}：{speaker}")
            print(f">> {text}")

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

        # 有可见问题，调用记忆测试服务
        test_data = {
            "task_id": task_id,
            "session_id": session_id,
            "dialog_id": dialog_id,
            "dialogs": dialogs,
        }

        # 调用记忆测试服务（阻塞等待）
        result = self.call_service(
            "memory_test_service",
            test_data,
            method="process",
            timeout=300.0,
        )

        print(f"{'=' * 60}\n")
        
        # 如果处理完成，关闭进度条
        if self.progress_bar.current >= self.total_dialogs:
            self.progress_bar.close()

        # 提取 payload（如果返回的是 PipelineRequest）
        if hasattr(result, "payload"):
            return result.payload
        return result
