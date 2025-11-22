"""vLLM LLM算子 - 基于vLLM服务的大语言模型推理算子"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from sage.common.core.functions import MapFunction as MapOperator


def _extract_prompt_bundle(data: Sequence[Any]) -> tuple[Any, Any, dict[str, Any]]:
    """Normalize pipeline inputs into (original, prompt, overrides)."""

    if not data:
        raise ValueError("VLLMGenerator expects at least one input value")

    if len(data) == 1:
        original, prompt = {}, data[0]
    else:
        original, prompt = data[0], data[1]

    overrides: dict[str, Any] = {}
    if isinstance(prompt, dict) and "prompt" in prompt:
        overrides = dict(prompt.get("options", {}))
        prompt = prompt.get("prompt")

    return original, prompt, overrides


@dataclass
class VLLMGenerator(MapOperator):
    """
    vLLM 生成算子 - 调用 vLLM 服务进行文本生成

    继承自 kernel 的 MapOperator 基类，实现 LLM 推理的领域逻辑。

    Example:
        ```python
        generator = VLLMGenerator(
            service_name="vllm_service",
            default_options={"temperature": 0.7, "max_tokens": 512}
        )
        result = generator.execute(["生成一首诗"])
        ```
    """

    service_name: str = "vllm_service"
    timeout: float = 60.0
    default_options: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__init__()

    def execute(self, data: Sequence[Any]) -> tuple[Any, str] | dict[str, Any]:
        """执行生成"""
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
class VLLMEmbedding(MapOperator):
    """
    vLLM 嵌入算子 - 从 vLLM 服务获取文本嵌入

    Example:
        ```python
        embedder = VLLMEmbedding(service_name="vllm_service")
        result = embedder.execute("这是一段文本")
        vectors = result["vectors"]
        ```
    """

    service_name: str = "vllm_service"
    timeout: float = 30.0
    normalize: bool = True
    default_options: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__init__()

    def execute(self, data: str | Sequence[str]) -> dict[str, Any]:
        """执行嵌入"""
        texts: list[str]
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


__all__ = ["VLLMGenerator", "VLLMEmbedding"]
