from sage.api.operator import SinkFunction
from sage.api.operator import Data
from typing import Tuple
class TerminalSink(SinkFunction):

    def __init__(self,config):
        super().__init__()
        self.config=config["sink"]

    def execute(self, data:Data[Tuple[str,str]]):
        question,answer=data.data

        print(f"\033[96m[Q] Question :{question}\033[0m")  

        print(f"\033[92m[A] Answer :{answer}\033[0m")  