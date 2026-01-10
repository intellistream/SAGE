"""Factory and registry for safety implementations.

This module provides a registry pattern for safety components.
External packages (like isage-safety) can register their implementations here.

Example:
    # Register implementations
    from sage.libs.safety.interface import (
        register_guardrail,
        register_jailbreak_detector,
        register_toxicity_detector,
    )
    register_guardrail("llm", LLMGuardrail)
    register_jailbreak_detector("pattern", PatternJailbreakDetector)
    register_toxicity_detector("perspective", PerspectiveDetector)

    # Create instances
    from sage.libs.safety.interface import (
        create_guardrail,
        create_jailbreak_detector,
        create_toxicity_detector,
    )
    guardrail = create_guardrail("llm", model="gpt-4")
    detector = create_jailbreak_detector("pattern")
    toxicity = create_toxicity_detector("perspective")
"""

from typing import Any

from .base import (
    BaseAdversarialDefense,
    BaseGuardrail,
    BaseJailbreakDetector,
    BaseToxicityDetector,
)

_GUARDRAIL_REGISTRY: dict[str, type[BaseGuardrail]] = {}
_JAILBREAK_REGISTRY: dict[str, type[BaseJailbreakDetector]] = {}
_TOXICITY_REGISTRY: dict[str, type[BaseToxicityDetector]] = {}
_ADVERSARIAL_REGISTRY: dict[str, type[BaseAdversarialDefense]] = {}


class SafetyRegistryError(Exception):
    """Error raised when registry operations fail."""

    pass


# ========================================
# Guardrail Registry
# ========================================


def register_guardrail(name: str, cls: type[BaseGuardrail]) -> None:
    """Register a guardrail implementation.

    Args:
        name: Unique identifier (e.g., "llm", "classifier", "rule_based")
        cls: Guardrail class (should inherit from BaseGuardrail)

    Raises:
        SafetyRegistryError: If name already registered
    """
    if name in _GUARDRAIL_REGISTRY:
        raise SafetyRegistryError(f"Guardrail '{name}' already registered")

    if not issubclass(cls, BaseGuardrail):
        raise TypeError(f"Class must inherit from BaseGuardrail, got {cls}")

    _GUARDRAIL_REGISTRY[name] = cls


def create_guardrail(name: str, **kwargs: Any) -> BaseGuardrail:
    """Create a guardrail instance by name.

    Args:
        name: Name of the registered guardrail
        **kwargs: Arguments to pass to the guardrail constructor

    Returns:
        Instance of the guardrail

    Raises:
        SafetyRegistryError: If guardrail not found
    """
    if name not in _GUARDRAIL_REGISTRY:
        available = ", ".join(_GUARDRAIL_REGISTRY.keys()) if _GUARDRAIL_REGISTRY else "none"
        raise SafetyRegistryError(
            f"Guardrail '{name}' not found. Available: {available}. Did you install 'isage-safety'?"
        )

    cls = _GUARDRAIL_REGISTRY[name]
    return cls(**kwargs)


def registered_guardrails() -> list[str]:
    """Get list of registered guardrail names."""
    return list(_GUARDRAIL_REGISTRY.keys())


def unregister_guardrail(name: str) -> None:
    """Unregister a guardrail (for testing)."""
    _GUARDRAIL_REGISTRY.pop(name, None)


# ========================================
# Jailbreak Detector Registry
# ========================================


def register_jailbreak_detector(name: str, cls: type[BaseJailbreakDetector]) -> None:
    """Register a jailbreak detector implementation.

    Args:
        name: Unique identifier (e.g., "pattern", "ml", "llm", "ensemble")
        cls: Detector class (should inherit from BaseJailbreakDetector)

    Raises:
        SafetyRegistryError: If name already registered
    """
    if name in _JAILBREAK_REGISTRY:
        raise SafetyRegistryError(f"Jailbreak detector '{name}' already registered")

    if not issubclass(cls, BaseJailbreakDetector):
        raise TypeError(f"Class must inherit from BaseJailbreakDetector, got {cls}")

    _JAILBREAK_REGISTRY[name] = cls


def create_jailbreak_detector(name: str, **kwargs: Any) -> BaseJailbreakDetector:
    """Create a jailbreak detector instance by name.

    Args:
        name: Name of the registered detector
        **kwargs: Arguments to pass to the detector constructor

    Returns:
        Instance of the detector

    Raises:
        SafetyRegistryError: If detector not found
    """
    if name not in _JAILBREAK_REGISTRY:
        available = ", ".join(_JAILBREAK_REGISTRY.keys()) if _JAILBREAK_REGISTRY else "none"
        raise SafetyRegistryError(
            f"Jailbreak detector '{name}' not found. Available: {available}. Did you install 'isage-safety'?"
        )

    cls = _JAILBREAK_REGISTRY[name]
    return cls(**kwargs)


