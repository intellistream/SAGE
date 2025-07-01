from typeguard import value
from sage.core.operator import BaseFunction,Data
from typing import Tuple, List
def condition(value:bool)->bool:
    if value:
        return True
    else:   
        return False
    
class BoolRouter(BaseFunction):
    """
    BaseFunction that routes based on a boolean value.
    Used for control two different branches in the pipeline.
    """
    def __init__(self,config):
        super().__init__()
        self.config = config["router"]

        self.condition=condition

    def execute(self, data:Data) -> Data[bool]:
        try:
            value,_,_=data.data
            if self.condition(value):
                return Data(True)
            else:
                return Data(False)
        except Exception as e:
            self.logger.error(f"{e} when WriterFuction")