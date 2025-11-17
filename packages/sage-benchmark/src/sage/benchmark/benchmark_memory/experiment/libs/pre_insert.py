

"""预插入处理模块 - 在记忆插入前的预处理（可选）

对于短期记忆（STM），通常不需要预处理，直接插入即可。
此模块保留用于未来扩展（如数据验证、格式转换等）。
"""

from sage.common.core import MapFunction


class PreInsert(MapFunction):
    """记忆插入前的预处理算子
    
    职责：
    - 数据验证
    - 格式转换
    - 过滤无效对话
    
    注：短期记忆通常不需要此步骤
    """

    def __init__(self):
        super().__init__()

    def execute(self, data):
        """执行预处理
        
        Args:
            data: PipelineRequest 对象或原始对话数据
        
        Returns:
            处理后的数据（默认直接透传）
        """
        if not data:
            return None

        # 默认直接透传，不做任何处理
        return data
