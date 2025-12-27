from __future__ import annotations

import logging
from typing import Any, Iterable, Mapping, Optional

import requests

from sage.common.config.ports import SagePorts

logger = logging.getLogger(__name__)


def _default_base_url() -> str:
    """Return the default Control Plane endpoint using loopback."""

    return f"http://127.0.0.1:{SagePorts.GATEWAY_DEFAULT}/v1"


class UnifiedInferenceClient:
    """Minimal client that always routes through the Control Plane."""

    def __init__(
        self,
        base_url: str,
        default_llm_model: Optional[str] = None,
        default_embedding_model: Optional[str] = None,
        timeout: int = 60,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_llm_model = default_llm_model
        self.default_embedding_model = default_embedding_model
        self.timeout = timeout
        self.session = session or requests.Session()

    @classmethod
    def create(
        cls,
        control_plane_url: Optional[str] = None,
        default_llm_model: Optional[str] = None,
        default_embedding_model: Optional[str] = None,
        timeout: int = 60,
        session: Optional[requests.Session] = None,
    ) -> UnifiedInferenceClient:
        """Create a client that talks to the Control Plane endpoint only."""

        base_url = control_plane_url or _default_base_url()
        if "localhost" in base_url:
            base_url = base_url.replace("localhost", "127.0.0.1")
        return cls(
            base_url=base_url,
            default_llm_model=default_llm_model,
            default_embedding_model=default_embedding_model,
            timeout=timeout,
            session=session,
        )

    @classmethod
    def create_with_control_plane(
        cls,
        control_plane_url: Optional[str] = None,
        default_llm_model: Optional[str] = None,
        default_embedding_model: Optional[str] = None,
        timeout: int = 60,
        session: Optional[requests.Session] = None,
    ) -> UnifiedInferenceClient:
        """Alias for create() to match prior API."""

        return cls.create(
            control_plane_url=control_plane_url,
            default_llm_model=default_llm_model,
            default_embedding_model=default_embedding_model,
            timeout=timeout,
            session=session,
        )

    def chat(
        self,
        messages: Iterable[Mapping[str, Any]],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> Mapping[str, Any]:
        payload: dict[str, Any] = {
            "messages": list(messages),
            "model": model or self.default_llm_model,
        }
        payload.update(kwargs)
        return self._post_json("/chat/completions", payload)

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> Mapping[str, Any]:
        payload: dict[str, Any] = {
            "prompt": prompt,
            "model": model or self.default_llm_model,
        }
        payload.update(kwargs)
        return self._post_json("/completions", payload)

    def embed(
        self,
        texts: Iterable[str],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> Mapping[str, Any]:
        payload: dict[str, Any] = {
            "input": list(texts),
            "model": model or self.default_embedding_model,
        }
        payload.update(kwargs)
        return self._post_json("/embeddings", payload)

    def models(self) -> Mapping[str, Any]:
        return self._get_json("/models")

    def _post_json(self, path: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        logger.debug("POST %s", url)
        response = self.session.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _get_json(self, path: str) -> Mapping[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        logger.debug("GET %s", url)
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()


__all__ = ["UnifiedInferenceClient"]
