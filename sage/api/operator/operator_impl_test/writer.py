from ast import List
from sage.api.operator import WriterFunction,Data
from sage.api.memory import connect,get_default_manager
from typing import Tuple
import ray



class LongTimeWriter(WriterFunction):
    def __init__(self,config):
        super().__init__()
        self.config = config["writer"]
        # self.memory_manager=get_default_manager()

        self.memory_manager=config["memory_manager"]
        self.ltm=connect(self.memory_manager,"short_term_memory")

    def execute(self, data:Data[Tuple[str,str]]) -> Data[Tuple[str,str]]:
        try:
            query,answer=data.data
            ref=self.memory_manager.store.remote(query+answer,"long_term_memory")
            ray.get(ref)
        except Exception as e:
            self.logger.error(f"{e} when WriterFuction")


        return Data((query,answer))

class MemWriter(WriterFunction):
    def __init__(self,config):
        super().__init__()
        self.config = config["writer"]
        self.memory_manager=get_default_manager()
        self.ltm=connect(self.memory_manager,"long_term_memory")

    def execute(self, data:Data[list[str]])-> Data[list[str]]:
        try:
            chunks=data.data
            for chunk in chunks:
                self.ltm.store(chunk)
        except Exception as e:
            self.logger.error(f"{e} when WriterFuction")

        return Data(chunks)