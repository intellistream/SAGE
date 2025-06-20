from abc import ABC, abstractmethod
from typing import List, Any

class BaseKVIndex(ABC):
    def __init__(
        self,
        name: str,
        texts: List[str],
        ids: List[str]):
        """
        :param name: 索引名称
        :param texts: 文本列表
        :param ids: 对应的 id 列表，len(ids) == len(texts)
        """
        self.name = name

    @abstractmethod
    def insert(self, text: str, id: str) -> None:
        pass

    @abstractmethod
    def delete(self, id: str) -> None:
        pass

    @abstractmethod
    def search(self, query: str, topk: int = 10) -> List[str]:
        pass

    @abstractmethod
    def update(self, id: str, new_text: str) -> None:
        pass
