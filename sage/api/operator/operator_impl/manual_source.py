from sage.api.operator import SourceFunction
from sage.api.operator import Data
from typing import Tuple, Any

from sage.utils.data_loader import resolve_data_path
from sage.core.io.message_queue import MessageQueue

class ManualSource(SourceFunction):
    """
    A source function that reads a file line by line and returns each line as a string.

    Input: None (reads directly from a file located at the specified `data_path`).
    Output: A Data object containing the next line of the file content.

    Attributes:
        config: Configuration dictionary containing various settings, including the file path.
        data_path: The path to the file to be read.
        file_pos: Tracks the current position in the file for sequential reading.
    """

    def __init__(self, config:dict):
        """
        Initializes the FileSource with the provided configuration and sets the data path for the file.

        :param config: Configuration dictionary containing source settings, including `data_path`.
        """
        super().__init__()
        self.config = config
        self.input_buffer = MessageQueue()


    def push(self, data: Any):
        """
        External API to push data into the source.
        """
        self.input_buffer.put(data)

    def execute(self) -> Data[str]:
        """
        Reads the next line from the file and returns it as a string.

        :return: A Data object containing the next line of the file content.
        """
        if(self.input_buffer.is_empty()):
            return
        else:
            return Data(self.input_buffer.get())