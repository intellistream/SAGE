from sage.core.api.function.sink_function import SinkFunction
from typing import Tuple, List, Union, Type, Any
import os



class TerminalSink(SinkFunction):
    
    def __init__(self, config: dict = None,  **kwargs):
        super().__init__(**kwargs)
        self.config=config

    def execute(self, data:Tuple[str,str]):
        question,answer=data

        self.logger.info(f"Executing {self.__class__.__name__} [Q] Question :{question}")
        self.logger.info(f"Executing {self.__class__.__name__} [A] Answer :{answer}")
        print(f"[{self.__class__.__name__}]: \033[96m[Q] Question :{question}\033[0m")

        print(f"[{self.__class__.__name__}]: \033[92m[A] Answer :{answer}\033[0m")

class RetriveSink(SinkFunction):

    def __init__(self, config: dict = None,  **kwargs):
        super().__init__(**kwargs)
        self.config=config
    def execute(self, data:Tuple[str, List[str]]):
        question,chunks=data

        print(f"\033[96m[Q] Question :{question}\033[0m")

        print(f"\033[92m[A] Chunks :{chunks}\033[0m")


class FileSink(SinkFunction):
    def __init__(self, config: dict = None, **kwargs):
        super().__init__(**kwargs)
        
        file_path = config.get("file_path", "qa_output.txt") if config else "qa_output.txt"
        self.config = config
        
        # 判断路径类型并处理
        if os.path.isabs(file_path):
            # 绝对路径：直接使用
            self.file_path = file_path
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        else:
            # 相对路径：添加output前缀
            os.makedirs("output", exist_ok=True)
            self.file_path = os.path.join("output", file_path)

        # 创建或清空文件
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write("=== QA Output Log ===\n")

    def execute(self, data: Tuple[str, str]):
        # 添加详细的日志记录
        self.logger.info(f"FileSink.execute called with data: {data}")
        self.logger.info(f"Data type: {type(data)}")
        
        if not isinstance(data, tuple) or len(data) != 2:
            self.logger.error(f"FileSink expected tuple of 2 elements, got: {data}")
            return
            
        question, answer = data

        # 确保数据是字符串类型
        if not isinstance(question, str) or not isinstance(answer, str):
            self.logger.error(f"FileSink expected string tuple, got question: {type(question)}, answer: {type(answer)}")
            return

        self.logger.info(f"Writing QA pair to file {self.file_path}")
        self.logger.info(f"Question: {question[:100]}..." if len(question) > 100 else f"Question: {question}")
        self.logger.info(f"Answer: {answer[:100]}..." if len(answer) > 100 else f"Answer: {answer}")

        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write("[Q] Question: " + question + "\n")
            f.write("[A] Answer  : " + answer + "\n")
            f.write("-" * 40 + "\n")
        self.logger.info(f"Data successfully written to file: {self.file_path}")

class MemWriteSink(SinkFunction):
    def __init__(self, config: dict = None,  **kwargs):
        super().__init__(**kwargs)
        self.config = config
        # 从配置获取文件路径，默认为 'mem_output.txt'
        self.file_path = self.config.get("file_path", "mem_output.txt")
        self.counter = 0  # 全局字符串计数器

        # 初始化文件并写入标题
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write("=== Memory String Log ===\n")

    def execute(self, data: Union[str, List[str], Tuple[str, str]]):
        # 解析输入数据为字符串列表
        input_data = data
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

class PrintSink(SinkFunction):
    """
    简洁的打印汇聚函数 - 提供便捷的datastream.print()支持
    
    支持多种数据格式的智能打印，自动检测数据类型并格式化输出
    """
    
    def __init__(self, prefix: str = "", separator: str = " | ", colored: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.prefix = prefix
        self.separator = separator
        self.colored = colored
        
    def execute(self, data: Any) -> None:
        """
        智能打印数据，支持多种数据格式
        
        Args:
            data: 任意类型的输入数据
        """
        formatted_output = self._format_data(data)
        
        if self.prefix:
            output = f"{self.prefix}{self.separator}{formatted_output}"
        else:
            output = formatted_output
            
        print(output)
        
        # 记录日志
        self.logger.info(f"PrintSink output: {formatted_output}")
    
    def _format_data(self, data: Any) -> str:
        """格式化数据为可读字符串"""
        
        # 处理问答对 (question, answer)
        if isinstance(data, tuple) and len(data) == 2:
            if all(isinstance(item, str) for item in data):
                question, answer = data
                if self.colored:
                    return f"\033[96m[Q] {question}\033[0m\n\033[92m[A] {answer}\033[0m"
                else:
                    return f"[Q] {question}\n[A] {answer}"
        
        # 处理检索结果 (question, chunks)
        if isinstance(data, tuple) and len(data) == 2:
            question, chunks = data
            if isinstance(question, str) and isinstance(chunks, list):
                if self.colored:
                    chunks_str = "\n".join([f"  - {chunk}" for chunk in chunks])
                    return f"\033[96m[Q] {question}\033[0m\n\033[93m[Chunks]\033[0m\n{chunks_str}"
                else:
                    chunks_str = "\n".join([f"  - {chunk}" for chunk in chunks])
                    return f"[Q] {question}\n[Chunks]\n{chunks_str}"
        
        # 处理字符串列表
        if isinstance(data, list):
            if all(isinstance(item, str) for item in data):
                return "\n".join([f"  - {item}" for item in data])
            else:
                return "\n".join([f"  - {str(item)}" for item in data])
        
        # 处理字典
        if isinstance(data, dict):
            items = []
            for key, value in data.items():
                if self.colored:
                    items.append(f"\033[94m{key}\033[0m: {value}")
                else:
                    items.append(f"{key}: {value}")
            return "\n".join(items)
        
        # 处理其他类型，直接转换为字符串
        return str(data)