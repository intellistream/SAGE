"""Blocking vLLM service integration for SAGE.

Layer: L1 (Foundation - Common Components)

This module provides a SAGE service wrapper around vLLM for:
- High-performance LLM text generation
- LLM-based embeddings
- Model management (download, switch, fine-tune)

Dependencies:
    - sage.platform.service (L2 - BaseService interface)
    - sage.common.model_registry (L1 - Model management)
    - vllm (external - optional dependency)
"""

from __future__ import annotations

import threading
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from sage.common.model_registry import vllm_registry
from sage.common.model_registry.vllm_registry import ModelInfo
from sage.common.service import BaseService

try:  # Optional dependency – raise during setup if unavailable
    from vllm import LLM, SamplingParams
except ImportError:  # pragma: no cover - allows unit tests to stub vllm
    LLM = None  # type: ignore
    SamplingParams = None  # type: ignore


_DEFAULT_SAMPLING = {
    "temperature": 0.7,
    "top_p": 0.95,
    "max_tokens": 512,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
}
_DEFAULT_ENGINE = {
    "dtype": "auto",
    "tensor_parallel_size": 1,
    "gpu_memory_utilization": 0.9,
    "max_model_len": 4096,
}


@dataclass
class VLLMServiceConfig:
    """Configuration payload accepted by :class:`VLLMService`."""

    model_id: str
    embedding_model_id: str | None = None
    auto_download: bool = False
    auto_reload: bool = True
    engine: dict[str, Any] = field(default_factory=lambda: dict(_DEFAULT_ENGINE))
    embedding_engine: dict[str, Any] = field(default_factory=dict)
    sampling: dict[str, Any] = field(default_factory=lambda: dict(_DEFAULT_SAMPLING))
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VLLMServiceConfig:
        engine = dict(_DEFAULT_ENGINE)
        engine.update(data.get("engine", {}))

        sampling = dict(_DEFAULT_SAMPLING)
        sampling.update(data.get("sampling", {}))

        embedding_engine = dict(engine)
        embedding_engine.update(data.get("embedding_engine", {}))

        return cls(
            model_id=data["model_id"],
            embedding_model_id=data.get("embedding_model_id"),
            auto_download=bool(data.get("auto_download", False)),
            auto_reload=bool(data.get("auto_reload", True)),
            engine=engine,
            embedding_engine=embedding_engine,
            sampling=sampling,
            tags=list(data.get("tags", [])),
        )


