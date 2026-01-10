"""Abstract base classes for intent recognition components.

This module defines the core abstractions for intent recognition and classification:
- IntentRecognizer: Recognize user intents from natural language input
- IntentClassifier: Classify intents into predefined categories
- IntentCatalog: Manage intent definitions and schemas
- IntentSlotExtractor: Extract slots/entities from user input

These interfaces enable pluggable implementations for NLU (Natural Language Understanding).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class Intent:
    """A recognized intent with confidence score."""

    name: str
    confidence: float
    slots: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate intent fields."""
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("Intent name must be a non-empty string")
        if not isinstance(self.confidence, (int, float)) or not (0 <= self.confidence <= 1):
            raise ValueError("Confidence must be a number between 0 and 1")
        if self.slots is None:
            self.slots = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class IntentDefinition:
    """Intent definition with examples and patterns."""

    name: str
    description: str
    examples: list[str]
    slots: list[str] | None = None
    patterns: list[str] | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Initialize default fields."""
        if self.slots is None:
            self.slots = []
        if self.patterns is None:
            self.patterns = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Slot:
    """An extracted slot/entity from user input."""

    name: str
    value: Any
    entity_type: str
    confidence: float = 1.0
    start_pos: int = 0
    end_pos: int = 0

    def __post_init__(self) -> None:
        """Validate slot fields."""
        if not isinstance(self.confidence, (int, float)) or not (0 <= self.confidence <= 1):
            raise ValueError("Confidence must be between 0 and 1")


# ========================================
# Intent Recognizer Interface
# ========================================


class IntentRecognizer(ABC):
    """Abstract base class for intent recognition.

    Intent recognizers identify user intents from natural language input.

    Implementations can use:
    - Keyword matching
    - Machine learning classifiers (BERT, RoBERTa)
    - LLM-based recognition
    - Rule-based patterns (regex, templates)
    - Hybrid approaches
    """

    @abstractmethod
    def recognize(self, text: str, **kwargs: Any) -> Intent:
        """Recognize intent from user input.

        Args:
            text: User input text
            **kwargs: Recognizer-specific options (threshold, context, etc.)

        Returns:
            Recognized intent with confidence score

        Raises:
            ValueError: If text is empty or invalid
        """
        pass

    @abstractmethod
    def recognize_batch(self, texts: list[str], **kwargs: Any) -> list[Intent]:
        """Recognize intents from multiple inputs.

        Args:
            texts: List of user inputs
            **kwargs: Recognizer-specific options

        Returns:
            List of recognized intents
        """
        pass

    @abstractmethod
    def get_top_k(self, text: str, k: int = 5, **kwargs: Any) -> list[Intent]:
        """Get top K intent candidates.

        Args:
            text: User input text
            k: Number of candidates to return
            **kwargs: Recognizer-specific options

        Returns:
            List of top K intents sorted by confidence descending
        """
        pass


# ========================================
# Intent Classifier Interface
# ========================================


class IntentClassifier(ABC):
    """Abstract base class for intent classification.

    Intent classifiers map user inputs to predefined intent categories.

    Implementations can use:
    - Traditional ML (SVM, Naive Bayes)
    - Deep learning (CNN, RNN, Transformer)
    - Few-shot learning
    - Zero-shot classification
    """

    @abstractmethod
    def classify(self, text: str, **kwargs: Any) -> str:
        """Classify user input into an intent category.

        Args:
            text: User input text
            **kwargs: Classifier-specific options

        Returns:
            Intent category name

        Raises:
            ValueError: If text cannot be classified
        """
        pass

    @abstractmethod
    def classify_with_confidence(self, text: str, **kwargs: Any) -> tuple[str, float]:
        """Classify with confidence score.

        Args:
            text: User input text
            **kwargs: Classifier-specific options

        Returns:
            Tuple of (intent_name, confidence_score)
        """
        pass

    @abstractmethod
    def train(self, training_data: list[tuple[str, str]], **kwargs: Any) -> None:
        """Train the classifier on labeled data.

        Args:
            training_data: List of (text, intent_label) tuples
            **kwargs: Training options (epochs, batch_size, etc.)
        """
        pass

    @abstractmethod
    def get_classes(self) -> list[str]:
        """Get list of supported intent classes.

        Returns:
            List of intent category names
        """
        pass


# ========================================
# Intent Catalog Interface
# ========================================


class IntentCatalog(ABC):
    """Abstract base class for intent catalog management.

    Intent catalogs store and manage intent definitions, examples, and schemas.

    Use cases:
    - Intent definition management
    - Training data organization
    - Intent versioning
    - Schema validation
    """

    @abstractmethod
    def add_intent(self, intent_def: IntentDefinition) -> None:
        """Add an intent definition to the catalog.

        Args:
            intent_def: Intent definition to add

        Raises:
            ValueError: If intent already exists or definition is invalid
        """
        pass

    @abstractmethod
    def get_intent(self, name: str) -> IntentDefinition:
        """Get an intent definition by name.

        Args:
            name: Intent name

        Returns:
            Intent definition

        Raises:
            KeyError: If intent not found
        """
        pass

    @abstractmethod
    def list_intents(self) -> list[str]:
        """Get list of all intent names in catalog.

        Returns:
            List of intent names
        """
        pass

    @abstractmethod
    def remove_intent(self, name: str) -> None:
        """Remove an intent from the catalog.

        Args:
            name: Intent name to remove

        Raises:
            KeyError: If intent not found
        """
        pass

    @abstractmethod
    def search_intents(self, query: str, **kwargs: Any) -> list[IntentDefinition]:
        """Search for intents matching a query.

        Args:
            query: Search query (name, description, examples)
            **kwargs: Search options (fuzzy, threshold, etc.)

        Returns:
            List of matching intent definitions
        """
        pass


# ========================================
# Intent Slot Extractor Interface
# ========================================


class IntentSlotExtractor(ABC):
    """Abstract base class for slot/entity extraction.

    Slot extractors identify and extract structured information (entities)
    from user input, such as dates, locations, names, quantities.

    Implementations can use:
    - Named Entity Recognition (NER)
    - Pattern matching (regex)
    - Dependency parsing
    - LLM-based extraction
    """

    @abstractmethod
    def extract_slots(self, text: str, intent: str | None = None, **kwargs: Any) -> list[Slot]:
        """Extract slots from user input.

        Args:
            text: User input text
            intent: Known intent (optional, for context)
            **kwargs: Extractor-specific options

        Returns:
            List of extracted slots
        """
        pass

    @abstractmethod
    def extract_slot_by_name(self, text: str, slot_name: str, **kwargs: Any) -> Slot | None:
        """Extract a specific slot by name.

        Args:
            text: User input text
            slot_name: Name of the slot to extract
            **kwargs: Extractor-specific options

        Returns:
            Extracted slot or None if not found
        """
        pass

    @abstractmethod
    def get_supported_slots(self) -> list[str]:
        """Get list of supported slot types.

        Returns:
            List of slot/entity type names
        """
        pass


__all__ = [
    # Data classes
    "Intent",
    "IntentDefinition",
    "Slot",
    # Base classes
    "IntentRecognizer",
    "IntentClassifier",
    "IntentCatalog",
    "IntentSlotExtractor",
]
