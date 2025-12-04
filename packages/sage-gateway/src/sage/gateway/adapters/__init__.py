"""Protocol adapters for different API formats"""

from .openai import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionUsage,
    ChatMessage,
    OpenAIAdapter,
)

__all__ = [
    "OpenAIAdapter",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatCompletionChoice",
    "ChatCompletionUsage",
    "ChatMessage",
]
