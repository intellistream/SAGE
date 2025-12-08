"""Helpers for detecting locally running LLM services.

This module provides lightweight HTTP probes that discover OpenAI-compatible
endpoints exposed by popular local deployments such as Ollama and vLLM. The
resulting metadata can be used to auto-populate generator configuration blocks.
"""

from __future__ import annotations

import json
import ssl
from collections.abc import Iterable
from dataclasses import dataclass
from urllib import error, request

from sage.common.config.ports import SagePorts


@dataclass
class LLMServiceInfo:
    """Metadata describing a detected LLM service."""

    name: str
    base_url: str
    models: list[str]
    default_model: str
    generator_section: str
    description: str


DEFAULT_TIMEOUT = 2  # seconds


def _safe_http_get(
    url: str, timeout: int = DEFAULT_TIMEOUT, auth_token: str | None = None
) -> str | None:
    """Best-effort HTTP GET that returns response text or ``None`` on failure."""

    req = request.Request(url)
    if auth_token:
        req.add_header("Authorization", f"Bearer {auth_token}")

    try:
        with request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset)
    except (TimeoutError, error.URLError, ssl.SSLError):
        return None


def _ssl_context() -> ssl.SSLContext | None:
    """Create a default SSL context while remaining compatible with older Python."""

    try:
        return ssl.create_default_context()
    except AttributeError:  # pragma: no cover - extremely old Python
        return None


def detect_ollama(
    base_urls: Iterable[str] | None = None,
) -> LLMServiceInfo | None:
    """Detect a running Ollama service by probing the tags endpoint."""

    if base_urls is None:
        base_urls = (
            "http://127.0.0.1:11434",
            "http://localhost:11434",
            "http://0.0.0.0:11434",
        )

    for host in base_urls:
        payload = _safe_http_get(f"{host}/api/tags")
        if not payload:
            continue

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue

        models = [model["name"] for model in data.get("models", []) if "name" in model]
        if not models:
            continue

        default_model = models[0]
        return LLMServiceInfo(
            name="ollama",
            base_url=f"{host}/v1",
            models=models,
            default_model=default_model,
            generator_section="remote",
            description=f"Ollama at {host}",
        )

    return None


def detect_vllm(
    base_urls: Iterable[str] | None = None, auth_token: str | None = None
) -> LLMServiceInfo | None:
    """Detect a running vLLM service by probing the OpenAI-compatible models API."""

    if base_urls is None:
        gateway_port = SagePorts.GATEWAY_DEFAULT
        base_urls = (
            f"http://127.0.0.1:{gateway_port}",
            f"http://localhost:{gateway_port}",
            f"http://0.0.0.0:{gateway_port}",
        )

    # If user provides auth_token, use it; otherwise try common defaults
    if auth_token is not None:
        auth_tokens = [auth_token]
    else:
        auth_tokens = [None, "token-abc123", "test-token", "vllm-token"]

    for host in base_urls:
        for token in auth_tokens:
            payload = _safe_http_get(f"{host}/v1/models", auth_token=token)
            if payload:
                break

        if not payload:
            continue

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue

        models = [item.get("id") for item in data.get("data", []) if item.get("id")]
        if not models:
            continue

        default_model = models[0]
        return LLMServiceInfo(
            name="vllm",
            base_url=f"{host}/v1",
            models=models,
            default_model=default_model,
            generator_section="vllm",
            description=f"vLLM at {host}",
        )

    return None


def detect_all_services(
    prefer: str | None = None, auth_token: str | None = None
) -> list[LLMServiceInfo]:
    """Detect all supported services, optionally restricting by name."""

    prefer_normalized = prefer.lower() if prefer else None
    detections: list[LLMServiceInfo] = []

    if prefer_normalized in (None, "ollama"):
        service = detect_ollama()
        if service:
            detections.append(service)

    if prefer_normalized in (None, "vllm"):
        service = detect_vllm(auth_token=auth_token)
        if service:
            detections.append(service)

    return detections
