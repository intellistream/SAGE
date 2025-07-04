from typing import TypeVar, Generic

T = TypeVar('T')
class Data(Generic[T]):
    def __init__(self, data: T):
        self.data = data