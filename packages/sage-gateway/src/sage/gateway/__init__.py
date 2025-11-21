"""
SAGE Gateway - OpenAI/Anthropic Compatible API Gateway

Layer: L6 (User Interface & API Gateway)
Dependencies: sage-kernel (L3), sage-libs (L3), sage-common (L1)

提供熟悉的 API 接口，将请求转换为 SAGE DataStream 执行：
- OpenAI /v1/chat/completions
- Anthropic /v1/messages (planned)
- Session management
- Streaming support (SSE/WebSocket)
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
