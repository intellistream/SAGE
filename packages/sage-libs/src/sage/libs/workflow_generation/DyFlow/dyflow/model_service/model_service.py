"""
ModelService - Unified LLM service abstraction.

Provides a unified interface for multiple LLM providers:
- OpenAI models (GPT-4, GPT-3.5-turbo, etc.)
- Anthropic models (Claude-3, Claude-2, etc.)
- Local models (via custom endpoints)

Features:
- Shared client management
- Token usage tracking
- Cost calculation
- Async support
- Retry mechanisms

Layer: L3 (Core Library)
"""

import os
import threading
from typing import Any, ClassVar, Optional

from sage.common.utils.logging.custom_logger import CustomLogger

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # pragma: no cover - optional dependency

    def load_dotenv(*_args, **_kwargs):  # type: ignore
        return False


from .clients import ModelClients
from .config import MODEL_MAPPING, get_available_models, get_model_category
from .pricing import calculate_price, get_price_info
from .token_counter import TokenTracker
from .utils import retry_decorator

# Initialize logger
logger = CustomLogger(__name__)

# Load environment variables
load_dotenv()

# Set proxy if available
if os.getenv("HTTP_PROXY"):
    os.environ["http_proxy"] = os.getenv("HTTP_PROXY")
    os.environ["https_proxy"] = os.getenv("HTTPS_PROXY")


class ModelService:
    """Service to handle interactions with various AI models"""

    # Class variable to store shared clients
    _clients: ClassVar[Optional[ModelClients]] = None

    @classmethod
    def _get_clients(cls) -> ModelClients:
        """Get or initialize the shared clients instance"""
        if cls._clients is None:
            cls._clients = ModelClients()
        return cls._clients

    def __init__(
        self,
        model: str = "chatgpt-4o-latest",
        temperature: float = 0.01,
        lock: threading.Lock = None,
    ):
        """
        Initialize the model service with a specific model

        Args:
            model (str): The model to use for generation
            temperature (float): Default temperature for generation
            lock: Optional threading lock for local models
        """
        self.token_tracker = TokenTracker()
        self.temperature = temperature

        # Validate and set the model
        if model not in MODEL_MAPPING:
            available = get_available_models()
            raise ValueError(f"Unknown model: {model}. Available models: {', '.join(available)}")

        self.model = model
        self.model_category = get_model_category(model)
        self.pricing = get_price_info(model)

        # Get the shared clients instance
        self.clients = self._get_clients()
        self.lock = lock

    @classmethod
    def create(cls, model: str = "chatgpt-4o-latest", temperature: float = 0.01) -> "ModelService":
        """Factory method to create a new ModelService instance"""
        return cls(model=model, temperature=temperature)

    @classmethod
    def gpt4o(cls, temperature: float = 0.01) -> "ModelService":
        """Create a ModelService instance with GPT-4o"""
        return cls(model="gpt-4o", temperature=temperature)

    @classmethod
    def claude(cls, temperature: float = 0.01) -> "ModelService":
        """Create a ModelService instance with Claude 3.5 Sonnet"""
        return cls(model="claude-3.5-sonnet", temperature=temperature)

    @classmethod
    def local(cls, temperature: float = 0.01, lock: threading.Lock = None) -> "ModelService":
        """Create a ModelService instance with local model server"""
        return cls(model="local", temperature=temperature, lock=lock)

    def switch_model(self, model: str) -> None:
        """
        Switch to a different model

        Args:
            model (str): The new model to use
        """
        if model not in MODEL_MAPPING:
            available = get_available_models()
            raise ValueError(f"Unknown model: {model}. Available models: {', '.join(available)}")

        self.model = model
        self.model_category = get_model_category(model)
        self.pricing = get_price_info(model)
        logger.info(f"Switched to model: {model}")

    @retry_decorator()
    def generate(
        self, prompt: str, temperature: float = None, max_tokens: int = 2048, msg: list = None
    ) -> dict[str, Any]:
        """
        Generate a response using the current model

        Args:
            prompt (str): The input prompt
            temperature (float): Sampling temperature, defaults to self.temperature if None
            max_tokens (int): Maximum number of tokens to generate
            msg: Optional message format for chat models

        Returns:
            Dict containing:
                - response (str): The model's response
                - usage (Dict): Token usage statistics
                - price (float): The cost of this request in USD
        """
        if temperature is None:
            temperature = self.temperature

        if len(prompt) > 50000:
            logger.warning(f"Prompt is too long: {len(prompt)} characters")
            return {"response": None, "model": self.model, "usage": {}, "price": 0}
        # Get response based on model type
        if self.model_category == "anthropic":
            response, tokens = self.clients.call_anthropic(
                self.model, prompt, temperature, max_tokens, msg
            )
        elif self.model_category == "local":
            if self.lock:
                with self.lock:
                    response, tokens = self.clients.call_local(self.model, prompt, temperature, msg)
            else:
                response, tokens = self.clients.call_local(self.model, prompt, temperature, msg)
        else:
            response, tokens = self.clients.call_openai_compatible(
                self.model, prompt, temperature, self.model_category, msg
            )

        input_tokens, output_tokens = tokens["input_tokens"], tokens["output_tokens"]

        # Track usage
        self.token_tracker.track_usage(self.model, input_tokens, output_tokens)

        # Calculate price
        price = calculate_price(self.model, input_tokens, output_tokens)

        return {
            "response": response,
            "model": self.model,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
            "price": price,
        }

    async def generate_async(
        self, prompt: str, temperature: float = 0.001, max_tokens: int = 2048
    ) -> dict[str, Any]:
        """
        Generate a response using the current model asynchronously

        Args:
            prompt (str): The input prompt
            temperature (float): Sampling temperature
            max_tokens (int): Maximum number of tokens to generate

        Returns:
            Dict containing:
                - response (str): The model's response
                - usage (Dict): Token usage statistics
                - price (float): The cost of this request in USD
        """

        # Get response based on model type
        if self.model_category == "anthropic":
            response, tokens = await self.clients.call_anthropic_async(
                self.model, prompt, temperature, max_tokens
            )
        else:
            response, tokens = await self.clients.call_openai_compatible_async(
                self.model, prompt, temperature, self.model_category
            )

        input_tokens, output_tokens = tokens["input_tokens"], tokens["output_tokens"]

        # Track usage
        self.token_tracker.track_usage(self.model, input_tokens, output_tokens)

        # Calculate price
        price = calculate_price(self.model, input_tokens, output_tokens)

        return {
            "response": response,
            "model": self.model,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
            "price": price,
        }

    def get_usage_stats(self) -> dict[str, Any]:
        """
        Get the current usage statistics

        Returns:
            Dict: Usage statistics for all models
        """
        stats = {}
        token_stats = self.token_tracker.get_stats()

        for model, usage in token_stats.items():
            stats[model] = {
                **usage,
                "cost": calculate_price(model, usage["input_total"], usage["output_total"]),
            }
        return stats

    def get_current_model(self) -> str:
        """Get the current model name"""
        return self.model
