"""Module for token counting and tracking."""

import logging

try:
    import tiktoken  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    tiktoken = None  # type: ignore

logger = logging.getLogger(__name__)


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """Count the number of tokens in a text string

    Args:
        text (str): The text to count tokens for
        encoding_name (str): The name of the encoding to use

    Returns:
        int: The number of tokens
    """
    if tiktoken is None:
        return len(text) // 4
    try:
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(text))
    except Exception as exc:  # pragma: no cover - diagnostic path
        logger.error("Error in token counting: %s. Using approximate count.", exc)
        return len(text) // 4


class TokenTracker:
    """Track token usage across models"""

    def __init__(self):
        """Initialize the token tracker"""
        self.token_stats = {}

    def track_usage(self, model: str, input_tokens: int, output_tokens: int) -> None:
        """
        Track token usage for a model

        Args:
            model (str): The model name
            input_tokens (int): Number of input tokens
            output_tokens (int): Number of output tokens
        """
        if model not in self.token_stats:
            self.token_stats[model] = {"input_total": 0, "output_total": 0, "requests": 0}

        self.token_stats[model]["input_total"] += input_tokens
        self.token_stats[model]["output_total"] += output_tokens
        self.token_stats[model]["requests"] += 1

    def get_stats(self) -> dict[str, dict[str, int]]:
        """Get the usage statistics

        Returns:
            Dict: The usage statistics
        """
        return self.token_stats
