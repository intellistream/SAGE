"""
SIAS Core Data Types

Defines the core data structures used across SIAS components.
These are designed to be independent of specific data sources.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(slots=True)
class SIASSample:
    """
    Generic sample container for SIAS algorithms.

    This is a lightweight data class that can wrap samples from various sources.
    The only required fields are sample_id and text; everything else is optional.

    Attributes:
        sample_id: Unique identifier for this sample
        text: The text content (or serialized representation)
        metadata: Arbitrary metadata dictionary
        importance_score: SSIS-computed importance score (set during training)
    """

    sample_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    importance_score: float = 0.0

    def __hash__(self) -> int:
        return hash(self.sample_id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SIASSample):
            return self.sample_id == other.sample_id
        return False


@runtime_checkable
class SampleProtocol(Protocol):
    """
    Protocol for samples that can be used with SIAS algorithms.

    Any class with these attributes can be used with CoresetSelector
    and OnlineContinualLearner without modification.
    """

    @property
    def sample_id(self) -> str:
        """Unique identifier for the sample."""
        ...

    @property
    def text(self) -> str:
        """Text content of the sample."""
        ...

    @property
    def metadata(self) -> dict[str, Any]:
        """Metadata dictionary."""
        ...


# Backward compatibility alias
# This allows existing code using ProcessedDialog to work with SIAS
# by implementing the SampleProtocol
Sample = SIASSample


def wrap_sample(
    sample_id: str,
    text: str,
    metadata: dict[str, Any] | None = None,
    **kwargs: Any,
) -> SIASSample:
    """
    Factory function to create a SIASSample.

    Args:
        sample_id: Unique identifier
        text: Text content
        metadata: Optional metadata dict
        **kwargs: Additional metadata fields

    Returns:
        A new SIASSample instance
    """
    meta = metadata or {}
    meta.update(kwargs)
    return SIASSample(sample_id=sample_id, text=text, metadata=meta)
