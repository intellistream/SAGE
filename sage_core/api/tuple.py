from typing import TypeVar, Generic

# deprecated
T = TypeVar('T')
class Data(Generic[T]):
    def __init__(self, data: T):
        self.data = data