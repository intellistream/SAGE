"""后检索处理模块 - 在记忆检索后的后处理（可选）

对于短期记忆（STM），通常不需要后处理。
此模块保留用于未来扩展（如结果过滤、格式化、排序等）。
"""

from sage.common.core import MapFunction


class PostRetrieval(MapFunction):
    """记忆检索后的后处理算子
    
    职责：
    - 结果过滤
    - 格式化
    - 排序和去重
    
    注：短期记忆通常不需要此步骤
    """

    def __init__(self):
        super().__init__()

    def execute(self, data):
        """执行后处理
        
        Args:
            data: PipelineRequest 对象或检索到的记忆数据
        
        Returns:
            处理后的数据（默认直接透传）
        """
        if not data:
            return None

        # 默认直接透传，不做任何处理
        return data
