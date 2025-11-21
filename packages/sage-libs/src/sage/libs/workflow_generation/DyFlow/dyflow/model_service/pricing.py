"""
Module for handling pricing calculations.
"""

# Model price information (per 1M tokens in USD)
PRICE_INFO = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "o3-mini": {"input": 1.10, "output": 4.40},
    "chatgpt-4o-latest": {"input": 5.00, "output": 15.00},
    "llama-3.1-70B": {"input": 0.23, "output": 0.40},
    "llama-3.1-8B": {"input": 0.03, "output": 0.05},
    "llama-3.3-70B": {"input": 0.23, "output": 0.40},
    "gemma-2-27B": {"input": 0.27, "output": 0.27},
    "qwen-2.5-72B": {"input": 0.13, "output": 0.40},
    "qwen-2.5-7B": {"input": 0.025, "output": 0.05},
    "yi-lightning": {"input": 0.13, "output": 0.13},
    "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3.7-sonnet": {"input": 3.00, "output": 15.00},
    "deepseek-r1": {"input": 0.75, "output": 2.40},
    "gemma-3-27B": {"input": 0.1, "output": 0.2},
    "gemma-3-4B": {"input": 0.02, "output": 0.04},
    "gemma-3-12B": {"input": 0.05, "output": 0.1},
    "local": {"input": 0.0, "output": 0.0},
    "phi-4": {"input": 0.07, "output": 0.14},
    "gpt-4.1": {"input": 2.0, "output": 8.0},
    "gpt-4.1-mini": {"input": 0.4, "output": 1.6},
    "gpt-4.1-nano": {"input": 0.1, "output": 0.4},
    "llama-4-scout": {"input": 0.08, "output": 0.3},
    "qwen3-14B": {"input": 0.07, "output": 0.24},
    "qwen3-235B-A22B": {"input": 0.2, "output": 0.6},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
}


def calculate_price(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate the price for the API call

    Args:
        model (str): The model name
        input_tokens (int): Number of input tokens
        output_tokens (int): Number of output tokens

    Returns:
        float: The price in USD
    """
    if model not in PRICE_INFO:
        print(f"No price information available for model {model}. Using default pricing.")
        return 0.0

    # Calculate price in USD (converting from per million tokens to per token)
    input_price = (input_tokens / 1000000) * PRICE_INFO[model]["input"]
    output_price = (output_tokens / 1000000) * PRICE_INFO[model]["output"]

    return input_price + output_price


def get_price_info(model: str) -> dict[str, float]:
    """Get the price information for a model

    Args:
        model (str): The model name

    Returns:
        Dict: The price information for input and output tokens
    """
    if model not in PRICE_INFO:
        return {"input": 0.0, "output": 0.0}
    return PRICE_INFO[model]
