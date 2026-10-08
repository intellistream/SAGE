from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

FLOW_PROGRAM_SUBMIT_INVALID_MAPPING = "flow_program_submit_invalid_mapping"
FLOW_PROGRAM_SUBMIT_INVALID_TYPE = "flow_program_submit_invalid_type"
FLOW_PROGRAM_SUBMIT_INVALID_SCHEMA = "flow_program_submit_invalid_schema"
FLOW_PROGRAM_SUBMIT_INVALID_BINDING_KEY = "invalid_binding_key"

_DEFAULT_INGRESS_KIND = "manual_push"
_DEFAULT_EGRESS_KIND = "default"
_DEFAULT_EGRESS_MAPPING_KIND = "buffered"


class FlowProgramSubmitContractError(ValueError):
    """Stable validation error shape for submit-by-program input contracts."""

    def __init__(self, *, code: str, message: str):
        normalized_code = str(code or "").strip() or FLOW_PROGRAM_SUBMIT_INVALID_SCHEMA
        normalized_message = str(
            message or "FlowProgram submit contract validation failed."
        ).strip()
        self.code = normalized_code
        super().__init__(f"{normalized_code}: {normalized_message}")


def _raise_submit_contract_error(*, code: str, message: str) -> None:
    raise FlowProgramSubmitContractError(code=code, message=message)


def normalize_flow_program_submit_accept(
    accept_payload: Any,
    *,
    target_node: str,
) -> dict[str, Any]:
    if isinstance(accept_payload, Mapping):
        normalized = dict(accept_payload)
    else:
        normalized = {"descriptor": accept_payload}

    run_id = str(normalized.get("run_id") or "").strip()
    if not run_id:
        descriptor = normalized.get("descriptor")
        if isinstance(descriptor, Mapping):
            run_id = str(descriptor.get("run_id") or "").strip()
    if not run_id:
        raise RuntimeError("submit_flow_program_accept payload missing run_id.")

    normalized["run_id"] = run_id
    normalized["target_node"] = str(target_node or "").strip()
    normalized.setdefault("accept_schema", "flow_program_submit_accept.v1")
    return normalized


def prepare_flow_program_submit_inputs(
    *,
    io_contract: Mapping[str, Any] | None,
    bindings: Mapping[str, Any] | None,
    ingress: Any = None,
    egress: Any = None,
    run_config: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, Any, Any, dict[str, Any]]:
    contract = _normalize_io_contract(io_contract)
    connector_defaults = contract.get("connector_defaults")
    if connector_defaults is not None and not isinstance(connector_defaults, Mapping):
        _raise_submit_contract_error(
            code=FLOW_PROGRAM_SUBMIT_INVALID_MAPPING,
            message="io_contract.connector_defaults must be a mapping when provided.",
        )

    effective_ingress = ingress
    effective_egress = egress
    if isinstance(connector_defaults, Mapping):
        if effective_ingress is None:
            effective_ingress = connector_defaults.get("ingress")
        if effective_egress is None:
            effective_egress = connector_defaults.get("egress")

    normalized_bindings = _normalize_bindings(bindings)
    _validate_binding_schema(contract, normalized_bindings)
    _validate_connector_compatibility(
        contract,
        ingress=effective_ingress,
        egress=effective_egress,
    )
    effective_run_config = _normalize_run_config(run_config)
    return normalized_bindings, effective_ingress, effective_egress, effective_run_config


