import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, List, Dict, Tuple, Optional
from enum import Enum
from uuid import uuid4
import time
from pathlib import Path

from .search_result import SearchResult

@dataclass
class SearchQueryResults:
    """单个搜索查询的结果集"""
    query: str
    results: List[SearchResult] = field(default_factory=list)
    search_timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    total_results_count: int = 0  # 搜索引擎返回的总结果数
    execution_time_ms: int = 0  # 搜索执行时间（毫秒）
    search_engine: str = "unknown"  # 使用的搜索引擎
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外的搜索元数据

    def add_result(self, result: SearchResult) -> None:
        """添加搜索结果"""
        self.results.append(result)

    def get_results_count(self) -> int:
        """获取实际检索到的结果数量"""
        return len(self.results)

    def get_all_content(self) -> str:
        """获取所有结果的内容拼接"""
        return "\n\n".join([f"{result.title}\n{result.content}" for result in self.results])

    def get_top_results(self, n: int = 3) -> List[SearchResult]:
        """获取前N个结果"""
        return self.results[:n]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "query": self.query,
            "results": [result.to_dict() for result in self.results],
            "search_timestamp": self.search_timestamp,
            "total_results_count": self.total_results_count,
            "execution_time_ms": self.execution_time_ms,
            "search_engine": self.search_engine,
            "metadata": self.metadata.copy()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchQueryResults':
        """从字典创建SearchQueryResults"""
        results = [SearchResult.from_dict(r) for r in data.get("results", [])]
        
        return cls(
            query=data.get("query", ""),
            results=results,
            search_timestamp=data.get("search_timestamp", int(time.time() * 1000)),
            total_results_count=data.get("total_results_count", 0),
            execution_time_ms=data.get("execution_time_ms", 0),
            search_engine=data.get("search_engine", "unknown"),
            metadata=data.get("metadata", {})
        )