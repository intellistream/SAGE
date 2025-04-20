from sage.api.operator import WriterFunction,Data
from sage.api.memory import connect,get_default_manager
from typing import Tuple
import ray

@ray.remote
class SimpleWriter(WriterFunction):
    def __init__(self):
        super().__init__()
        self.memory_manager=get_default_manager()
        self.stm=connect(self.memory_manager,"short_term_memory")

    def execute(self, data:Data[Tuple[str,str]]) -> Data[Tuple[str,str]]:
        query,answer=data.data
        self.stm.store(query+answer)

        return Data((query,answer))
    