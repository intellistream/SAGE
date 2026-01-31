"""
Workload 4 - Utility Mappers

临时工具类，用于测试单源 pipeline
"""

from sage.common.core.functions import MapFunction

try:
    from .models import JoinedEvent, QueryEvent
except ImportError:
    from models import JoinedEvent, QueryEvent


class QueryToJoinedMapper(MapFunction):
    """
    将 QueryEvent 转换为 JoinedEvent（单源测试用）

    这个 Mapper 类直接继承自 MapFunction，避免 lambda 序列化问题。
    只捕获简单的 int 参数，不引用外部 self 对象。
    """

    def __init__(self, join_parallelism: int = 8):
        """
        Args:
            join_parallelism: Join 并行度（用于填充 JoinedEvent）
        """
        super().__init__()
        self.join_parallelism = join_parallelism

    def execute(self, query: QueryEvent) -> JoinedEvent:
        """
        将 QueryEvent 转换为 JoinedEvent

        Args:
            query: 查询事件

        Returns:
            包含 query 信息的 JoinedEvent（document 字段使用占位符）
        """
        return JoinedEvent(
            joined_id=query.query_id,
            query_id=query.query_id,
            query_text=query.query_text,
            query_vector=query.query_vector,
            query_type=query.query_type,
            category=query.category,
            timestamp=query.timestamp,
            # Document fields 使用占位符
            doc_id="mock_doc",
            doc_text="mock document for single-source testing",
            doc_vector=query.query_vector,  # 复用 query vector
            join_parallelism=self.join_parallelism,
        )
