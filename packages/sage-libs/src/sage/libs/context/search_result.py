from dataclasses import dataclass, field, asdict
from typing import Any, List, Dict, Tuple, Optional
import time


@dataclass
class SearchResult:
    """单个搜索结果的数据结构"""
    title: str
    content: str
    source: str
    rank: int = 1  # 搜索结果的排名
    relevance_score: float = 0.0  # 相关性分数
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))

    def __str__(self) -> str:
        """格式化显示搜索结果"""
        return f"[Rank {self.rank}] {self.title}\nContent: {self.content}\nSource: {self.source}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "rank": self.rank,
            "relevance_score": self.relevance_score,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchResult':
        """从字典创建SearchResult"""
        return cls(
            title=data.get("title", ""),
            content=data.get("content", ""),
            source=data.get("source", ""),
            rank=data.get("rank", 1),
            relevance_score=data.get("relevance_score", 0.0),
            timestamp=data.get("timestamp", int(time.time() * 1000))
        )