from ast import List
from sage.api.operator import WriterFunction,Data
from sage.api.memory import connect,get_default_manager
from typing import Tuple
<<<<<<< HEAD
=======
import ray

@ray.remote
>>>>>>> 0dc3395c4ba3171805ebb45c53b0f724de0fcbe0
class LongTimeWriter(WriterFunction):
    def __init__(self,config):
        super().__init__()
        self.config = config["writer"]
<<<<<<< HEAD
        self.memory_manager=get_default_manager()
        self.ltm=connect(self.memory_manager,"short_term_memory")
=======
        self.memory_manager=config["memory_manager"]
>>>>>>> 0dc3395c4ba3171805ebb45c53b0f724de0fcbe0

    def execute(self, data:Data[Tuple[str,str]]) -> Data[Tuple[str,str]]:
        try:
            query,answer=data.data
<<<<<<< HEAD
            self.ltm.store(query+answer)
=======
            ref=self.memory_manager.store.remote(query+answer,"long_term_memory")
            ray.get(ref)

>>>>>>> 0dc3395c4ba3171805ebb45c53b0f724de0fcbe0
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