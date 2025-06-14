import logging
from typing import TypeVar,Generic
T = TypeVar('T')
class Data(Generic[T]):
    def __init__(self, data: T):
        self.data = data 
class BaseFuction:
    def __init__(self):
        self.upstream = None
        self.downstream = None
        self._name = self.__class__.__name__
        self.logger = logging.getLogger(self.__class__.__name__)

    def set_upstream(self, op):
        self.upstream = op
        if op:
            op.downstream = self

    def set_downstream(self, op):
        self.downstream = op
        if op:
            op.upstream = self

    def get_name(self):
        return self._name

    def execute(self, *args, **kwargs):
        """
        Override this method with actual operator logic in subclasses.
        """
        raise NotImplementedError(f"{self._name}.execute() is not implemented")
    
class StateLessFuction(BaseFuction):
    def __init__(self):
        super().__init__()
    
    def execute(self, data: Data[T]) -> Data[T]:
        raise NotImplementedError(f"{self.get_name()}.execute() is not implemented")

class StatefulFuction(BaseFuction):
    def __init__(self):
        super().__init__()
        self._state = {}

    def execute(self, data: Data[T]) -> Data[T]:
        raise NotImplementedError(f"{self.get_name()}.execute() is not implemented")

    def get_state(self):
        return self._state

class SharedStateFuction(BaseFuction):
    shared_state = {}  # class-level shared state

    def __init__(self):
        super().__init__()

    def execute(self, data: Data[T]) -> Data[T]:
        raise NotImplementedError(f"{self.get_name()}.execute() is not implemented")

    @classmethod
    def get_shared_state(cls):
        return cls.shared_state
