from sage.api.operator import SourceFunction
from sage.api.operator import Data
from typing import Tuple
class FileSource(SourceFunction):

    def __init__(self,config):
        super().__init__()
        self.config=config["source"]
        self.data_path=self.config["data_path"]

    def execute(self)->Data[str]:
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                query = f.read()
                return Data(query)
        except FileNotFoundError:
            print(f"File not found: {self.data_path}")
        except Exception as e:
            print(f"Read File error : {e}")
        return Data("")