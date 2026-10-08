from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from sage.foundation import SagePorts, ensure_model_available, get_user_paths


@dataclass(frozen=True)
class SageServeConfig:
    """SAGE-side integration config for an external `isagellm` gateway."""

    host: str = "127.0.0.1"
    port: int = SagePorts.SAGELLM_GATEWAY
    log_level: str = "info"
    model: str | None = None
    enable_control_plane: bool = False
    engine_model_env: str = "SAGELLM_ENGINE_MODEL"
    gateway_module: str = "sagellm_gateway"
    health_path: str = "/health"
    openai_base_path: str = "/v1"
    extra_env: dict[str, str] = field(default_factory=dict)

    @property
    def base_url(self) -> str:
        return gateway_openai_base_url(self.host, self.port, self.openai_base_path)

    @property
    def health_url(self) -> str:
        return gateway_health_url(self.host, self.port, self.health_path)

    @property
    def log_file(self) -> Path:
        return get_user_paths().get_log_file("sagellm_gateway")


@dataclass(frozen=True)
class GatewayProbeResult:
    """Observed status of an external `isagellm` gateway instance."""

    ok: bool
    url: str
    status_code: int | None = None
    payload: dict[str, Any] | None = None
    error: str | None = None


def default_gateway_config(
    host: str = "127.0.0.1",
    port: int = SagePorts.SAGELLM_GATEWAY,
    model: str | None = None,
    *,
    enable_control_plane: bool = False,
    log_level: str = "info",
) -> SageServeConfig:
    """Create a default SAGE→isagellm integration config."""
    return SageServeConfig(
        host=host,
        port=port,
        model=model,
        enable_control_plane=enable_control_plane,
        log_level=log_level,
    )


def gateway_openai_base_url(
    host: str = "127.0.0.1",
    port: int = SagePorts.SAGELLM_GATEWAY,
    base_path: str = "/v1",
) -> str:
    """Return the OpenAI-compatible base URL exposed by `isagellm`."""
    normalized = base_path if base_path.startswith("/") else f"/{base_path}"
    return f"http://{host}:{port}{normalized}"


def gateway_health_url(
    host: str = "127.0.0.1",
    port: int = SagePorts.SAGELLM_GATEWAY,
    health_path: str = "/health",
) -> str:
    """Return the health-check URL exposed by `isagellm`."""
    normalized = health_path if health_path.startswith("/") else f"/{health_path}"
    return f"http://{host}:{port}{normalized}"


def infer_module_availability(module_name: str = "sagellm_gateway") -> bool:
    """Return whether the gateway integration module is importable."""
    return find_spec(module_name) is not None


def build_sagellm_gateway_command(config: SageServeConfig) -> list[str]:
    """Build the command used to launch the external `isagellm` gateway.

    SAGE does not implement the gateway itself; it only constructs the
    integration command and environment contract.
    """
    cmd = [
        sys.executable,
        "-m",
        config.gateway_module,
        "--host",
        config.host,
        "--port",
        str(config.port),
        "--log-level",
        config.log_level,
    ]
    if config.enable_control_plane:
        cmd.append("--control-plane")
    return cmd


def build_sagellm_gateway_env(config: SageServeConfig) -> dict[str, str]:
    """Build the environment contract used to launch `isagellm`."""
    env = dict(os.environ)
    if config.model:
        env[config.engine_model_env] = config.model
    env.update(config.extra_env)
    return env


def ensure_sagellm_model(model_id: str, *, auto_download: bool = True) -> Path:
    """Ensure the external `isagellm` engine model exists locally.

    SAGE owns the local model asset registry/integration workflow, while the
    inference engine itself remains external.
    """
    return ensure_model_available(model_id, auto_download=auto_download)


def probe_gateway(config: SageServeConfig, timeout: float = 3.0) -> GatewayProbeResult:
    """Probe the health endpoint of an external `isagellm` gateway."""
    request = urllib.request.Request(config.health_url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            payload = None
            try:
                payload = json.loads(body) if body else None
            except json.JSONDecodeError:
                payload = None
            return GatewayProbeResult(
                ok=200 <= response.status < 300,
                url=config.health_url,
                status_code=response.status,
                payload=payload,
            )
    except urllib.error.HTTPError as exc:
        return GatewayProbeResult(
            ok=False,
            url=config.health_url,
            status_code=exc.code,
            error=str(exc),
        )
    except urllib.error.URLError as exc:
        return GatewayProbeResult(ok=False, url=config.health_url, error=str(exc.reason))
    except TimeoutError:
        return GatewayProbeResult(ok=False, url=config.health_url, error="timed out")
    except OSError as exc:
        return GatewayProbeResult(ok=False, url=config.health_url, error=str(exc))
