"""Intelligent LLM Client with auto-detection and fallback support.

Layer: L1 (Foundation - Common Components)

This module provides a unified LLM client that:
- Auto-detects local vLLM services (OpenAI-compatible endpoints)
- Falls back to cloud APIs if local services are unavailable
- Supports OpenAI-compatible APIs (vLLM, Ollama, DashScope, etc.)
- Optionally integrates with Control Plane for advanced scheduling

Architecture:
    - L1 component: Can be used by all higher layers
    - No dependencies on L2+ layers
    - Minimal external dependencies (only openai package)
    - Optional integration with sageLLM Control Plane

Usage Modes:
    1. Simple Mode: Direct OpenAI-compatible API calls (default)
    2. Control Plane Mode: Advanced scheduling via sageLLM Control Plane (optional)

Example:
    >>> from sage.common.components.sage_llm.client import IntelligentLLMClient
    >>>
    >>> # Simple mode - Auto-detect and use best available service
    >>> client = IntelligentLLMClient.create_auto()
    >>> response = client.chat([
    ...     {"role": "user", "content": "Hello!"}
    ... ])
    >>>
    >>> # Control Plane mode - Advanced scheduling (if available)
    >>> client = IntelligentLLMClient.create_with_control_plane(
    ...     instances=[
    ...         {"host": "localhost", "port": 8001, "model_name": "llama-2-7b"},
    ...         {"host": "localhost", "port": 8002, "model_name": "llama-2-13b"},
    ...     ],
    ...     scheduling_policy="slo_aware"
    ... )
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib import error, request

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore

# Optional: Control Plane integration
try:
    from sage.common.components.sage_llm.control_plane_service import (
        ControlPlaneVLLMService,
        ControlPlaneVLLMServiceConfig,
    )

    CONTROL_PLANE_AVAILABLE = True
except ImportError:
    CONTROL_PLANE_AVAILABLE = False
    ControlPlaneVLLMService = None  # type: ignore
    ControlPlaneVLLMServiceConfig = None  # type: ignore


class IntelligentLLMClient:
    """Intelligent LLM client with auto-detection and cloud fallback.

    This client supports two modes:
    1. **Simple Mode** (default): Direct OpenAI-compatible API calls
       - Auto-detects local vLLM services
       - Falls back to cloud API
       - Lightweight, fast startup

    2. **Control Plane Mode** (optional): Advanced scheduling via sageLLM
       - Multi-instance load balancing
       - SLO-aware scheduling
       - Prefilling/Decoding separation
       - Topology-aware routing
       - Requires Control Plane setup

    Priority (Simple Mode):
        1. User-configured endpoint (SAGE_CHAT_BASE_URL)
        2. Local vLLM on port 8001 (recommended, avoids Gateway conflict)
        3. Local vLLM on port 8000 (vLLM default)
        4. Cloud API (DashScope default)
    """

    def __init__(
        self,
        model_name: str,
        base_url: str,
        api_key: str = "",
        timeout: int = 60,
        seed: int | None = None,
        use_control_plane: bool = False,
        control_plane_service: Any = None,
        **kwargs: Any,
    ):
        """Initialize LLM client with specific configuration.

        Args:
            model_name: Model identifier (e.g., "qwen-max", "meta-llama/Llama-2-7b")
            base_url: OpenAI-compatible API endpoint
            api_key: API key (use "empty" or "" for local services)
            timeout: Request timeout in seconds
            seed: Random seed for reproducibility (stored but not always enforced)
            use_control_plane: Enable Control Plane mode (requires setup)
            control_plane_service: Pre-configured Control Plane service instance
            **kwargs: Additional arguments passed to OpenAI client
        """
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key or "empty"
        self.timeout = timeout
        self.seed = seed  # Store for compatibility
        self.use_control_plane = use_control_plane
        self._control_plane_service = control_plane_service

        # Initialize OpenAI client (Simple Mode)
        if not use_control_plane:
            if OpenAI is None:
                raise ImportError("openai package is required. Install with: pip install openai")

            self.client = OpenAI(
                base_url=base_url,
                api_key=self.api_key,
                timeout=timeout,
                **kwargs,
            )

            # Log configuration
            if "localhost" in base_url or "127.0.0.1" in base_url:
                logger.info(f"✅ 初始化本地 LLM 客户端: {model_name} @ {base_url}")
            else:
                logger.info(f"☁️  初始化云端 LLM 客户端: {model_name} @ {base_url}")
        else:
            # Control Plane mode
            if not CONTROL_PLANE_AVAILABLE:
                raise RuntimeError(
                    "Control Plane mode requires sageLLM Control Plane. "
                    "Please ensure the control_plane module is installed."
                )
            if control_plane_service is None:
                raise ValueError(
                    "Control Plane mode requires a pre-configured control_plane_service. "
                    "Use IntelligentLLMClient.create_with_control_plane() instead."
                )
            logger.info(f"🎯 初始化 Control Plane LLM 客户端: {model_name}")

    @classmethod
    def create_with_control_plane(
        cls,
        instances: list[dict[str, Any]],
        scheduling_policy: str = "adaptive",
        routing_strategy: str = "load_balanced",
        enable_pd_separation: bool = True,
        **kwargs: Any,
    ) -> IntelligentLLMClient:
        """Create client with Control Plane for advanced multi-instance scheduling.

        This mode enables:
        - Multi-instance load balancing
        - SLO-aware scheduling (priority, deadlines)
        - Prefilling/Decoding separation
        - Topology-aware routing (NVLINK, NUMA)
        - Performance monitoring

        Args:
            instances: List of instance configurations, e.g.:
                [
                    {
                        "host": "localhost",
                        "port": 8001,
                        "model_name": "llama-2-7b",
                        "instance_type": "PREFILL",  # Optional
                        "gpu_count": 1,              # Optional
                    },
                    {
                        "host": "localhost",
                        "port": 8002,
                        "model_name": "llama-2-13b",
                        "instance_type": "DECODE",
                    },
                ]
            scheduling_policy: One of: adaptive, slo_aware, priority, fifo, cost_optimized
            routing_strategy: One of: load_balanced, affinity, locality, topology_aware
            enable_pd_separation: Enable Prefilling/Decoding separation optimization
            **kwargs: Additional Control Plane configuration

        Returns:
            IntelligentLLMClient configured with Control Plane

        Example:
            >>> client = IntelligentLLMClient.create_with_control_plane(
            ...     instances=[
            ...         {"host": "localhost", "port": 8001, "model_name": "llama-2-7b"},
            ...         {"host": "localhost", "port": 8002, "model_name": "llama-2-13b"},
            ...     ],
            ...     scheduling_policy="slo_aware"
            ... )
            >>> response = client.chat(
            ...     messages=[{"role": "user", "content": "Hello!"}],
            ...     priority="HIGH",
            ...     slo_deadline_ms=1000
            ... )
        """
        if not CONTROL_PLANE_AVAILABLE:
            raise RuntimeError(
                "Control Plane mode requires sageLLM Control Plane. "
                "Please ensure the control_plane module is installed."
            )

        # Create Control Plane service configuration
        cp_config = {
            "scheduling_policy": scheduling_policy,
            "routing_strategy": routing_strategy,
            "enable_pd_separation": enable_pd_separation,
            "instances": instances,
            **kwargs,
        }

        # Create and setup Control Plane service
        cp_service = ControlPlaneVLLMService(cp_config)
        cp_service.setup()

        # Extract model name from first instance
        model_name = instances[0].get("model_name", "unknown") if instances else "unknown"

        return cls(
            model_name=model_name,
            base_url="control-plane://multi-instance",  # Placeholder
            api_key="",
            use_control_plane=True,
            control_plane_service=cp_service,
        )

    @classmethod
    def create_auto(
        cls,
        model_name: str | None = None,
        probe_timeout: float = 1.5,
        **kwargs: Any,
    ) -> IntelligentLLMClient:
        """Auto-detect and create client with best available service.

        Detection logic:
        1. Check SAGE_CHAT_BASE_URL env var (user override)
        2. Probe local vLLM services (8001, 8000)
        3. Fall back to cloud API

        Args:
            model_name: Optional model override (uses env var or detected model)
            probe_timeout: Timeout for local service detection (seconds)
            **kwargs: Additional arguments passed to client

        Returns:
            Configured IntelligentLLMClient instance
        """
        config = cls._detect_llm_config(model_name, probe_timeout)
        return cls(
            model_name=config["model_name"],
            base_url=config["base_url"],
            api_key=config["api_key"],
            **kwargs,
        )

    @staticmethod
    def _detect_llm_config(
        model_override: str | None = None,
        probe_timeout: float = 1.5,
    ) -> dict[str, str]:
        """Detect best available LLM service configuration.

        Args:
            model_override: Override model name (takes precedence)
            probe_timeout: Timeout for probing local services

        Returns:
            Dict with 'model_name', 'base_url', 'api_key'
        """
        # Read environment variables
        # Fallback to standard OPENAI_* variables if SAGE_CHAT_* are not set
        user_base_url = os.getenv("SAGE_CHAT_BASE_URL") or os.getenv("OPENAI_BASE_URL")
        user_model = (
            model_override or os.getenv("SAGE_CHAT_MODEL") or os.getenv("OPENAI_MODEL_NAME")
        )
        user_api_key = os.getenv("SAGE_CHAT_API_KEY") or os.getenv("OPENAI_API_KEY", "")

        logger.debug("🔍 [LLM Detection] Starting detection...")
        logger.debug(f"🔍 [LLM Detection] SAGE_CHAT_BASE_URL={user_base_url}")
        logger.debug(f"🔍 [LLM Detection] SAGE_CHAT_MODEL={user_model}")
        logger.debug(
            f"🔍 [LLM Detection] SAGE_CHAT_API_KEY={'***' if user_api_key else '(not set)'}"
        )

        # Strategy: Local-first, cloud fallback
        # 1. If SAGE_CHAT_BASE_URL is set to localhost, use it directly
        # 2. Try to auto-detect local vLLM services (even if cloud API keys are set)
        # 3. If SAGE_CHAT_BASE_URL is set to remote, use it
        # 4. Fall back to default cloud API

        # Priority 1: User explicitly configured local endpoint
        if user_base_url:
            is_local = "localhost" in user_base_url or "127.0.0.1" in user_base_url
            if is_local:
                model_name = user_model or "local-model"
                api_key = user_api_key or ""
                logger.info(f"✅ 使用配置的本地服务: {model_name} @ {user_base_url}")
                return {
                    "model_name": model_name,
                    "base_url": user_base_url,
                    "api_key": api_key,
                }

        # Priority 2: Auto-detect local vLLM services (本地优先策略)
        logger.info("🔍 优先检测本地 LLM 服务...")
        local_endpoints = [
            "http://localhost:8001/v1",  # Recommended (avoids Gateway port 8000)
            "http://127.0.0.1:8001/v1",
            "http://localhost:8000/v1",  # vLLM default
            "http://127.0.0.1:8000/v1",
        ]

        for endpoint in local_endpoints:
            logger.debug(f"🔍 [LLM Detection] Probing {endpoint}...")
            detected_model = IntelligentLLMClient._probe_vllm_service(
                endpoint, timeout=probe_timeout
            )
            if detected_model:
                model_name = model_override or detected_model
                # For local vLLM, match server's auth setting
                # If VLLM_API_KEY is set, use it; otherwise use empty string (no auth)
                local_api_key = os.getenv("VLLM_API_KEY", "")
                logger.info(f"✅ 自动检测到本地 vLLM: {model_name} @ {endpoint}")
                logger.info("💡 使用本地服务，节省 API 成本")
                return {
                    "model_name": model_name,
                    "base_url": endpoint,
                    "api_key": local_api_key,
                }

        # Priority 3: User configured remote cloud endpoint
        if user_base_url:
            # Remote endpoint (already checked local above)
            model_name = user_model or "qwen-max"
            api_key = user_api_key or ""
            if not api_key:
                logger.warning("SAGE_CHAT_API_KEY 未设置，云端服务可能无法使用")
            logger.info(f"☁️  使用配置的云端服务: {model_name} @ {user_base_url}")
            return {
                "model_name": model_name,
                "base_url": user_base_url,
                "api_key": api_key,
            }

        # Priority 4: Fall back to default cloud API
        logger.info("☁️  未检测到本地服务，降级到默认云端 API")
        cloud_model = user_model or "qwen-max"
        cloud_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

        if not user_api_key:
            logger.warning(
                "SAGE_CHAT_API_KEY 未设置，云端服务可能无法使用。"
                "请设置环境变量或启动本地 vLLM 服务。"
            )

        return {
            "model_name": cloud_model,
            "base_url": cloud_url,
            "api_key": user_api_key,
        }

    @staticmethod
    def _probe_vllm_service(base_url: str, timeout: float = 1.5) -> str | None:
        """Probe local vLLM service and return available model name.

        Args:
            base_url: vLLM OpenAI-compatible endpoint (e.g., http://localhost:8001/v1)
            timeout: Probe timeout in seconds

        Returns:
            Model name if service is available, None otherwise
        """
        try:
            models_url = f"{base_url.rstrip('/')}/models"
            req = request.Request(models_url)
            with request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [item.get("id") for item in data.get("data", []) if item.get("id")]
                if models:
                    logger.debug(f"🔍 [LLM Detection] ✅ Found models at {base_url}: {models[0]}")
                    return models[0]  # Return first available model
                else:
                    logger.debug(f"🔍 [LLM Detection] ❌ No models found at {base_url}")
        except (TimeoutError, error.URLError, json.JSONDecodeError, KeyError, Exception) as e:
            logger.debug(f"🔍 [LLM Detection] ❌ Failed to probe {base_url}: {type(e).__name__}")
            pass  # Service unavailable, fail silently
        return None

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1500,
        stream: bool = False,
        priority: str | None = None,
        slo_deadline_ms: int | None = None,
        enable_thinking: bool = False,
        logprobs: bool = False,
        n: int = 1,
        **kwargs: Any,
    ) -> str | tuple[str, list] | list | Any:
        """Generate chat completion.

        Args:
            messages: Chat messages in OpenAI format
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens to generate
            stream: Enable streaming response
            priority: Request priority (Control Plane mode only): HIGH, NORMAL, LOW
            slo_deadline_ms: SLO deadline in milliseconds (Control Plane mode only)
            enable_thinking: Enable Qwen thinking mode (for DashScope/Qwen models)
            logprobs: Return log probabilities with response
            n: Number of candidate responses to generate
            **kwargs: Additional OpenAI API parameters

        Returns:
            - If stream=True: Generator/Iterator
            - If logprobs=True and n=1: (text, logprobs_list)
            - If logprobs=True and n>1: [(text, logprobs_list), ...]
            - If n=1: text (string)
            - If n>1: [text, text, ...] (list of strings)

        Raises:
            RuntimeError: If API call fails
        """
        # Control Plane mode
        if self.use_control_plane and self._control_plane_service:
            # Build prompt from messages (simplified)
            prompt = self._messages_to_prompt(messages)

            # Prepare options for Control Plane
            options = {
                "max_tokens": max_tokens,
                "temperature": temperature,
                **kwargs,
            }
            if priority:
                options["priority"] = priority
            if slo_deadline_ms:
                options["slo_deadline_ms"] = slo_deadline_ms

            # Call Control Plane service
            return self._control_plane_service.generate(prompt, **options)

        # Simple mode - Direct OpenAI API
        try:
            # Prepare request parameters
            request_params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream,
                "n": n,
            }

            # Add Qwen thinking mode if enabled (via extra_body)
            if enable_thinking:
                request_params["extra_body"] = {"chat_template_kwargs": {"enable_thinking": True}}

            # Add logprobs if requested
            if logprobs:
                request_params["logprobs"] = True

            # Add additional kwargs
            request_params.update(kwargs)

            response = self.client.chat.completions.create(**request_params)

            if stream:
                return response  # Return generator for streaming

            # Extract responses
            def _extract(choice):
                text = choice.message.content
                if logprobs and hasattr(choice, "logprobs") and choice.logprobs:
                    logits = [lp.logprob for lp in choice.logprobs.content]
                    return text, logits
                return text

            # Handle multiple candidates (n > 1)
            if n == 1:
                return _extract(response.choices[0])
            else:
                return [_extract(c) for c in response.choices]

        except Exception as e:
            logger.error(f"LLM chat 调用失败: {e}", exc_info=True)
            raise RuntimeError(f"LLM chat 调用失败: {e}") from e

    def _messages_to_prompt(self, messages: list[dict[str, str]]) -> str:
        """Convert OpenAI-style messages to a simple prompt string.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Formatted prompt string
        """
        lines = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def generate(
        self,
        messages: list[dict[str, str]] | dict[str, str],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        max_new_tokens: int | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> str | tuple[str, list] | list | Any:
        """Generate completion (alias for chat method for compatibility).

        Provides compatibility with existing code using `generate()` method.
        Also supports `max_new_tokens` as alias for `max_tokens`.

        Args:
            messages: Chat messages (list[dict] or single dict)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            max_new_tokens: Alias for max_tokens (for compatibility)
            stream: Enable streaming
            **kwargs: Additional parameters (enable_thinking, logprobs, n, etc.)

        Returns:
            Same as chat() method
        """
        # Normalize messages to list
        if isinstance(messages, dict):
            messages = [messages]

        # Handle max_tokens aliases
        tokens_limit = max_tokens or max_new_tokens or 1500

        return self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=tokens_limit,
            stream=stream,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Control Plane specific methods
    # ------------------------------------------------------------------
    def get_instances(self) -> list[dict[str, Any]] | None:
        """Get information about registered instances (Control Plane mode only).

        Returns:
            List of instance information dicts, or None if not in Control Plane mode
        """
        if self.use_control_plane and self._control_plane_service:
            return self._control_plane_service.show_instances()
        return None

    def get_metrics(self) -> dict[str, Any] | None:
        """Get performance metrics (Control Plane mode only).

        Returns:
            Metrics dict with latency, throughput, SLO compliance, etc.
            None if not in Control Plane mode
        """
        if self.use_control_plane and self._control_plane_service:
            return self._control_plane_service.get_metrics()
        return None

    def health_check(self) -> dict[str, Any]:
        """Check health status of the client.

        Returns:
            Health status dict with availability and instance info
        """
        if self.use_control_plane and self._control_plane_service:
            # Control Plane mode - check all instances
            instances = self._control_plane_service.show_instances()
            healthy_count = sum(1 for inst in instances if inst.get("is_healthy", False))
            return {
                "mode": "control_plane",
                "total_instances": len(instances),
                "healthy_instances": healthy_count,
                "available": healthy_count > 0,
                "instances": instances,
            }
        else:
            # Simple mode - check if client is configured
            return {
                "mode": "simple",
                "model_name": self.model_name,
                "base_url": self.base_url,
                "available": self.client is not None,
            }

    def cleanup(self) -> None:
        """Cleanup resources (important for Control Plane mode).

        Should be called when client is no longer needed, especially in Control Plane mode.
        """
        if self.use_control_plane and self._control_plane_service:
            logger.info("Cleaning up Control Plane service")
            self._control_plane_service.cleanup()
            self._control_plane_service = None


__all__ = ["IntelligentLLMClient"]
