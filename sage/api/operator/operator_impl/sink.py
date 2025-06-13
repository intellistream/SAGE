from sage.api.operator import SinkFunction
from sage.api.operator import Data
from typing import Tuple, List


class TerminalSink(SinkFunction):

    def __init__(self,config):
        super().__init__()
        self.config=config["sink"]

    def execute(self, data:Data[Tuple[str,str]]):
        question,answer=data.data

        print(f"\033[96m[Q] Question :{question}\033[0m")  

        print(f"\033[92m[A] Answer :{answer}\033[0m")

class RetriveSink(SinkFunction):
    def __init__(self,config):
        super().__init__()
        self.config=config["sink"]
    def execute(self, data:Data[Tuple[str, List[str]]]):
        question,chunks=data.data

        print(f"\033[96m[Q] Question :{question}\033[0m")

        print(f"\033[92m[A] Chunks :{chunks}\033[0m")


class FileSink(SinkFunction):
    def __init__(self, config):
        super().__init__()
        self.config = config["sink"]
        self.file_path =  "output.txt"

        # 创建或清空文件
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write("=== QA Output Log ===\n")

    def execute(self, data: Data[Tuple[str, str]]):
        question, answer = data.data

        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write("[Q] Question: " + question + "\n")
            f.write("[A] Answer  : " + answer + "\n")
            f.write("-" * 40 + "\n")
