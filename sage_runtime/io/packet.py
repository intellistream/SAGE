from typing import TypeVar, Generic

T = TypeVar('T')
class Packet(Generic[T]):
    def __init__(self, payload: T):
        self.payload = payload