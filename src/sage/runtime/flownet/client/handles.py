from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ResourceKind = Literal["flow", "producer", "process", "actor", "stateless", "source", "service"]


@dataclass(frozen=True)
class RegistrationHandle:
    """
    Canonical registration artifact for v1 client three-stage API.

    registration only captures declaration identity and metadata; it does not
    instantiate runtime objects.
    """

    kind: ResourceKind
    registration_id: str
    uri: str
    declaration: Any
    owner: str
    anonymous: bool
    owner_private: bool
    discoverable: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InstanceHandle:
    """
    Canonical instantiation artifact for v1 client three-stage API.

    instantiate is the stage that binds runtime options to a registration.
    """

    kind: ResourceKind
    instance_id: str
    registration: RegistrationHandle
    implicit_registration: bool
    config: dict[str, Any] = field(default_factory=dict)
    policies: dict[str, Any] = field(default_factory=dict)
    bindings: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)

    @property
    def uri(self) -> str:
        return self.registration.uri


__all__ = [
    "ResourceKind",
    "RegistrationHandle",
    "InstanceHandle",
]
