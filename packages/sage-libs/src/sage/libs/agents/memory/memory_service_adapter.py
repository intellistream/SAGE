# sage/libs/agents/memory/memory_service_adapter.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Callable, Literal
from dataclasses import dataclass
from .base import BaseMemory, MemoryRecord  # 你前面定义的统一接口
# 依赖你给的 MemoryService
from sage.middleware.services.memory.memory_service import MemoryService
MemoryKind = Literal["working", "episodic", "semantic"]

@dataclass
class MemoryServiceAdapterConfig:
    session_id: Optional[str] = None              # 会话维度隔离
    similarity_threshold: Optional[float] = None  # 相似度阈值（越小越相近，取决于你的 VDB metric）
    include_graph_context: bool = False           # 是否返回图上下文
    create_knowledge_graph: bool = False          # 写入时是否建图

class MemoryServiceAdapter(BaseMemory):
    """
    将 teammates 的 MemoryService 封装为 BaseMemory：
      - add(MemoryRecord) -> 调用 store_memory()
      - search(query)     -> embed(query) -> search_memories()
      - working_window()  -> 用 kv 持本地窗口（可选：也可入服务）
      - as_context()      -> 组合 working + episodic + semantic
    """
    def __init__(
        self,
        mem_svc: MemoryService,
        embed_fn: Callable[[str], List[float]],
        cfg: Optional[MemoryServiceAdapterConfig] = None,
    ):
        self.svc = mem_svc
        self.embed = embed_fn
        self.cfg = cfg or MemoryServiceAdapterConfig()
        # 本地 working 缓冲，快速给 Planner 用，不必每次都查 VDB
        self._working_buf: List[str] = []

    # ============ BaseMemory 接口实现 ============

    def add(self, rec: MemoryRecord) -> str:
        kind_map = {
            "working": "conversation",   # 你们的 service 中 memory_type 可以自定义
            "episodic": "event",
            "semantic": "knowledge",
        }
        memory_type = kind_map.get(rec.kind, "event")
        vec = self.embed(rec.text)  # 向量由外部注入（与 RAG 复用同一模型）

        mid = self.svc.store_memory(
            content=rec.text,
            vector=vec,
            session_id=self.cfg.session_id,
            memory_type=memory_type,
            metadata=(rec.meta or {}),
            create_knowledge_graph=self.cfg.create_knowledge_graph,
        )

        if rec.kind == "working":
            self._working_buf.append(rec.text)
            self._working_buf = self._working_buf[-16:]  # 简单保留最近 N 条

        return mid

    def search(
        self,
        query: str,
        top_k: int = 5,
        kind: Optional[MemoryKind] = None,
    ) -> List[MemoryRecord]:
        qvec = self.embed(query)
        type_map = {
            "working": "conversation",
            "episodic": "event",
            "semantic": "knowledge",
            None: None
        }
        memory_type = type_map.get(kind, None)

        results = self.svc.search_memories(
            query_vector=qvec,
            session_id=self.cfg.session_id,
            memory_type=memory_type,
            limit=top_k,
            similarity_threshold=self.cfg.similarity_threshold,
            include_graph_context=self.cfg.include_graph_context,
        )

        out: List[MemoryRecord] = []
        rev_type = {"conversation": "working", "event": "episodic", "knowledge": "semantic"}
        for r in results:
            raw_type = r.get("memory_type")
            mkind: MemoryKind = rev_type.get(raw_type, "episodic")  # type: ignore # 默认回落 episodic
            meta = r.get("metadata", {})
            text = r.get("content") or r.get("vector_text") or ""
            out.append(MemoryRecord(text=text, kind=mkind, meta=meta))
        return out

    def working_window(self, last_n: int = 8) -> List[str]:
        return self._working_buf[-last_n:]

    def as_context(self, limit_chars: int = 1200) -> str:
        lines: List[str] = []
        # working：直接从本地窗口
        for w in self.working_window(8):
            lines.append(f"[WK] {w}")
        # episodic / semantic：各检索一些代表性内容
        for rec in self.search("recent tool executions", 3, "episodic"):
            lines.append(f"[EP] {rec.text}")
        for rec in self.search("user preferences and rules", 3, "semantic"):
            lines.append(f"[SE] {rec.text}")
        return "\n".join(lines)[:limit_chars]
