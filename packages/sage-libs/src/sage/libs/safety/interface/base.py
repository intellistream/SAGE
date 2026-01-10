"""Base classes and interfaces for safety.

This module defines abstract interfaces for safety and guardrails:
- BaseGuardrail: Content safety guardrail base class
- BaseJailbreakDetector: Jailbreak/prompt injection detection
- BaseAdversarialDefense: Adversarial input defense
- BaseToxicityDetector: Toxicity and harmful content detection

Implementations are provided by the external 'isage-safety' package.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class SafetyCategory(Enum):
    """Categories of safety concerns."""

    # Content safety
    TOXICITY = "toxicity"
    HATE_SPEECH = "hate_speech"
    VIOLENCE = "violence"
    SEXUAL = "sexual"
    SELF_HARM = "self_harm"

    # Security
    JAILBREAK = "jailbreak"
    PROMPT_INJECTION = "prompt_injection"
    DATA_LEAKAGE = "data_leakage"

    # Privacy
    PII_EXPOSURE = "pii_exposure"
    SENSITIVE_INFO = "sensitive_info"

    # Misinformation
    FACTUAL_ERROR = "factual_error"
    HALLUCINATION = "hallucination"

    # Other
    POLICY_VIOLATION = "policy_violation"
    CUSTOM = "custom"


class SafetyAction(Enum):
    """Actions to take when safety issues are detected."""

    ALLOW = "allow"  # Allow the content
    WARN = "warn"  # Allow with warning
    MODIFY = "modify"  # Modify/filter the content
    BLOCK = "block"  # Block the content
    ESCALATE = "escalate"  # Escalate to human review


@dataclass
class SafetyResult:
    """Result of a safety check."""

    is_safe: bool
    action: SafetyAction = SafetyAction.ALLOW

    # Detection details
    category: Optional[SafetyCategory] = None
    confidence: float = 0.0
    detected_issues: list[str] = field(default_factory=list)

    # Modified content (if action is MODIFY)
    modified_content: Optional[str] = None

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"SafetyResult(safe={self.is_safe}, action={self.action.value}, confidence={self.confidence:.2f})"


@dataclass
class JailbreakResult:
    """Result of a jailbreak detection check."""

    is_jailbreak: bool
    confidence: float = 0.0

    # Attack type
    attack_type: Optional[str] = None  # "prompt_injection", "role_play", "encoding", etc.
    attack_signature: Optional[str] = None

    # Explanation
    explanation: Optional[str] = None

    metadata: dict[str, Any] = field(default_factory=dict)


class BaseGuardrail(ABC):
    """Abstract base class for content safety guardrails.

    Examples of implementations:
    - LLMGuardrail: LLM-based content moderation
    - ClassifierGuardrail: ML classifier-based moderation
    - RuleBasedGuardrail: Pattern/rule-based filtering
    - HybridGuardrail: Combined approach
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the guardrail name."""
        pass

    @property
    def categories(self) -> list[SafetyCategory]:
        """Return the safety categories this guardrail handles."""
        return [SafetyCategory.CUSTOM]

    @abstractmethod
    def check(
        self,
        content: str,
        context: Optional[str] = None,
        **kwargs: Any,
    ) -> SafetyResult:
        """Check content for safety issues.

        Args:
            content: Content to check (user input or model output)
            context: Optional conversation context
            **kwargs: Guardrail-specific parameters

        Returns:
            SafetyResult with detection status and recommended action
        """
        pass

    def check_batch(
        self,
        contents: list[str],
        contexts: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> list[SafetyResult]:
        """Check multiple contents for safety issues.

        Default implementation calls check() for each content.
        Override for batch-optimized processing.

        Args:
            contents: List of contents to check
            contexts: Optional list of contexts
            **kwargs: Guardrail-specific parameters

        Returns:
            List of SafetyResults
        """
        contexts = contexts or [None] * len(contents)
        return [
            self.check(content, context, **kwargs) for content, context in zip(contents, contexts)
        ]

    def filter(
        self,
        content: str,
        **kwargs: Any,
    ) -> tuple[str, SafetyResult]:
        """Check and potentially modify content.

        Args:
            content: Content to check and filter
            **kwargs: Guardrail-specific parameters

        Returns:
            Tuple of (filtered_content, SafetyResult)
        """
        result = self.check(content, **kwargs)
        if result.action == SafetyAction.MODIFY and result.modified_content:
            return result.modified_content, result
        return content, result


class BaseJailbreakDetector(ABC):
    """Abstract base class for jailbreak and prompt injection detection.

    Examples of implementations:
    - PatternJailbreakDetector: Pattern/regex-based detection
    - MLJailbreakDetector: ML model-based detection
    - LLMJailbreakDetector: LLM-based detection
    - EnsembleJailbreakDetector: Combined approach
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the detector name."""
        pass

    @abstractmethod
    def detect(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> JailbreakResult:
        """Detect jailbreak attempts in a prompt.

        Args:
            prompt: User prompt to analyze
            system_prompt: System prompt (to detect prompt injection)
            **kwargs: Detector-specific parameters

        Returns:
            JailbreakResult with detection status and confidence
        """
        pass

    def detect_batch(
        self,
        prompts: list[str],
        system_prompts: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> list[JailbreakResult]:
        """Detect jailbreaks in multiple prompts.

        Default implementation calls detect() for each prompt.
        Override for batch-optimized processing.

        Args:
            prompts: List of prompts to analyze
            system_prompts: Optional list of system prompts
            **kwargs: Detector-specific parameters

        Returns:
            List of JailbreakResults
        """
        system_prompts = system_prompts or [None] * len(prompts)
        return [
            self.detect(prompt, system_prompt, **kwargs)
            for prompt, system_prompt in zip(prompts, system_prompts)
        ]

    def is_jailbreak(self, prompt: str, threshold: float = 0.5, **kwargs: Any) -> bool:
        """Quick check if prompt is a jailbreak attempt.

        Args:
            prompt: Prompt to check
            threshold: Confidence threshold
            **kwargs: Detector parameters

        Returns:
            True if jailbreak detected with confidence >= threshold
        """
        result = self.detect(prompt, **kwargs)
        return result.is_jailbreak and result.confidence >= threshold


class BaseToxicityDetector(ABC):
    """Abstract base class for toxicity detection.

    Examples of implementations:
    - PerspectiveDetector: Google Perspective API
    - TransformerDetector: Transformer-based toxicity model
    - MultilingualDetector: Multilingual toxicity detection
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the detector name."""
        pass

    @abstractmethod
    def detect(
        self,
        text: str,
        **kwargs: Any,
    ) -> SafetyResult:
        """Detect toxicity in text.

        Args:
            text: Text to analyze
            **kwargs: Detector-specific parameters

        Returns:
            SafetyResult with toxicity detection
        """
        pass

    def get_scores(
        self,
        text: str,
        **kwargs: Any,
    ) -> dict[str, float]:
        """Get detailed toxicity scores.

        Args:
            text: Text to analyze
            **kwargs: Detector parameters

        Returns:
            Dictionary mapping categories to scores
        """
        result = self.detect(text, **kwargs)
        return result.metadata.get("scores", {})


class BaseAdversarialDefense(ABC):
    """Abstract base class for adversarial input defense.

    Examples of implementations:
    - InputSanitizer: Clean adversarial perturbations
    - AdversarialDetector: Detect adversarial inputs
    - RobustClassifier: Adversarially trained classifier
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the defense name."""
        pass

    @abstractmethod
    def defend(
        self,
        input_data: Any,
        **kwargs: Any,
    ) -> tuple[Any, bool]:
        """Apply defense to input.

        Args:
            input_data: Input to defend (text, embedding, etc.)
            **kwargs: Defense-specific parameters

        Returns:
            Tuple of (defended_input, was_adversarial)
        """
        pass

    def is_adversarial(
        self,
        input_data: Any,
        **kwargs: Any,
    ) -> tuple[bool, float]:
        """Check if input is adversarial.

        Args:
            input_data: Input to check
            **kwargs: Defense parameters

        Returns:
            Tuple of (is_adversarial, confidence)
        """
        _, was_adversarial = self.defend(input_data, **kwargs)
        return was_adversarial, 1.0 if was_adversarial else 0.0


__all__ = [
    # Enums
    "SafetyCategory",
    "SafetyAction",
    # Data classes
    "SafetyResult",
    "JailbreakResult",
    # Base classes
    "BaseGuardrail",
    "BaseJailbreakDetector",
    "BaseToxicityDetector",
    "BaseAdversarialDefense",
]