def _normalize_io_contract(io_contract: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if io_contract is None:
        return {}
    if not isinstance(io_contract, Mapping):
        _raise_submit_contract_error(
            code=FLOW_PROGRAM_SUBMIT_INVALID_MAPPING,
            message="io_contract must be a mapping when provided.",
        )
    return io_contract


def _normalize_bindings(bindings: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if bindings is None:
        return None
    if not isinstance(bindings, Mapping):
        _raise_submit_contract_error(
            code=FLOW_PROGRAM_SUBMIT_INVALID_MAPPING,
            message="bindings must be a mapping when provided.",
        )
    normalized: dict[str, Any] = {}
    for raw_key, value in bindings.items():
        key = str(raw_key).strip()
        if not key:
            _raise_submit_contract_error(
                code=FLOW_PROGRAM_SUBMIT_INVALID_BINDING_KEY,
                message="bindings keys must be non-empty strings.",
            )
        normalized[key] = value
    return normalized


def _normalize_run_config(run_config: Mapping[str, Any] | None) -> dict[str, Any]:
    if run_config is None:
        return {}
    if not isinstance(run_config, Mapping):
        _raise_submit_contract_error(
            code=FLOW_PROGRAM_SUBMIT_INVALID_MAPPING,
            message="run_config must be a mapping when provided.",
        )
    return dict(run_config)


def _first_present(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in mapping:
            return mapping.get(key)
    return None


def _coerce_string_set(name: str, raw_value: Any) -> set[str]:
    if raw_value is None:
        return set()
    items: Iterable[Any]
    if isinstance(raw_value, str):
        items = [raw_value]
    elif isinstance(raw_value, Mapping):
        _raise_submit_contract_error(
            code=FLOW_PROGRAM_SUBMIT_INVALID_SCHEMA,
            message=f"{name} must be a string or iterable of strings.",
        )
    elif isinstance(raw_value, Iterable):
        items = raw_value
    else:
        _raise_submit_contract_error(
            code=FLOW_PROGRAM_SUBMIT_INVALID_SCHEMA,
            message=f"{name} must be a string or iterable of strings.",
        )

    values: set[str] = set()
    for item in items:
        normalized = str(item).strip()
        if not normalized:
            _raise_submit_contract_error(
                code=FLOW_PROGRAM_SUBMIT_INVALID_SCHEMA,
                message=f"{name} must not contain empty values.",
            )
        values.add(normalized)
    return values


def _resolve_binding_schema(io_contract: Mapping[str, Any]) -> tuple[set[str], set[str] | None]:
    binding_schema = io_contract.get("binding_schema")
    if binding_schema is None:
        binding_schema = io_contract.get("bindings")
    if binding_schema is None:
        return set(), None
    if not isinstance(binding_schema, Mapping):
        _raise_submit_contract_error(
            code=FLOW_PROGRAM_SUBMIT_INVALID_MAPPING,
            message="io_contract.binding_schema must be a mapping when provided.",
        )

    required_raw = _first_present(
        binding_schema,
        ("required", "required_bindings", "required_keys"),
    )
    allowed_raw = _first_present(
        binding_schema,
        ("allowed", "allowed_bindings", "allowed_keys"),
    )

    required = _coerce_string_set("io_contract.binding_schema.required", required_raw)
    if allowed_raw is None:
        allowed = None
    else:
        allowed = _coerce_string_set("io_contract.binding_schema.allowed", allowed_raw)
    return required, allowed


def _validate_binding_schema(
    io_contract: Mapping[str, Any],
    bindings: Mapping[str, Any] | None,
) -> None:
    required, allowed = _resolve_binding_schema(io_contract)
    provided_keys = set(bindings.keys()) if bindings is not None else set()

    missing = sorted(required - provided_keys)
    if missing:
        _raise_submit_contract_error(
            code=FLOW_PROGRAM_SUBMIT_INVALID_SCHEMA,
            message=(
                "FlowProgram bindings missing required keys from io_contract: " + ", ".join(missing)
            ),
        )

    if allowed is not None:
        unexpected = sorted(provided_keys - allowed)
        if unexpected:
            _raise_submit_contract_error(
                code=FLOW_PROGRAM_SUBMIT_INVALID_BINDING_KEY,
                message=(
                    "FlowProgram bindings include keys not allowed by io_contract: "
                    + ", ".join(unexpected)
                ),
            )


def _resolve_allowed_connector_kinds(
    io_contract: Mapping[str, Any],
    *,
    direction: str,
) -> set[str] | None:
    direct_raw = io_contract.get(f"allowed_{direction}_kinds")
    compatibility = io_contract.get("connector_compatibility")
    if compatibility is None:
        compatibility = io_contract.get("connector_compat")

    if compatibility is not None and not isinstance(compatibility, Mapping):
        _raise_submit_contract_error(
            code=FLOW_PROGRAM_SUBMIT_INVALID_MAPPING,
            message="io_contract.connector_compatibility must be a mapping when provided.",
        )

    compat_raw = None
    if isinstance(compatibility, Mapping):
        compat_raw = _first_present(
            compatibility,
            (
                direction,
                f"{direction}_kinds",
                f"allowed_{direction}_kinds",
            ),
        )

    raw = compat_raw if compat_raw is not None else direct_raw
    if raw is None:
        return None
    return _coerce_string_set(
        f"io_contract.connector_compatibility.allowed_{direction}_kinds",
        raw,
    )


def _validate_connector_compatibility(
    io_contract: Mapping[str, Any],
    *,
    ingress: Any,
    egress: Any,
) -> None:
    def _resolve_kind(connector: Any, *, direction: str) -> str:
        try:
            return _resolve_connector_kind(connector, direction=direction)
        except (TypeError, ValueError) as exc:
            raise FlowProgramSubmitContractError(
                code=FLOW_PROGRAM_SUBMIT_INVALID_TYPE,
                message=(f"{direction} connector is invalid for submit_flow_program: {exc}"),
            ) from exc

    ingress_kind = _resolve_kind(ingress, direction="ingress")
    allowed_ingress = _resolve_allowed_connector_kinds(io_contract, direction="ingress")
    if allowed_ingress is not None:
        if ingress_kind not in allowed_ingress:
            allowed = ", ".join(sorted(allowed_ingress))
            _raise_submit_contract_error(
                code=FLOW_PROGRAM_SUBMIT_INVALID_SCHEMA,
                message=(
                    "Ingress connector kind is not allowed by io_contract: "
                    f"{ingress_kind!r} not in [{allowed}]"
                ),
            )

    egress_kind = _resolve_kind(egress, direction="egress")
    allowed_egress = _resolve_allowed_connector_kinds(io_contract, direction="egress")
    if allowed_egress is not None:
        if egress_kind not in allowed_egress:
            allowed = ", ".join(sorted(allowed_egress))
            _raise_submit_contract_error(
                code=FLOW_PROGRAM_SUBMIT_INVALID_SCHEMA,
                message=(
                    "Egress connector kind is not allowed by io_contract: "
                    f"{egress_kind!r} not in [{allowed}]"
                ),
            )


def _resolve_connector_kind(connector: Any, *, direction: str) -> str:
    if direction not in {"ingress", "egress"}:
        raise ValueError(f"Unsupported connector direction: {direction!r}")

    if connector is None:
        return _DEFAULT_INGRESS_KIND if direction == "ingress" else _DEFAULT_EGRESS_KIND
    if isinstance(connector, str):
        return connector
    if isinstance(connector, Mapping):
        default_kind = (
            _DEFAULT_INGRESS_KIND if direction == "ingress" else _DEFAULT_EGRESS_MAPPING_KIND
        )
        kind = connector.get("kind")
        if kind is None:
            kind = default_kind
        if not isinstance(kind, str) or not kind:
            raise ValueError("Connector kind must be a non-empty string.")
        return kind
    kind = getattr(connector, "kind", None)
    if isinstance(kind, str):
        return kind
    raise TypeError(f"Unsupported {direction} connector type: {type(connector)}")


__all__ = [
    "FlowProgramSubmitContractError",
    "FLOW_PROGRAM_SUBMIT_INVALID_BINDING_KEY",
    "FLOW_PROGRAM_SUBMIT_INVALID_MAPPING",
    "FLOW_PROGRAM_SUBMIT_INVALID_SCHEMA",
    "FLOW_PROGRAM_SUBMIT_INVALID_TYPE",
    "normalize_flow_program_submit_accept",
    "prepare_flow_program_submit_inputs",
]
