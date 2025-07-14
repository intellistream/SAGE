
from sage_core.function.map_function import MapFunction
from sage_utils.custom_logger import CustomLogger
from typing import List
from sage_common_funs.utils.template import AI_Template
from uuid import uuid4
import time

# 接受上游原始问题，生成一个AI_Template对象，包含问题、提示和答案等字段，发给下游。
class Templater(MapFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sequence = 0

    def execute(self, data:str) -> AI_Template:
        template = AI_Template(
            sequence=self.sequence,
            raw_question=data,
        )
        self.sequence += 1
        return template