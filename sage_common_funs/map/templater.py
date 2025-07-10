from sage_core.api.tuple import Data
from sage_core.api.base_function import BaseFunction
from sage_utils.custom_logger import CustomLogger
from typing import List
from sage_common_funs.utils.template import AI_Template
from uuid import uuid4
import time

# 接受上游原始问题，生成一个AI_Template对象，包含问题、提示和答案等字段，发给下游。
class Templater(BaseFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sequence = 0

    def execute(self, data:Data[str]) -> Data[AI_Template]:
        template = AI_Template(
            sequence=self.sequence,
            raw_question=data.data,
        )
        self.sequence += 1
        return Data(template)