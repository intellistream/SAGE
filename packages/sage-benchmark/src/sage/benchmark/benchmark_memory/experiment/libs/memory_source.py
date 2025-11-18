"""记忆实验数据源 - 支持多数据集的统一接口"""

from sage.common.core import BatchFunction
from sage.data.locomo.dataloader import LocomoDataLoader


class MemorySource(BatchFunction):
    """
    从多种数据集中逐个读取对话轮次的Source
    
    支持的数据集：
    - locomo: 长轮对话数据集
    
    输出格式：
    {
        "task_id": str,        # 任务/样本ID
        "session_id": int,     # 会话ID
        "dialog_id": int,      # 对话索引
        "dialogs": [           # 对话列表
            {
                "speaker": str,         # 说话者
                "text": str,           # 对话内容
            },
            ...
        ],
        "dialog_len": int      # 对话列表长度
    }
    """

    def __init__(self, dataset: str, task_id: str):
        """初始化数据源
        
        Args:
            dataset: 数据集名称 ('locomo', 等)
            task_id: 任务/样本ID
        """
        super().__init__()
        self.dataset = dataset
        self.task_id = task_id
        
        # 根据数据集类型初始化加载器
        self.loader = self._init_loader(dataset)
        
        # 初始化数据集特定的状态
        if dataset == "locomo":
            self._init_locomo()
        else:
            raise ValueError(f"不支持的数据集: {dataset}")

    def _init_loader(self, dataset: str):
        """根据数据集类型初始化加载器"""
        if dataset == "locomo":
            return LocomoDataLoader()
        else:
            raise ValueError(f"不支持的数据集: {dataset}")

    def _init_locomo(self):
        """初始化 Locomo 数据集"""
        # 获取所有session和对话轮数
        self.turns = self.loader.get_turn(self.task_id)
        
        # 统计总的dialog数量
        self.total_dialogs = sum((max_dialog_idx + 1) for _, max_dialog_idx in self.turns)
        
        print(f"📊 样本 {self.task_id} 统计信息:")
        print(f"   - 总会话数: {len(self.turns)}")
        print(f"   - 总对话数: {self.total_dialogs}")
        for idx, (session_id, max_dialog_idx) in enumerate(self.turns):
            dialog_count = max_dialog_idx + 1
            print(
                f"   - 会话 {idx + 1} (session_id={session_id}): {dialog_count} 个对话 (max_dialog_idx={max_dialog_idx})"
            )
        
        # 初始化指针
        self.session_idx = 0  # 当前session在turns列表中的索引
        self.dialog_ptr = 0  # 当前dialog指针（偶数）

    def execute(self):
        """执行数据读取"""
        if self.dataset == "locomo":
            result = self._execute_locomo()
        else:
            raise ValueError(f"不支持的数据集: {self.dataset}")
        
        return result

    def _execute_locomo(self):
        """执行 Locomo 数据集的读取"""
        # 检查是否已经遍历完所有session
        if self.session_idx >= len(self.turns):
            print(f"🏁 MemorySource 已完成：所有 {len(self.turns)} 个会话已处理完毕")
            return None

        # 获取当前session信息
        session_id, max_dialog_idx = self.turns[self.session_idx]

        # 检查当前session是否已经遍历完
        if self.dialog_ptr > max_dialog_idx:
            # 移动到下一个session
            self.session_idx += 1
            self.dialog_ptr = 0

            # 检查是否还有更多session
            if self.session_idx >= len(self.turns):
                return None

            # 更新到新session的信息
            session_id, max_dialog_idx = self.turns[self.session_idx]

        # 获取当前对话
        try:
            dialogs = self.loader.get_dialog(
                self.task_id, session_x=session_id, dialog_y=self.dialog_ptr
            )

            # 准备返回数据
            result = {
                "task_id": self.task_id,
                "session_id": session_id,
                "dialog_id": self.dialog_ptr,
                "dialogs": dialogs,
                "dialog_len": len(dialogs),
            }

            # 移动指针到下一组对话（每次+2，因为一组对话包含问答两轮）
            self.dialog_ptr += 2

            return result

        except Exception as e:
            print(f"❌ 获取对话时出错 session {session_id}, dialog {self.dialog_ptr}: {e}")
            import traceback

            traceback.print_exc()
            # 出错时移动到下一个dialog，返回None让下次execute()调用处理
            self.dialog_ptr += 2
            return None
