"""
LLM client helpers for DyFlow designer and executor roles.
"""

from typing import Any

from ..model_service.model_service import ModelService


class ExecutorLLMClient:
    """
    Client for the executor LLM.

    This client is used to execute specific instructions in the workflow.
    """

    def __init__(self, model_name: str = "gpt-4o-mini"):
        """
        Initialize the executor LLM client.

        Args:
            model_name: Name of the model to use (default: "gpt-4o-mini")
        """
        self.model_name = model_name
        self.service = ModelService(model=model_name)

    def generate(self, prompt: str, temperature: float = 0.001) -> str:
        """
        Call the executor LLM with the given prompt.

        Args:
            prompt: The prompt to send to the model
            temperature: Temperature parameter for generation (default: 0.001)

        Returns:
            str: The model's response
        """
        return self.service.generate(prompt=prompt, temperature=temperature)

    def get_usage(self) -> dict[str, Any]:
        """
        Get the usage information for the executor LLM.
        """
        return self.service.get_usage_stats()


class DesignerLLMClient:
    """
    Client for the designer LLM.
    """

    def __init__(self, model_name: str = "gpt-4o"):
        """
        Initialize the designer LLM client.

        Args:
            model_name: Name of the model to use (default: "gpt-4o")
        """
        self.model_name = model_name
        self.service = ModelService(model=model_name)

    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Call the designer LLM with the given prompt.
        """
        return self.service.generate(prompt=prompt, temperature=temperature)

    def get_usage(self) -> dict[str, Any]:
        """
        Get the usage information for the designer LLM.
        """
        return self.service.get_usage_stats()
