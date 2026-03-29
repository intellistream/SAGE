from __future__ import annotations

import re
import uuid
from collections.abc import Callable, Mapping
from threading import Lock
from typing import Any

from sage.runtime.flownet.client.handles import RegistrationHandle, ResourceKind

_OWNER_SEGMENT_RE = re.compile(r"[^a-zA-Z0-9._-]+")


class SurfaceRegistry:
    """
    In-memory registration registry per client surface.

    Explicit URI registrations are discoverable. Anonymous registrations are
    owner-private and intentionally excluded from discoverable index.
    """

    def __init__(
        self,
        *,
        kind: ResourceKind,
        owner: str,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._kind = kind
        self._owner = _normalize_non_empty(owner, field_name="owner")
        self._id_factory = id_factory or (lambda: uuid.uuid4().hex)
        self._registrations: dict[str, RegistrationHandle] = {}
        self._discoverable_by_uri: dict[str, RegistrationHandle] = {}
        self._lock = Lock()

    @property
    def kind(self) -> ResourceKind:
        return self._kind

    def register(
        self,
        declaration: Any,
        *,
        uri: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> RegistrationHandle:
        if declaration is None:
            raise TypeError("declaration must not be None.")

        explicit_uri = _normalize_optional_uri(uri)
        if explicit_uri is None:
            explicit_uri = _normalize_optional_uri(
                _extract_declared_uri(declaration, kind=self._kind)
            )

        anonymous = explicit_uri is None
        discoverable = not anonymous
        owner_private = anonymous
        resolved_uri = explicit_uri or self._new_anonymous_uri()
        registration_id = _normalize_non_empty(self._id_factory(), field_name="registration_id")
        resolved_metadata = _merge_registration_metadata(
            declaration=declaration,
            metadata=metadata,
        )
        registration = RegistrationHandle(
            kind=self._kind,
            registration_id=registration_id,
            uri=resolved_uri,
            declaration=declaration,
            owner=self._owner,
            anonymous=anonymous,
            owner_private=owner_private,
            discoverable=discoverable,
            metadata=resolved_metadata,
        )

        with self._lock:
            if discoverable:
                existing = self._discoverable_by_uri.get(resolved_uri)
                if existing is not None and existing.declaration is not declaration:
                    existing_hash = _resolve_definition_hash(existing.metadata)
                    incoming_hash = _resolve_definition_hash(resolved_metadata)
                    if (
                        existing_hash is not None
                        and incoming_hash is not None
                        and existing_hash != incoming_hash
                    ):
                        raise ValueError(f"{self._kind}_definition_hash_mismatch:{resolved_uri}")
                    if (
                        existing_hash is not None
                        and incoming_hash is not None
                        and existing_hash == incoming_hash
                    ):
                        return existing
                    raise ValueError(f"{self._kind}_uri_already_registered:{resolved_uri}")
                if existing is not None:
                    return existing
                self._discoverable_by_uri[resolved_uri] = registration
            self._registrations[registration_id] = registration
        return registration

    def ensure_registration(
        self,
        declaration_or_registration: Any,
    ) -> tuple[RegistrationHandle, bool]:
        if isinstance(declaration_or_registration, RegistrationHandle):
            registration = declaration_or_registration
            if registration.kind != self._kind:
                raise TypeError(
                    f"registration kind mismatch: expected={self._kind}, actual={registration.kind}",
                )
            return registration, False
        return self.register(declaration_or_registration), True

    def get_discoverable(self, uri: str) -> RegistrationHandle | None:
        normalized_uri = _normalize_non_empty(uri, field_name="uri")
        with self._lock:
            return self._discoverable_by_uri.get(normalized_uri)

    def list_discoverable(self) -> list[RegistrationHandle]:
        with self._lock:
            records = list(self._discoverable_by_uri.values())
        records.sort(key=lambda item: item.uri)
        return records

    def list_registrations(self) -> list[RegistrationHandle]:
        with self._lock:
            records = list(self._registrations.values())
        records.sort(key=lambda item: item.registration_id)
        return records

    def _new_anonymous_uri(self) -> str:
        owner_segment = _normalize_owner_segment(self._owner)
        token = _normalize_non_empty(self._id_factory(), field_name="anonymous_token")
        return f"anon://{owner_segment}/{self._kind}/{token}"


def _extract_declared_uri(declaration: Any, *, kind: ResourceKind) -> str | None:
    field_names: tuple[str, ...]
    if kind == "flow":
        field_names = ("uri", "flow_uri")
    else:
        field_names = ("uri",)

    for field_name in field_names:
        value = _field(declaration, field_name)
        normalized = _normalize_optional_uri(value)
        if normalized is not None:
            return normalized
    return None


def _field(declaration: Any, field_name: str) -> Any:
    if isinstance(declaration, Mapping):
        return declaration.get(field_name)
    return getattr(declaration, field_name, None)


def _normalize_owner_segment(owner: str) -> str:
    normalized = _OWNER_SEGMENT_RE.sub("-", owner.strip()).strip("-.")
    if not normalized:
        raise ValueError("owner must not be empty after normalization.")
    return normalized


def _normalize_optional_uri(raw_value: Any) -> str | None:
    if raw_value is None:
        return None
    normalized = str(raw_value).strip()
    if not normalized:
        return None
    return normalized


def _normalize_non_empty(raw_value: Any, *, field_name: str) -> str:
    normalized = str(raw_value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


def _merge_registration_metadata(
    *,
    declaration: Any,
    metadata: Mapping[str, Any] | None,
) -> dict[str, Any]:
    resolved = dict(metadata or {})
    declaration_metadata = _field(declaration, "metadata")
    declaration_metadata_mapping = (
        declaration_metadata if isinstance(declaration_metadata, Mapping) else {}
    )
    for key in ("namespace", "declaration_id", "definition_hash"):
        value = _field(declaration, key)
        if value is None and declaration_metadata_mapping:
            value = declaration_metadata_mapping.get(key)
        normalized = _normalize_optional_uri(value)
        if normalized is not None and key not in resolved:
            resolved[key] = normalized
    return resolved


def _resolve_definition_hash(raw_metadata: Mapping[str, Any] | None) -> str | None:
    if not isinstance(raw_metadata, Mapping):
        return None
    return _normalize_optional_uri(raw_metadata.get("definition_hash"))


__all__ = ["SurfaceRegistry"]
