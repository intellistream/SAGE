"""Configuration settings for the model service."""

import os

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # pragma: no cover - optional dependency

    def load_dotenv(*_args, **_kwargs):  # type: ignore
        return False


# Load environment variables
load_dotenv()

# Set proxy if available
if os.getenv("HTTP_PROXY"):
    os.environ["http_proxy"] = os.getenv("HTTP_PROXY")
    os.environ["https_proxy"] = os.getenv("HTTPS_PROXY")

# Model name mapping from user-friendly names to API model identifiers
MODEL_MAPPING = {
    "gpt-3.5-turbo": "gpt-3.5-turbo",
    "gpt-4o": "gpt-4o-2024-11-20",
    "gpt-4o-mini": "gpt-4o-mini",
    "o3-mini": "o3-mini-2025-01-31",
    "chatgpt-4o-latest": "chatgpt-4o-latest",
    "llama-3.1-70B": "meta-llama/Meta-Llama-3.1-70B-Instruct",
    "llama-3.1-8B": "meta-llama/Meta-Llama-3.1-8B-Instruct",
    "llama-3.3-70B": "meta-llama/Llama-3.3-70B-Instruct",
    "gemma-2-27B": "google/gemma-2-27b-it",
    "qwen-2.5-72B": "Qwen/Qwen2.5-72B-Instruct",
    "qwen-2.5-7B": "Qwen/Qwen2.5-7B-Instruct",
    "yi-lightning": "yi-lightning",
    "claude-3.5-sonnet": "claude-3-5-sonnet-20241022",
    "claude-3.7-sonnet": "claude-3-7-sonnet-20250219",
    "deepseek-r1": "deepseek-ai/DeepSeek-R1",
    "gemma-3-27B": "google/gemma-3-27b-it",
    "gemma-3-4B": "google/gemma-3-4b-it",
    "gemma-3-12B": "google/gemma-3-12b-it",
    "deepseek-v3": "deepseek-ai/DeepSeek-V3-0324",
    "phi-4": "microsoft/phi-4",
    "gpt-4.1": "gpt-4.1-2025-04-14",
    "gpt-4.1-mini": "gpt-4.1-mini-2025-04-14",
    "gpt-4.1-nano": "gpt-4.1-nano-2025-04-14",
    "qwen3-235B-A22B": "Qwen/Qwen3-235B-A22B",
    "llama-4-scout": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
    "qwen3-14B": "Qwen/Qwen3-14B",
    "local": "",
}

# Model categories for client selection
ANTHROPIC_MODELS = ["claude-3.5-sonnet", "claude-3.7-sonnet"]
DEEPINFRA_MODELS = [
    "llama-3.1-70B",
    "llama-3.1-8B",
    "qwen-2.5-72B",
    "gemma-2-27B",
    "llama-3.3-70B",
    "qwen-2.5-7B",
    "deepseek-r1",
    "gemma-3-27B",
    "gemma-3-4B",
    "gemma-3-12B",
    "deepseek-v3",
    "phi-4",
    "qwen3-235B-A22B",
    "llama-4-scout",
    "qwen3-14B",
]
YI_MODELS = ["yi-lightning"]
LOCAL_MODELS = ["local"]
STRUCTURED_OUTPUT_SUPPORT = ["gpt-4o", "gpt-4o-mini", "chatgpt-4o-latest"]

# Environment variables
ENV_VARS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepinfra": {"api_key": "DEEPINFRA_API_KEY", "base_url": "DEEPINFRA_BASE_URL"},
    "yi": {"api_key": "YI_API_KEY", "base_url": "YI_BASE_URL"},
}


def get_available_models():
    """Return a list of available models"""
    return list(MODEL_MAPPING.keys())


def get_model_category(model_name):
    """Determine which category a model belongs to"""
    if model_name in ANTHROPIC_MODELS:
        return "anthropic"
    elif model_name in DEEPINFRA_MODELS:
        return "deepinfra"
    elif model_name in YI_MODELS:
        return "yi"
    elif model_name in LOCAL_MODELS:
        return "local"
    else:
        return "openai"
