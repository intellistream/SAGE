import os

from sage.common.core import SinkFunction
from sage.benchmark.benchmark_memory.experiment.utils.path_finder import get_project_root


class MemorySink(SinkFunction):
    """将接收到的对话数据保存到文本文件的Sink"""

    def __init__(self, dataset_name, output_name):
        """初始化LocomoSink
        
        Args:
            dataset_name: 数据集名称（用作子目录）
            output_name: 输出文件名（不含扩展名）
        """
        # 获取项目根目录
        project_root = get_project_root()
        
        # 创建输出目录
        self.output_dir = os.path.join(project_root, f".sage/benchmarks/benchmark_memory/{dataset_name}")
        os.makedirs(self.output_dir, exist_ok=True)

        # 设置输出文件路径
        self.output_file = os.path.join(self.output_dir, f"{output_name}.txt")
        print(f"💾 输出文件: {self.output_file}")

    def execute(self, data):
        """处理并保存对话数据
        
        Args:
            data: 包含以下键的字典或 PipelineRequest 对象
                - task_id: 样本ID
                - session_id: 会话ID
                - dialog_id: 对话索引
                - dialogs: 对话列表，每个元素包含 speaker, text
        """
        # # 提取 payload（如果是 PipelineRequest）
        # payload = data.payload if hasattr(data, "payload") else data
        
        # session_id = payload.get("session_id")
        # dialog_id = payload.get("dialog_id")
        # dialogs = payload.get("dialogs", [])
        
        # # 打开文件追加内容
        # with open(self.output_file, "a", encoding="utf-8") as f:
        #     # 写入分隔符
        #     f.write("======\n")
            
        #     # 写入session和dialog信息
        #     if len(dialogs) == 1:
        #         f.write(f"session {session_id}\n")
        #         f.write(f"dialog {dialog_id}\n")
        #     else:
        #         f.write(f"session {session_id}\n")
        #         f.write(f"dialog {dialog_id}-{dialog_id + len(dialogs) - 1}\n")
            
        #     # 写入每个对话
        #     for dialog in dialogs:
        #         speaker = dialog.get("speaker", "Unknown")
        #         text = dialog.get("text", "")
        #         f.write(f'"{speaker}": "{text}"\n')
        
        # print(f"📝 保存数据: session_id={session_id}, dialog_idx={dialog_id}, dialog_count={len(dialogs)}")