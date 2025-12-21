from __future__ import annotations

from typing import Any


class GeneratorToClientAdapter:
    """
    Adapts OpenAIGenerator/HFGenerator (L4) to UnifiedInferenceClient interface (L2/L3).
    """

    def __init__(self, generator):
        self.generator = generator

    def chat(
        self, messages: list[dict[str, str]], temperature: float = 0.7, max_tokens: int = 512
    ) -> str:
        """
        Execute chat completion.
        """
        # OpenAIGenerator.execute takes [user_query, messages] or just messages depending on impl.
        # Let's check OpenAIGenerator.execute signature.
        # Based on usage in LLMPlanner: self.generator.execute([user_query, messages])
        # But here we might not have user_query easily available if it's just a chat call.
        # We can pass the last user message as user_query.

        user_query = "Chat request"
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_query = msg["content"]
                break

        # The generator returns (token_usage, text_output)
        _, output = self.generator.execute([user_query, messages])
        return output

    def generate(self, prompt: str, **kwargs) -> list[dict[str, Any]]:
        """
        Execute text generation.
        """
        _, output = self.generator.execute([prompt, [{"role": "user", "content": prompt}]])
        return [{"generations": [{"text": output}]}]
