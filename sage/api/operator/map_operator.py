# sage/api/operator/map_operator.py

from typing import Any, List
from sage.api.operator.base import Operator


class MapOperator(Operator):
    """
    将用户编写的 Function 包装为 Map 算子，
    对流中每条记录调用 Function.process，
    并统一输出为列表形式。
    """

    def run(self, record: Any) -> List[Any]:
        """
        对单条记录执行 Function.process。
        :param record: 上游传入的数据元素
        :return: 下游记录列表
        """
        # 调用底层业务逻辑
        result = self.fn.process(record)
        # 统一成列表输出
        if isinstance(result, list):
            return result
        return [result]
