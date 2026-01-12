"""Safety & Guardrails utilities.

This module provides safety checks and content filtering:
- content_filter: Regex/pattern-based content filters
- pii_scrubber: Simple PII detection and scrubbing
- policy_check: Tool call policy validation
- interface: Abstract interfaces for advanced safety features

Concrete implementations for advanced features are provided by isage-safety.
"""

from . import content_filter, interface, pii_scrubber, policy_check

# Re-export key interfaces for convenience
from .interface import (
    # Base classes
    BaseAdversarialDefense,
    BaseGuardrail,
    BaseJailbreakDetector,
    BaseToxicityDetector,
    # Data types
    JailbreakResult,
    # Enums
    SafetyAction,
    SafetyCategory,
    SafetyResult,
    # Factories
    create_guardrail,
    create_jailbreak_detector,
    register_guardrail,
    register_jailbreak_detector,
    registered_guardrails,
    registered_jailbreak_detectors,
)

__all__ = [
    # Submodules
    "content_filter",
    "pii_scrubber",
    "policy_check",
    "interface",
    # Enums
    "SafetyCategory",
    "SafetyAction",
    # Data types
    "SafetyResult",
    "JailbreakResult",
    # Base classes
    "BaseGuardrail",
    "BaseJailbreakDetector",
    "BaseToxicityDetector",
    "BaseAdversarialDefense",
    # Factories
    "register_guardrail",
    "create_guardrail",
    "registered_guardrails",
    "register_jailbreak_detector",
    "create_jailbreak_detector",
    "registered_jailbreak_detectors",
]
