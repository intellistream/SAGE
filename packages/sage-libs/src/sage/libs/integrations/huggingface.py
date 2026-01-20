"""HuggingFace local inference client.

This module provides a simple client for running HuggingFace models locally.
For production use with remote LLM services, use:

    from isagellm import UnifiedInferenceClient
    client = UnifiedInferenceClient.create()

Note:
    This client is kept for local development and testing scenarios
    where you want to run models directly on your machine without
    external services.
"""

import logging
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

logger = logging.getLogger(__name__)


class HFClient:
    def __init__(
        self,
        model_name: str = "llama",
        device: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        seed: int | None = None,
    ):
        self.device: str = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        self.model_name = model_name
        self.model, self.tokenizer = self._initialize_model()

    def _initialize_model(self):
        tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            trust_remote_code=True,
            device_map="auto" if self.device == "cuda" else None,
        )

        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # Ensure model on the right device if not using device_map
        if self.device != "cuda":
            # Note: type ignore is needed due to incomplete type hints in transformers library
            # model.to() correctly accepts device strings at runtime
            model.to(self.device)  # type: ignore

        return model, tokenizer

    def generate(self, prompt: str | list[dict[str, str]], **kwargs: Any) -> str:
        """Generate text from a prompt.

        Args:
            prompt: Either a string prompt or a list of message dicts
                   with 'role' and 'content' keys.
            **kwargs: Generation parameters:
                - max_new_tokens: Maximum tokens to generate (default: 128)
                - temperature: Sampling temperature (default: 0.3)

        Returns:
            Generated text response.
        """
        generation_kwargs = {
            "max_new_tokens": kwargs.get("max_new_tokens", 128),
            "temperature": kwargs.get("temperature", 0.3),
            "do_sample": True,
            "pad_token_id": self.tokenizer.eos_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
        }

        # Construct prompt text
        if isinstance(prompt, list):
            input_prompt = ""
            for message in prompt:
                role = message["role"]
                content = message["content"]
                if role == "system":
                    input_prompt += f"System: {content}\n\n"
                elif role == "user":
                    input_prompt += f"User: {content}\n\nAssistant: "
        else:
            input_prompt = prompt

        logger.debug("Input prompt: %s...", input_prompt[:200])

        # Tokenize input
        input_ids = self.tokenizer(
            input_prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=1024,
        ).to(self.device)

        logger.debug("Input token length: %d", input_ids["input_ids"].shape[1])

        # Generate output
        try:
            with torch.no_grad():
                output = self.model.generate(**input_ids, **generation_kwargs)
        except Exception as e:
            logger.exception("Generation failed: %s", e)
            raise RuntimeError(f"Generation failed: {e}") from e

        # Decode output
        response_text = self.tokenizer.decode(
            output[0][input_ids["input_ids"].shape[1] :], skip_special_tokens=True
        ).strip()

        logger.debug("Generated response: %s", response_text)
        return response_text
