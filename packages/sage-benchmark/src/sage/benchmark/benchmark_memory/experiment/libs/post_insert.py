"""后插入处理模块 - 在记忆插入后的后处理（可选）

对于短期记忆（STM），通常不需要后处理。
此模块保留用于未来扩展（如日志记录、统计分析等）。
"""

from sage.common.core import MapFunction


class PostInsert(MapFunction):
    """记忆插入后的后处理算子

    职责：
    - 日志记录
    - 统计分析
    - 触发后续操作

    注：短期记忆通常不需要此步骤
    """

    def __init__(self, config):
        """初始化 PostInsert

        Args:
            config: RuntimeConfig 对象，从中获取 operators.post_insert.action
        """
        super().__init__()
        self.action = config.get("operators.post_insert.action", "none")

    def execute(self, data):
        """执行后处理

        Args:
            data: 由 MemoryInsert 输出的数据，格式：
                {
                    "memory_entries": [条目1, 条目2, ...],  # 已插入但未清空的队列
                    ...其他字段
                }

        Returns:
            处理后的数据（清空队列后透传）
        """
        if not data:
            return None

        # 清空 memory_entries 队列（插入已完成）
        if "memory_entries" in data:
            data["memory_entries"] = []

        # 根据 action 模式执行不同操作（如果需要）
        if self.action == "none":
            # 不执行任何操作，直接透传
            return data
        elif self.action == "log":
            # 日志记录
            self._log_data(data)
            return data
        elif self.action == "stats":
            # 统计分析
            self._analyze_stats(data)
            return data
        else:
            # 未知操作模式，透传
            return data

    def _log_data(self, data: list[dict]):
        """日志记录（占位方法）

        Args:
            data: 记忆条目列表
        """
        print(f"[PostInsert] 插入了 {len(data)} 个记忆条目")
        for i, entry in enumerate(data, 1):
            if "refactor" in entry:
                print(f"  {i}. 三元组模式: {entry.get('refactor', '')[:50]}...")
            elif "data" in entry:
                print(f"  {i}. 传统模式: {type(entry['data'])}")
            else:
                print(f"  {i}. 未知格式: {list(entry.keys())}")

    def _analyze_stats(self, data: list[dict]):
        """统计分析（占位方法）

        Args:
            data: 记忆条目列表
        """
        triple_count = sum(1 for entry in data if "triple" in entry)
        traditional_count = sum(1 for entry in data if "data" in entry)
        print(f"[PostInsert] 统计: 总计 {len(data)} 个条目")
        print(f"  - 三元组模式: {triple_count} 个")
        print(f"  - 传统模式: {traditional_count} 个")
        return data
