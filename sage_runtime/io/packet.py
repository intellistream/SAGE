from typing import TypeVar, Generic, Any

T = TypeVar('T')
class Packet(Generic[T]):
    def __init__(self, payload: T, input_index: int = 0):
        self.payload:Any = payload
        self.input_index:int = input_index