import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, List, Dict, Tuple, Optional
from enum import Enum
from uuid import uuid4
import time
from pathlib import Path

from .search_result import SearchResult
from .search_query_results import SearchQueryResults


@dataclass
class SearchSession:
    """整个搜索会话的结果集合"""
    session_id: str = field(default_factory=lambda: str(uuid4()))
    query_results: List[SearchQueryResults] = field(default_factory=list)
    session_timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    original_question: str = ""
    session_metadata: Dict[str, Any] = field(default_factory=dict)

    def add_query_results(self, query_results: SearchQueryResults) -> None:
        """添加查询结果"""
        self.query_results.append(query_results)

    def get_all_queries(self) -> List[str]:
        """获取所有查询字符串"""
        return [qr.query for qr in self.query_results]

    def get_total_results_count(self) -> int:
        """获取所有查询的结果总数"""
        return sum(qr.get_results_count() for qr in self.query_results)

    def get_all_results(self) -> List[SearchResult]:
        """获取所有搜索结果"""
        all_results = []
        for query_result in self.query_results:
            all_results.extend(query_result.results)
        return all_results

    def get_results_by_query(self, query: str) -> Optional[SearchQueryResults]:
        """根据查询字符串获取结果"""
        for qr in self.query_results:
            if qr.query == query:
                return qr
        return None

    def get_combined_content(self) -> str:
        """获取所有搜索结果的组合内容"""
        combined_parts = []
        for i, query_result in enumerate(self.query_results, 1):
            combined_parts.append(f"=== Query {i}: {query_result.query} ===")
            for j, result in enumerate(query_result.results, 1):
                combined_parts.append(f"[Result {j}] {result.title}")
                combined_parts.append(f"Content: {result.content}")
                combined_parts.append(f"Source: {result.source}")
                combined_parts.append("")
        return "\n".join(combined_parts)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "query_results": [qr.to_dict() for qr in self.query_results],
            "session_timestamp": self.session_timestamp,
            "original_question": self.original_question,
            "session_metadata": self.session_metadata.copy()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchSession':
        """从字典创建SearchSession"""
        query_results = [SearchQueryResults.from_dict(qr) for qr in data.get("query_results", [])]
        
        return cls(
            session_id=data.get("session_id", str(uuid4())),
            query_results=query_results,
            session_timestamp=data.get("session_timestamp", int(time.time() * 1000)),
            original_question=data.get("original_question", ""),
            session_metadata=data.get("session_metadata", {})
        )