"""Safety interface layer for SAGE.

This module provides abstract interfaces for safety and guardrail components.
Concrete implementations are provided by external packages (e.g., isage-safety).

Architecture:
    - base.py: Abstract base classes (BaseGuardrail, BaseJailbreakDetector, etc.)
    - factory.py: Registry and factory functions
    - External packages register their implementations at import time

Usage:
    # Option 1: Direct instantiation (if you know the implementation)
    from isage_safety import LLMGuardrail, PatternJailbreakDetector
    guardrail = LLMGuardrail(model="gpt-4")
    detector = PatternJailbreakDetector()

    # Option 2: Factory pattern (more flexible)
    from sage.libs.safety.interface import create_guardrail, create_jailbreak_detector
    guardrail = create_guardrail("llm", model="gpt-4")
    detector = create_jailbreak_detector("pattern")

    # Check safety
    result = guardrail.check(user_input)
    if not result.is_safe:
        print(f"Blocked: {result.detected_issues}")
"""

# Base classes and data types
from .base import (
    BaseAdversarialDefense,
    BaseGuardrail,
    BaseJailbreakDetector,
    BaseToxicityDetector,
    JailbreakResult,
    SafetyAction,
    SafetyCategory,
    SafetyResult,
)

# Factory functions
from .factory import (
    SafetyRegistryError,
    # Adversarial
    create_adversarial_defense,
    # Guardrail
    create_guardrail,
    # Jailbreak
    create_jailbreak_detector,
    # Toxicity
    create_toxicity_detector,
    register_adversarial_defense,
    register_guardrail,
    register_jailbreak_detector,
    register_toxicity_detector,
    registered_adversarial_defenses,
    registered_guardrails,
    registered_jailbreak_detectors,
    registered_toxicity_detectors,
    unregister_adversarial_defense,
    unregister_guardrail,
    unregister_jailbreak_detector,
    unregister_toxicity_detector,
)

__all__ = [
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
    # Guardrail registry
    "register_guardrail",
    "create_guardrail",
    "registered_guardrails",
    "unregister_guardrail",
    # Jailbreak registry
    "register_jailbreak_detector",
    "create_jailbreak_detector",
    "registered_jailbreak_detectors",
    "unregister_jailbreak_detector",
    # Toxicity registry
    "register_toxicity_detector",
    "create_toxicity_detector",
    "registered_toxicity_detectors",
    "unregister_toxicity_detector",
    # Adversarial registry
    "register_adversarial_defense",
    "create_adversarial_defense",
    "registered_adversarial_defenses",
    "unregister_adversarial_defense",
    # Exception
    "SafetyRegistryError",
]
