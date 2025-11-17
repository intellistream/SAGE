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

    def __init__(self):
        super().__init__()

    def execute(self, data):
        """执行后处理
        
        Args:
            data: PipelineRequest 对象或已插入记忆的数据
        
        Returns:
            处理后的数据（默认直接透传）
        """
        if not data:
            return None

        # 默认直接透传，不做任何处理
        return data
