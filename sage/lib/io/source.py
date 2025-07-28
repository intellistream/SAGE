
from sage.core.function.source_function import SourceFunction
from pathlib import Path

class FileSource(SourceFunction):
    """
    A source rag that reads a file line by line and returns each line as a string.

    Input: None (reads directly from a file located at the specified `data_path`).
    Output: A Data object containing the next line of the file content.

    Attributes:
        config: Configuration dictionary containing various settings, including the file path.
        data_path: The path to the file to be read.
        file_pos: Tracks the current position in the file for sequential reading.
    """

    def __init__(self, config: dict = None,  **kwargs):
        super().__init__(**kwargs)
        """
        Initializes the FileSource with the provided configuration and sets the data path for the file.

        :param config: Configuration dictionary containing source settings, including `data_path`.
        """
        self.config = config
        self.data_path = self.resolve_data_path(config["data_path"])  # → project_root/data/sample/question.txt
        self.file_pos = 0  # Track the file read position

    def resolve_data_path(self,path: str | Path) -> Path:
        """
        传入相对路径则返回相对于项目根目录的绝对路径（默认假设项目根目录含有 'data/' 子目录），
        传入绝对路径则直接返回。
        """
        import os
        p = Path(path)
        if p.is_absolute():
            return p
        # 假设调用时 cwd 是项目的某个子目录，项目根为“当前工作目录的祖父目录”
        project_root = Path(os.getcwd()).resolve()
        return project_root  / p
    


    def execute(self) -> str:
        """
        Reads the next line from the file and returns it as a string.

        :return: A Data object containing the next line of the file content.
        """
        try:
            while True:
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    f.seek(self.file_pos)  # Move to the last read position
                    line = f.readline()
                    self.file_pos = f.tell()  # Update the new position
                    if line:
                        self.logger.info(f"\033[32m[ {self.__class__.__name__}]: Read query: {line.strip()}\033[0m ")
                        return line.strip()  # Return non-empty lines
                    else:
                        self.logger.info(f"\033[33m[ {self.__class__.__name__}]: Reached end of file, maintaining position.\033[0m ")
                        # Reset position if end of file is reached (optional)
                        continue
        except FileNotFoundError:
            self.logger.error(f"File not found: {self.data_path}")
        except Exception as e:
            self.logger.error(f"Error reading file '{self.data_path}': {e}")
