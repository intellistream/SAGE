"""Session management module"""

from .manager import ChatMessage, ChatSession, SessionManager, get_session_manager
from .storage import FileSessionStore, SessionStorage


# 懒加载 NeuroMemSessionStorage（避免启动时加载 FAISS）
def __getattr__(name: str):
    if name == "NeuroMemSessionStorage":
        from .neuromem_storage import NeuroMemSessionStorage

        return NeuroMemSessionStorage
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ChatMessage",
    "ChatSession",
    "SessionManager",
    "get_session_manager",
    "FileSessionStore",
    "NeuroMemSessionStorage",
    "SessionStorage",
]
