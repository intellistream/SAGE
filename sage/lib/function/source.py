from sage.core.operator.base_operator import Data
from sage.api.base_function import BaseFunction
from typing import Tuple
from sage.utils.custom_logger import CustomLogger
from sage.utils.data_loader import resolve_data_path


class FileSource(BaseFunction):
    """
    A source function that reads a file line by line and returns each line as a string.

    Input: None (reads directly from a file located at the specified `data_path`).
    Output: A Data object containing the next line of the file content.

    Attributes:
        config: Configuration dictionary containing various settings, including the file path.
        data_path: The path to the file to be read.
        file_pos: Tracks the current position in the file for sequential reading.
    """

    def __init__(self, config:dict,*,session_folder:str = None, **kwargs):
        """
        Initializes the FileSource with the provided configuration and sets the data path for the file.

        :param config: Configuration dictionary containing source settings, including `data_path`.
        """
        self.logger = CustomLogger(
            object_name=f"FileSource_Function",
            log_level="DEBUG",
            session_folder=session_folder,
            console_output=False,
            file_output=True
        )
        self.config = config
        # self.data_path = self.config["data_path"]
        self.data_path = resolve_data_path(config["data_path"])  # → project_root/data/sample/question.txt
        self.file_pos = 0  # Track the file read position

    def execute(self) -> Data[str]:
        """
        Reads the next line from the file and returns it as a string.

        :return: A Data object containing the next line of the file content.
        """
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                f.seek(self.file_pos)  # Move to the last read position
                line = f.readline()
                self.file_pos = f.tell()  # Update the new position
                if line:
                    self.logger.info(f"\033[32m[ {self.__class__.__name__}]: Read query: {line.strip()}\033[0m ")
                    return Data(line.strip())  # Return non-empty lines
                else:
                    # Reset position if end of file is reached (optional)
                    # self.file_pos = 0
                    return Data("")  # Return empty Data at EOF
        except FileNotFoundError:
            self.logger.error(f"File not found: {self.data_path}")
        except Exception as e:
            self.logger.error(f"Error reading file '{self.data_path}': {e}")
        return Data("")
