from sage.api.operator import SourceFunction
from sage.api.operator import Data
from typing import Tuple
from typing import Tuple, List
import ray

class FileSource(SourceFunction):
    """
    A source function that reads a file and returns its contents as a string.

    Input: None (reads directly from a file located at the specified `data_path`).
    Output: A Data object containing the content of the file as a string.

    Attributes:
        config: Configuration dictionary containing various settings, including the file path.
        data_path: The path to the file to be read.
    """

    def __init__(self, config):
        """
        Initializes the FileSource with the provided configuration and sets the data path for the file.

        :param config: Configuration dictionary containing source settings, including `data_path`.
        """
        super().__init__()  # Call the parent class's constructor
        self.config = config["source"]  # Access the source configuration
        self.data_path = self.config["data_path"]  # Retrieve the file path from the configuration

    def execute(self) -> Data[str]:
        """
        Reads the file located at `data_path` and returns its contents as a string.

        :return: A Data object containing the file content as a string.
        """
        try:
            # Open the file in read mode and read its contents
            with open(self.data_path, 'r', encoding='utf-8') as f:
                query = f.read()  # Read the entire file content
                return Data(query)  # Return the content wrapped in a Data object
        except FileNotFoundError:
            self.logger.error(f"File not found: {self.data_path}")
        except Exception as e:
            self.logger.error(f"Error reading file '{self.data_path}': {e}")
        
        # Return an empty string inside a Data object if an error occurs
        return Data("")

class JSONFileBatchSource(SourceFunction):
    """
    A source function that reads a list of JSON files and returns their parsed contents.

    Input: A Data object containing a list of JSON file paths (List[str]).
    Output: A Data object containing a list of parsed JSON contents (List[dict] or List[Any]).

    Attributes:
        config: Configuration dictionary, currently unused but kept for future extension.
    """

    def __init__(self, config):
        """
        Initializes the JSONFileBatchSource with the provided configuration.

        :param config: Configuration dictionary (currently unused but required for interface consistency).
        """
        super().__init__()
        self.config = config.get("jsonsource", {})  # Default to empty dict if 'source' key is not present

    def execute(self, data: Data[List[str]]) -> Data[List[dict]]:
        """
        Reads the list of JSON files and returns a list of their parsed contents.

        :param inputs: A Data object containing a list of JSON file paths.
        :return: A Data object containing a list of parsed JSON contents.
        """
        import json

        file_paths = data.data
        results = []

        for path in file_paths:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    results.append(content)
            except FileNotFoundError:
                self.logger.error(f"File not found: {path}")
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error in file '{path}': {e}")
            except Exception as e:
                self.logger.error(f"Error reading file '{path}': {e}")
        
        return Data(results)
