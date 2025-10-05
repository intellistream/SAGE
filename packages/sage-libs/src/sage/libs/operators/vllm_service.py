"""Operators that interact with the in-process vLLM service."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from sage.core.api.function.map_function import MapFunction


def _extract_prompt_bundle(data: Sequence[Any]) -> Tuple[Any, Any, Dict[str, Any]]:
    """Normalize pipeline inputs into (original, prompt, overrides)."""

    if not data:
        raise ValueError("VLLMServiceGenerator expects at least one input value")

    if len(data) == 1:
        original, prompt = {}, data[0]
    else:
        original, prompt = data[0], data[1]

    overrides: Dict[str, Any] = {}
    if isinstance(prompt, dict) and "prompt" in prompt:
        overrides = dict(prompt.get("options", {}))
        prompt = prompt.get("prompt")

    return original, prompt, overrides


@dataclass
class VLLMServiceGenerator(MapFunction):
    """Invoke the vLLM service for text generation inside a pipeline."""

    service_name: str = "vllm_service"
    timeout: float = 60.0
    default_options: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__init__()

    def execute(self, data: Sequence[Any]) -> Union[Tuple[Any, str], Dict[str, Any]]:
        original, prompt, overrides = _extract_prompt_bundle(data)

        merged_options = dict(self.default_options)
        merged_options.update({k: v for k, v in overrides.items() if v is not None})

        response = self.call_service(
            self.service_name,
            prompt,
            timeout=self.timeout,
            method="generate",
            **merged_options,
        )

        if not response:
            raise RuntimeError("vLLM service returned no generations")

        first_choice = response[0].get("generations", [{}])[0]
        text = first_choice.get("text", "")
        usage = response[0].get("usage", {})

        if isinstance(original, dict):
            result = dict(original)
            result.setdefault("metadata", {})
            result["generated"] = text
            result["usage"] = usage
            return result

        return original, text


@dataclass
class VLLMEmbeddingOperator(MapFunction):
    """Fetch embeddings from the vLLM service."""

    service_name: str = "vllm_service"
    timeout: float = 30.0
    normalize: bool = True
    default_options: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__init__()

    def execute(self, data: Union[str, Sequence[str]]) -> Dict[str, Any]:
        texts: List[str]
        if isinstance(data, str):
            texts = [data]
        elif isinstance(data, Sequence):
            texts = [str(item) for item in data]
        else:
            texts = [str(data)]

        options = dict(self.default_options)
        options.setdefault("normalize", self.normalize)

        result = self.call_service(
            self.service_name,
            texts,
            timeout=self.timeout,
            method="embed",
            **options,
        )

        if not isinstance(result, dict) or "vectors" not in result:
            raise RuntimeError("vLLM embedding response is malformed")

        return result


__all__ = ["VLLMServiceGenerator", "VLLMEmbeddingOperator"]
