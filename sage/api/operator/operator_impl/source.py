from sage.api.operator import SourceFunction
from sage.api.operator import Data
from typing import Tuple
import ray

@ray.remote
class FileSource(SourceFunction):
    """
    A source function that reads a file line by line and returns each line as a string.

    Input: None (reads directly from a file located at the specified `data_path`).
    Output: A Data object containing the next line of the file content.

    Attributes:
        config: Configuration dictionary containing various settings, including the file path.
        data_path: The path to the file to be read.
        file_pos: Tracks the current position in the file for sequential reading.
    """

    def __init__(self, config):
        """
        Initializes the FileSource with the provided configuration and sets the data path for the file.

        :param config: Configuration dictionary containing source settings, including `data_path`.
        """
        super().__init__()
        self.config = config["source"]
        self.data_path = self.config["data_path"]
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
