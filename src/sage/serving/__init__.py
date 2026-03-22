"""Serving integration boundary for SAGE.

This package intentionally does not implement an inference engine.
Instead, it standardizes how SAGE integrates with the independent
`isagellm` engine family.
"""

from .gateway import (
    GatewayProbeResult,
    SageServeConfig,
    build_sagellm_gateway_command,
    default_gateway_config,
    ensure_sagellm_model,
    gateway_health_url,
    gateway_openai_base_url,
    infer_module_availability,
    probe_gateway,
)

__all__ = [
    "SageServeConfig",
    "GatewayProbeResult",
    "default_gateway_config",
    "gateway_health_url",
    "gateway_openai_base_url",
    "build_sagellm_gateway_command",
    "infer_module_availability",
    "probe_gateway",
    "ensure_sagellm_model",
]