def registered_jailbreak_detectors() -> list[str]:
    """Get list of registered jailbreak detector names."""
    return list(_JAILBREAK_REGISTRY.keys())


def unregister_jailbreak_detector(name: str) -> None:
    """Unregister a jailbreak detector (for testing)."""
    _JAILBREAK_REGISTRY.pop(name, None)


# ========================================
# Toxicity Detector Registry
# ========================================


def register_toxicity_detector(name: str, cls: type[BaseToxicityDetector]) -> None:
    """Register a toxicity detector implementation.

    Args:
        name: Unique identifier (e.g., "perspective", "transformer", "multilingual")
        cls: Detector class (should inherit from BaseToxicityDetector)

    Raises:
        SafetyRegistryError: If name already registered
    """
    if name in _TOXICITY_REGISTRY:
        raise SafetyRegistryError(f"Toxicity detector '{name}' already registered")

    if not issubclass(cls, BaseToxicityDetector):
        raise TypeError(f"Class must inherit from BaseToxicityDetector, got {cls}")

    _TOXICITY_REGISTRY[name] = cls


def create_toxicity_detector(name: str, **kwargs: Any) -> BaseToxicityDetector:
    """Create a toxicity detector instance by name.

    Args:
        name: Name of the registered detector
        **kwargs: Arguments to pass to the detector constructor

    Returns:
        Instance of the detector

    Raises:
        SafetyRegistryError: If detector not found
    """
    if name not in _TOXICITY_REGISTRY:
        available = ", ".join(_TOXICITY_REGISTRY.keys()) if _TOXICITY_REGISTRY else "none"
        raise SafetyRegistryError(
            f"Toxicity detector '{name}' not found. Available: {available}. Did you install 'isage-safety'?"
        )

    cls = _TOXICITY_REGISTRY[name]
    return cls(**kwargs)


def registered_toxicity_detectors() -> list[str]:
    """Get list of registered toxicity detector names."""
    return list(_TOXICITY_REGISTRY.keys())


def unregister_toxicity_detector(name: str) -> None:
    """Unregister a toxicity detector (for testing)."""
    _TOXICITY_REGISTRY.pop(name, None)


# ========================================
# Adversarial Defense Registry
# ========================================


def register_adversarial_defense(name: str, cls: type[BaseAdversarialDefense]) -> None:
    """Register an adversarial defense implementation.

    Args:
        name: Unique identifier (e.g., "sanitizer", "detector", "robust")
        cls: Defense class (should inherit from BaseAdversarialDefense)

    Raises:
        SafetyRegistryError: If name already registered
    """
    if name in _ADVERSARIAL_REGISTRY:
        raise SafetyRegistryError(f"Adversarial defense '{name}' already registered")

    if not issubclass(cls, BaseAdversarialDefense):
        raise TypeError(f"Class must inherit from BaseAdversarialDefense, got {cls}")

    _ADVERSARIAL_REGISTRY[name] = cls


def create_adversarial_defense(name: str, **kwargs: Any) -> BaseAdversarialDefense:
    """Create an adversarial defense instance by name.

    Args:
        name: Name of the registered defense
        **kwargs: Arguments to pass to the defense constructor

    Returns:
        Instance of the defense

    Raises:
        SafetyRegistryError: If defense not found
    """
    if name not in _ADVERSARIAL_REGISTRY:
        available = ", ".join(_ADVERSARIAL_REGISTRY.keys()) if _ADVERSARIAL_REGISTRY else "none"
        raise SafetyRegistryError(
            f"Adversarial defense '{name}' not found. Available: {available}. Did you install 'isage-safety'?"
        )

    cls = _ADVERSARIAL_REGISTRY[name]
    return cls(**kwargs)


def registered_adversarial_defenses() -> list[str]:
    """Get list of registered adversarial defense names."""
    return list(_ADVERSARIAL_REGISTRY.keys())


def unregister_adversarial_defense(name: str) -> None:
    """Unregister an adversarial defense (for testing)."""
    _ADVERSARIAL_REGISTRY.pop(name, None)


__all__ = [
    "SafetyRegistryError",
    # Guardrail
    "register_guardrail",
    "create_guardrail",
    "registered_guardrails",
    "unregister_guardrail",
    # Jailbreak
    "register_jailbreak_detector",
    "create_jailbreak_detector",
    "registered_jailbreak_detectors",
    "unregister_jailbreak_detector",
    # Toxicity
    "register_toxicity_detector",
    "create_toxicity_detector",
    "registered_toxicity_detectors",
    "unregister_toxicity_detector",
    # Adversarial
    "register_adversarial_defense",
    "create_adversarial_defense",
    "registered_adversarial_defenses",
    "unregister_adversarial_defense",
]
