from sage_core.api.tuple import Data
from sage_core.api.base_function import BaseFunction
from sage_utils.custom_logger import CustomLogger
from typing import Tuple, List, Union, Type




class TerminalSink(BaseFunction):
    
    def __init__(self, config:dict,*,session_folder:str = None, **kwargs):
        self.logger = CustomLogger(
            object_name=f"DenseRetriever_Function",
            log_level="DEBUG",
            session_folder=session_folder,
            console_output=False,
            file_output=True
        )
        self.config=config

    def execute(self, data:Data[Tuple[str,str]]):
        question,answer=data.data

        print(f"\033[96m[Q] Question :{question}\033[0m")  

        print(f"\033[92m[A] Answer :{answer}\033[0m")

class RetriveSink(BaseFunction):

    def __init__(self, config:dict,*,session_folder:str = None, **kwargs):
        self.logger = CustomLogger(
            object_name=f"DenseRetriever_Function",
            log_level="DEBUG",
            session_folder=session_folder,
            console_output=False,
            file_output=True
        )
        self.config=config
    def execute(self, data:Data[Tuple[str, List[str]]]):
        question,chunks=data.data

        print(f"\033[96m[Q] Question :{question}\033[0m")

        print(f"\033[92m[A] Chunks :{chunks}\033[0m")


class FileSink(BaseFunction):
    def __init__(self, config:dict,*,session_folder:str = None, **kwargs):
        self.file_path =  config.get("file_path","qa_output.txt")
        self.logger = CustomLogger(
            object_name=f"FileSink_Function_{self.file_path}",
            log_level="DEBUG",
            session_folder=session_folder,
            console_output=False,
            file_output=True
        )
        self.config = config

        # 创建或清空文件
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write("=== QA Output Log ===\n")

    def execute(self, data: Data[Tuple[str, str]]):
        question, answer = data.data

        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write("[Q] Question: " + question + "\n")
            f.write("[A] Answer  : " + answer + "\n")
            f.write("-" * 40 + "\n")


class MemWriteSink(BaseFunction):
    def __init__(self, config):
        super().__init__()
        self.config = config
        # 从配置获取文件路径，默认为 'mem_output.txt'
        self.file_path = self.config.get("file_path", "mem_output.txt")
        self.counter = 0  # 全局字符串计数器

        # 初始化文件并写入标题
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write("=== Memory String Log ===\n")

    def execute(self, data: Data[Union[str, List[str], Tuple[str, str]]]):
        # 解析输入数据为字符串列表
        input_data = data.data
        strings = self._parse_input(input_data)

        # 追加写入文件
        with open(self.file_path, "a", encoding="utf-8") as f:
            for s in strings:
                self.counter += 1
                f.write(f"[{self.counter}] {s}\n")
            f.write("-" * 40 + "\n")  # 写入分隔线

    def _parse_input(self, input_data):
        """将不同格式的输入统一解析为字符串列表"""
        if isinstance(input_data, str):
            return [input_data]
        elif isinstance(input_data, list):
            return input_data
        elif isinstance(input_data, tuple):
            # 展平元组中的所有字符串
            return [item for item in input_data if isinstance(item, str)]
        else:
            # 其他类型转换为字符串
            return [str(input_data)]