
from sage_core.api.base_function import BaseFunction
from sage_utils.custom_logger import CustomLogger
from typing import Tuple, List, Union, Type
from sage_common_funs.utils.template import AI_Template
import os



class ChatTerminalSink(BaseFunction):
    
    def __init__(self, *args,  **kwargs):
        super().__init__(**kwargs)

    def execute(self, data:AI_Template):
        input_template=data

        print(f"\033[96m[Q] Question :{input_template.raw_question}\033[0m")  

        print(f"\033[92m[A] Answer :{input_template.response}\033[0m")


class ChatFileSink(BaseFunction):
    def __init__(self, config: dict = None,*args,  **kwargs):
        super().__init__(**kwargs)
        os.makedirs("output", exist_ok=True)
        self.file_path = os.path.join("output", config.get("file_path", "qa_output.txt"))
        self.config = config

        # 创建或清空文件
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write("=== QA Output Log ===\n")

    def execute(self, data: AI_Template):
        input_template=data

        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write("[Q] Question: " + input_template.raw_question + "\n")
            f.write("[A] Answer  : " + input_template.response + "\n")
            f.write("-" * 40 + "\n")
        self.logger.debug(f"Data written to file: {self.file_path}")
