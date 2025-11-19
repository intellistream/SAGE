"""Protocol adapters for different API formats"""

from .openai import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    OpenAIAdapter,
)

__all__ = [
    "OpenAIAdapter",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatMessage",
]
