# sage/api/operator/sink_operator.py

from typing import Any, List
from sage.api.operator.base import Operator


class SinkOperator(Operator):
    """
    将用户编写的 Function 包装为 Sink 算子，
    对流中每条记录调用 Function.process，
    并且不向下游继续传递任何数据。
    """

    def run(self, record: Any) -> List[Any]:
        """
        对单条记录执行 Function.process，将结果落盘或发送外部系统。
        :param record: 上游传入的数据元素
        :return: 始终返回空列表，表示没有下游输出
        """
        # 调用底层业务逻辑（写入文件、数据库等）
        self.fn.process(record)
        # 不再有下游数据
        return []