class VLLMService(BaseService):
    """Blocking service that hosts a vLLM engine for generation and embeddings."""

    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self.config = VLLMServiceConfig.from_dict(config)
        self._text_engine: LLM | None = None  # type: ignore
        self._embedding_engine: LLM | None = None  # type: ignore
        self._sampling_defaults = self._build_sampling_params(self.config.sampling)
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # SAGE lifecycle hooks
    # ------------------------------------------------------------------
    def setup(self) -> None:
        if LLM is None:
            raise RuntimeError(
                "vLLM is not installed. Install the 'isage-middleware[vllm]' extra to enable this service."
            )

        self.logger.info("VLLMService setup starting")
        self._load_text_engine(force_reload=False)
        if (
            self.config.embedding_model_id
            and self.config.embedding_model_id != self.config.model_id
        ):
            self._load_embedding_engine(force_reload=False)
        self.logger.info("VLLMService setup complete")

    def cleanup(self) -> None:
        with self._lock:
            for engine_name, engine in {
                "text": self._text_engine,
                "embedding": self._embedding_engine,
            }.items():
                if engine is None:
                    continue
                try:
                    if hasattr(engine, "shutdown"):
                        engine.shutdown()
                except Exception as exc:  # pragma: no cover - shutdown best-effort
                    self.logger.warning(f"Failed to shutdown {engine_name} engine: {exc}")
            self._text_engine = None
            self._embedding_engine = None

    # ------------------------------------------------------------------
    # Public service API
    # ------------------------------------------------------------------
    def process(self, payload: dict[str, Any]) -> Any:
        task = (payload or {}).get("task", "generate")
        inputs = (payload or {}).get("inputs")
        options = (payload or {}).get("options", {})

        if task == "generate":
            if inputs is None:
                raise ValueError("'generate' task requires 'inputs'")
            return self.generate(inputs, **options)
        if task == "embed":
            if inputs is None:
                raise ValueError("'embed' task requires 'inputs'")
            return self.embed(inputs, **options)
        if task == "show_models":
            return [self._model_info_to_dict(info) for info in vllm_registry.list_models()]
        if task == "download_model":
            target = options.get("model_id") or inputs
            if not target:
                raise ValueError("'download_model' task requires 'model_id'")
            info = vllm_registry.download_model(str(target), revision=options.get("revision"))
            if self.config.auto_reload and str(target) == self.config.model_id:
                self.switch_model(str(target), revision=options.get("revision"))
            return self._model_info_to_dict(info)
        if task == "delete_model":
            target = options.get("model_id") or inputs
            if not target:
                raise ValueError("'delete_model' task requires 'model_id'")
            vllm_registry.delete_model(str(target))
            return {"deleted": target}
        if task == "fine_tune":
            return self.fine_tune(options or inputs or {})

        raise ValueError(f"Unsupported task '{task}'")

    def generate(
        self,
        prompts: str | dict[str, Any] | Sequence[str | dict[str, Any]],
        **runtime_sampling: Any,
    ) -> list[dict[str, Any]]:
        engine = self._load_text_engine(force_reload=False)
        normalized_prompts = self._normalize_prompts(prompts)
        sampling_params = self._merge_sampling_params(runtime_sampling)

        outputs = engine.generate(normalized_prompts, sampling_params=sampling_params)
        results: list[dict[str, Any]] = []
        for request_output in outputs:
            generations = []
            total_output_tokens = 0
            for seq_output in request_output.outputs:
                text = seq_output.text
                token_count = len(seq_output.token_ids)
                total_output_tokens += token_count
                generations.append(
                    {
                        "text": text,
                        "token_ids": seq_output.token_ids,
                        "logprobs": getattr(seq_output, "logprobs", None),
                        "finish_reason": getattr(seq_output, "finish_reason", None),
                    }
                )

            usage = {
                "input_tokens": len(request_output.prompt_token_ids),
                "output_tokens": total_output_tokens,
            }
            results.append(
                {
                    "generations": generations,
                    "usage": usage,
                    "request_id": getattr(request_output, "request_id", None),
                }
            )

        return results

    def embed(
        self,
        texts: str | Sequence[str],
        *,
        normalize: bool = True,
        batch_size: int | None = None,
    ) -> dict[str, Any]:
        engine = self._load_embedding_engine(force_reload=False)
        normalized_texts = self._normalize_texts(texts)
        vectors: list[list[float]] = []

        if hasattr(engine, "get_embedding"):
            raw = engine.get_embedding(normalized_texts)  # type: ignore[attr-defined]
        elif hasattr(engine, "get_embeddings"):
            raw = engine.get_embeddings(normalized_texts, batch_size=batch_size)
        else:
            raise RuntimeError("Current vLLM build does not provide an embedding API")

        for item in raw:
            vec = None
            if isinstance(item, dict) and "embedding" in item:
                vec = item["embedding"]
            elif hasattr(item, "embedding"):
                vec = item.embedding
            elif isinstance(item, (list, tuple)):
                vec = item
            else:
                vec = list(item)
            array = np.array(vec, dtype=np.float32)
            if normalize:
                norm = np.linalg.norm(array)
                if norm > 0:
                    array = array / norm
            vectors.append(array.tolist())

        dim = len(vectors[0]) if vectors else 0
        return {
            "model_id": self.config.embedding_model_id or self.config.model_id,
            "vectors": vectors,
            "dimension": dim,
        }

    # ------------------------------------------------------------------
    # Model management helpers
    # ------------------------------------------------------------------
    def switch_model(self, model_id: str, *, revision: str | None = None) -> None:
        with self._lock:
            self.logger.info(f"Switching vLLM model from {self.config.model_id} to {model_id}")
            self.config.model_id = model_id
            vllm_registry.ensure_model_available(
                model_id,
                revision=revision,
                auto_download=self.config.auto_download,
            )
            self._load_text_engine(force_reload=True, revision=revision)
            if not self.config.embedding_model_id or self.config.embedding_model_id == model_id:
                self._embedding_engine = self._text_engine

    def show_models(self) -> list[dict[str, Any]]:
        return [self._model_info_to_dict(info) for info in vllm_registry.list_models()]

    def fine_tune(self, request: dict[str, Any]) -> dict[str, Any]:
        required_fields = {"base_model", "dataset_path", "output_dir"}
        missing = [field for field in required_fields if field not in request]
        if missing:
            raise ValueError(f"Fine-tune request missing fields: {', '.join(missing)}")
        raise NotImplementedError(
            "Fine-tuning pipeline is not implemented yet. Please contact the fine-tune team."
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _model_info_to_dict(self, info: ModelInfo) -> dict[str, Any]:
        return {
            "model_id": info.model_id,
            "path": str(info.path),
            "revision": info.revision,
            "size_bytes": info.size_bytes,
            "size_mb": round(info.size_mb, 2),
            "last_used": info.last_used_iso,
            "tags": info.tags,
        }

    def _load_text_engine(
        self, *, force_reload: bool, revision: str | None = None
    ) -> LLM:  # type: ignore
        with self._lock:
            if self._text_engine is not None and not force_reload:
                return self._text_engine

            path = vllm_registry.ensure_model_available(
                self.config.model_id,
                revision=revision,
                auto_download=self.config.auto_download,
            )
            self.logger.info(f"Loading vLLM model '{self.config.model_id}' from {path}")

            engine_kwargs = dict(self.config.engine)
            engine_kwargs.setdefault("model", str(path))
            engine_kwargs["model"] = str(path)

            self._text_engine = LLM(**engine_kwargs)  # type: ignore[operator-not-callable]
            self._sampling_defaults = self._build_sampling_params(self.config.sampling)

            if (
                not self.config.embedding_model_id
                or self.config.embedding_model_id == self.config.model_id
            ):
                self._embedding_engine = self._text_engine

            return self._text_engine

    def _load_embedding_engine(
        self, *, force_reload: bool, revision: str | None = None
    ) -> LLM:  # type: ignore
        with self._lock:
            if self._embedding_engine is not None and not force_reload:
                return self._embedding_engine

            model_id = self.config.embedding_model_id or self.config.model_id
            path = vllm_registry.ensure_model_available(
                model_id,
                revision=revision,
                auto_download=self.config.auto_download,
            )

            if self._text_engine is not None and model_id == self.config.model_id:
                self._embedding_engine = self._text_engine
                return self._embedding_engine

            engine_kwargs = dict(self.config.embedding_engine)
            engine_kwargs.setdefault("model", str(path))
            engine_kwargs["model"] = str(path)
            engine_kwargs.setdefault("task", "embedding")

            self.logger.info(f"Loading vLLM embedding model '{model_id}' from {path}")
            self._embedding_engine = LLM(**engine_kwargs)  # type: ignore[operator-not-callable]
            return self._embedding_engine

    def _normalize_prompts(
        self, prompts: str | dict[str, Any] | Sequence[str | dict[str, Any]]
    ) -> list[str]:
        if isinstance(prompts, (str, dict)):
            prompts = [prompts]
        normalized: list[str] = []
        for item in prompts:
            if isinstance(item, str):
                normalized.append(item)
            elif isinstance(item, dict):
                normalized.append(self._messages_to_prompt([item]))
            elif isinstance(item, Sequence):
                normalized.append(self._messages_to_prompt(item))
            else:
                normalized.append(str(item))
        return normalized

    def _messages_to_prompt(self, messages: Iterable[Any]) -> str:
        lines: list[str] = []
        for message in messages:
            if isinstance(message, dict):
                role = message.get("role", "user")
                content = message.get("content", "")
                lines.append(f"{role}: {content}")
            else:
                lines.append(str(message))
        return "\n".join(lines)

    def _normalize_texts(self, texts: str | Sequence[str]) -> list[str]:
        if isinstance(texts, str):
            return [texts]
        return [str(text) for text in texts]

    def _merge_sampling_params(self, overrides: dict[str, Any]) -> SamplingParams:  # type: ignore
        merged = dict(_DEFAULT_SAMPLING)
        merged.update(self.config.sampling)
        merged.update({k: v for k, v in overrides.items() if v is not None})
        filtered = {k: v for k, v in merged.items() if v is not None}
        return self._build_sampling_params(filtered)

    def _build_sampling_params(self, params: dict[str, Any]) -> SamplingParams:  # type: ignore
        if SamplingParams is None:
            raise RuntimeError("vLLM is not installed; cannot create SamplingParams")
        return SamplingParams(**params)


def register_vllm_service(environment: Any, service_name: str, config: dict[str, Any]) -> Any:
    """Helper to register the vLLM service with a SAGE environment."""

    return environment.register_service(service_name, VLLMService, config)


__all__ = ["VLLMService", "VLLMServiceConfig", "register_vllm_service"]
