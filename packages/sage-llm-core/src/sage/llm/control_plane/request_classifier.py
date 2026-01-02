# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Request classifier for hybrid scheduling.

This module provides the RequestClassifier class, which is responsible for:
1. Automatically classifying requests based on their content
2. Filtering execution instances by compatibility with request types
3. Validating request completeness and correctness

The classifier is a key component in the hybrid scheduling pipeline,
enabling the Control Plane to route LLM and Embedding requests to
appropriate execution instances.

Example:
    >>> from control_plane.request_classifier import RequestClassifier
    >>> from control_plane.types import RequestMetadata, ExecutionInstance, RequestType
    >>>
    >>> classifier = RequestClassifier()
    >>>
    >>> # Classify a request
    >>> request = RequestMetadata(
    ...     request_id="req-1",
    ...     embedding_texts=["Hello", "World"],
    ... )
    >>> request_type = classifier.classify(request)
    >>> print(request_type)  # RequestType.EMBEDDING
    >>>
    >>> # Get compatible instances
    >>> instances = [...]  # list of ExecutionInstance
    >>> compatible = classifier.get_compatible_instances(
    ...     RequestType.EMBEDDING,
    ...     instances,
    ... )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from .types import (
    ExecutionInstance,
    ExecutionInstanceType,
    RequestMetadata,
    RequestType,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ValidationErrorCode(Enum):
    """Error codes for request validation failures.

    These codes help identify specific validation issues and enable
    appropriate error handling and user feedback.

    Attributes:
        MISSING_REQUEST_ID: Request ID is missing or empty.
        MISSING_PROMPT: LLM request is missing prompt text.
        MISSING_EMBEDDING_TEXTS: Embedding request has no texts to embed.
        EMPTY_EMBEDDING_TEXTS: Embedding texts list is empty.
        INVALID_EMBEDDING_BATCH_SIZE: Batch size is not positive.
        INVALID_MAX_TOKENS: Max tokens is not positive.
        INVALID_TEMPERATURE: Temperature is out of valid range.
        INVALID_TOP_P: Top-p is out of valid range.
        CONFLICTING_REQUEST_TYPE: Request has conflicting type indicators.
    """

    MISSING_REQUEST_ID = "missing_request_id"
    MISSING_PROMPT = "missing_prompt"
    MISSING_EMBEDDING_TEXTS = "missing_embedding_texts"
    EMPTY_EMBEDDING_TEXTS = "empty_embedding_texts"
    INVALID_EMBEDDING_BATCH_SIZE = "invalid_embedding_batch_size"
    INVALID_MAX_TOKENS = "invalid_max_tokens"
    INVALID_TEMPERATURE = "invalid_temperature"
    INVALID_TOP_P = "invalid_top_p"
    CONFLICTING_REQUEST_TYPE = "conflicting_request_type"


@dataclass
class ValidationResult:
    """Result of request validation.

    Attributes:
        is_valid: Whether the request passed validation.
        error_code: Error code if validation failed, None otherwise.
        error_message: Human-readable error message if validation failed.
        warnings: List of non-fatal warning messages.
    """

    is_valid: bool
    error_code: ValidationErrorCode | None = None
    error_message: str = ""
    warnings: list[str] | None = None

    def __post_init__(self) -> None:
        """Initialize warnings list if not provided."""
        if self.warnings is None:
            self.warnings = []


class RequestClassifier:
    """Classifier for inference requests in hybrid scheduling.

    This class provides methods to:
    1. Classify requests by type (LLM_CHAT, LLM_GENERATE, EMBEDDING)
    2. Filter execution instances by compatibility with request types
    3. Validate requests for completeness and correctness

    The classifier uses a priority-based classification strategy:
    1. If request.request_type is explicitly set and not default, use it
    2. If request.embedding_texts is non-empty, classify as EMBEDDING
    3. If request.prompt is non-empty, classify as LLM_CHAT or LLM_GENERATE
    4. Default to LLM_CHAT for backward compatibility

    Attributes:
        strict_validation: If True, validation is stricter (e.g., reject
            requests with both prompt and embedding_texts).

    Example:
        >>> classifier = RequestClassifier()
        >>>
        >>> # Auto-classification based on content
        >>> request = RequestMetadata(
        ...     request_id="req-1",
        ...     embedding_texts=["Hello", "World"],
        ... )
        >>> classifier.classify(request)
        RequestType.EMBEDDING
        >>>
        >>> # Explicit type takes precedence
        >>> request = RequestMetadata(
        ...     request_id="req-2",
        ...     prompt="Hello",
        ...     request_type=RequestType.LLM_GENERATE,
        ... )
        >>> classifier.classify(request)
        RequestType.LLM_GENERATE
    """

    def __init__(self, strict_validation: bool = False) -> None:
        """Initialize the request classifier.

        Args:
            strict_validation: If True, validation will be stricter.
                For example, requests with both prompt and embedding_texts
                will be rejected. Default is False for backward compatibility.
        """
        self.strict_validation = strict_validation

    def classify(self, request: RequestMetadata) -> RequestType:
        """Classify a request based on its content.

        This method determines the request type using the following priority:
        1. If request.request_type is explicitly set (not default LLM_CHAT
           when no prompt is provided), use it
        2. If request.embedding_texts is non-empty, classify as EMBEDDING
        3. If request.prompt is non-empty, use request.request_type
           (defaults to LLM_CHAT)
        4. Default to LLM_CHAT for backward compatibility

        Args:
            request: The request metadata to classify.

        Returns:
            The determined RequestType for this request.

        Examples:
            >>> classifier = RequestClassifier()
            >>>
            >>> # Embedding request (auto-detected)
            >>> req = RequestMetadata(
            ...     request_id="r1",
            ...     embedding_texts=["text1", "text2"],
            ... )
            >>> classifier.classify(req)
            RequestType.EMBEDDING
            >>>
            >>> # LLM chat request (default)
            >>> req = RequestMetadata(request_id="r2", prompt="Hello")
            >>> classifier.classify(req)
            RequestType.LLM_CHAT
            >>>
            >>> # Explicit type
            >>> req = RequestMetadata(
            ...     request_id="r3",
            ...     prompt="Generate:",
            ...     request_type=RequestType.LLM_GENERATE,
            ... )
            >>> classifier.classify(req)
            RequestType.LLM_GENERATE
        """
        # Priority 1: Check if request_type is explicitly set to EMBEDDING
        if request.request_type == RequestType.EMBEDDING:
            logger.debug(
                "Request %s classified as EMBEDDING (explicit type)",
                request.request_id,
            )
            return RequestType.EMBEDDING

        # Priority 2: Auto-detect EMBEDDING from embedding_texts
        if request.embedding_texts is not None and len(request.embedding_texts) > 0:
            logger.debug(
                "Request %s classified as EMBEDDING (has embedding_texts)",
                request.request_id,
            )
            return RequestType.EMBEDDING

        # Priority 3: Check if request_type is explicitly set to LLM_GENERATE
        if request.request_type == RequestType.LLM_GENERATE:
            logger.debug(
                "Request %s classified as LLM_GENERATE (explicit type)",
                request.request_id,
            )
            return RequestType.LLM_GENERATE

        # Priority 4: Default to LLM_CHAT
        # This handles cases where:
        # - request.prompt is set with default request_type
        # - request has neither prompt nor embedding_texts (edge case)
        logger.debug(
            "Request %s classified as LLM_CHAT (default)",
            request.request_id,
        )
        return RequestType.LLM_CHAT

    def get_compatible_instances(
        self,
        request_type: RequestType,
        instances: list[ExecutionInstance],
        *,
        include_unavailable: bool = False,
        prefer_specialized: bool = True,
    ) -> list[ExecutionInstance]:
        """Get execution instances compatible with a request type.

        Filters the provided list of instances to return only those that
        can handle the specified request type. By default, also filters
        out unavailable/unhealthy instances.

        Instance compatibility is determined by:
        1. The instance's supported_request_types (explicit or computed)
        2. The instance's availability and health status (unless disabled)

        For EMBEDDING requests:
        - EMBEDDING instances are preferred (specialized)
        - LLM_EMBEDDING instances are also compatible

        For LLM_CHAT/LLM_GENERATE requests:
        - GENERAL, PREFILLING, DECODING, HYBRID instances are preferred
        - LLM_EMBEDDING instances are also compatible
        - EMBEDDING instances are NOT compatible

        Args:
            request_type: The type of request to find compatible instances for.
            instances: List of execution instances to filter.
            include_unavailable: If True, include unavailable/unhealthy
                instances in the result. Default is False.
            prefer_specialized: If True, sort results to prefer specialized
                instances. For EMBEDDING, pure EMBEDDING instances come first.
                For LLM, LLM-only instances come before LLM_EMBEDDING.
                Default is True.

        Returns:
            List of compatible ExecutionInstance objects, optionally sorted
            by preference.

        Examples:
            >>> classifier = RequestClassifier()
            >>> instances = [
            ...     ExecutionInstance(
            ...         instance_id="llm-1", host="localhost", port=8000,
            ...         model_name="qwen", instance_type=ExecutionInstanceType.GENERAL,
            ...     ),
            ...     ExecutionInstance(
            ...         instance_id="embed-1", host="localhost", port=8090,
            ...         model_name="bge", instance_type=ExecutionInstanceType.EMBEDDING,
            ...     ),
            ...     ExecutionInstance(
            ...         instance_id="mixed-1", host="localhost", port=8001,
            ...         model_name="qwen", instance_type=ExecutionInstanceType.LLM_EMBEDDING,
            ...     ),
            ... ]
            >>>
            >>> # Get instances for EMBEDDING
            >>> compatible = classifier.get_compatible_instances(
            ...     RequestType.EMBEDDING, instances
            ... )
            >>> [i.instance_id for i in compatible]
            ['embed-1', 'mixed-1']
            >>>
            >>> # Get instances for LLM_CHAT
            >>> compatible = classifier.get_compatible_instances(
            ...     RequestType.LLM_CHAT, instances
            ... )
            >>> [i.instance_id for i in compatible]
            ['llm-1', 'mixed-1']
        """
        compatible: list[ExecutionInstance] = []

        for instance in instances:
            # Check type compatibility
            if not instance.can_handle_request_type(request_type):
                continue

            # Check availability (unless disabled)
            if not include_unavailable:
                if not instance.is_available or not instance.is_healthy:
                    continue

            compatible.append(instance)

        # Sort by preference if requested
        if prefer_specialized and compatible:
            compatible = self._sort_by_preference(request_type, compatible)

        logger.debug(
            "Found %d compatible instances for %s out of %d total",
            len(compatible),
            request_type.value,
            len(instances),
        )

        return compatible

    def _sort_by_preference(
        self,
        request_type: RequestType,
        instances: list[ExecutionInstance],
    ) -> list[ExecutionInstance]:
        """Sort instances by preference for a request type.

        For EMBEDDING requests:
        - Pure EMBEDDING instances first (most specialized)
        - LLM_EMBEDDING instances second (can do both but less efficient)

        For LLM requests:
        - Specialized LLM instances first (GENERAL, PREFILLING, DECODING, HYBRID)
        - LLM_EMBEDDING instances second (can do both but may be busy with embeddings)

        Within each category, instances are sorted by available capacity
        (descending) to prefer less loaded instances.

        Args:
            request_type: The request type for preference scoring.
            instances: List of instances to sort.

        Returns:
            Sorted list of instances by preference.
        """

        def preference_key(instance: ExecutionInstance) -> tuple[int, float]:
            """Generate a sort key (lower = more preferred).

            Returns:
                Tuple of (type_preference, -available_capacity).
                Type preference: 0 = most preferred, higher = less preferred.
                Negative capacity so higher capacity sorts first.
            """
            instance_type = instance.instance_type

            if request_type == RequestType.EMBEDDING:
                # For EMBEDDING: prefer pure embedding instances
                if instance_type == ExecutionInstanceType.EMBEDDING:
                    type_pref = 0  # Most preferred
                elif instance_type == ExecutionInstanceType.LLM_EMBEDDING:
                    type_pref = 1  # Second choice
                else:
                    type_pref = 99  # Shouldn't happen (filtered out)
            else:
                # For LLM requests: prefer dedicated LLM instances
                if instance_type in (
                    ExecutionInstanceType.GENERAL,
                    ExecutionInstanceType.HYBRID,
                ):
                    type_pref = 0  # Most preferred for general LLM
                elif instance_type == ExecutionInstanceType.PREFILLING:
                    type_pref = 1  # Good for long prompts
                elif instance_type == ExecutionInstanceType.DECODING:
                    type_pref = 1  # Good for generation
                elif instance_type == ExecutionInstanceType.LLM_EMBEDDING:
                    type_pref = 2  # Can do LLM but might be busy with embeddings
                else:
                    type_pref = 99  # Shouldn't happen

            # Secondary sort by available capacity (descending)
            return (type_pref, -instance.available_capacity)

        return sorted(instances, key=preference_key)

    def validate_request(
        self,
        request: RequestMetadata,
    ) -> ValidationResult:
        """Validate a request for completeness and correctness.

        Performs validation checks on the request to ensure it has all
        required fields and that field values are within valid ranges.

        Validation checks:
        1. Request ID is present and non-empty
        2. For EMBEDDING requests: embedding_texts is present and non-empty
        3. For LLM requests: prompt is present (warning if missing)
        4. Numeric parameters are in valid ranges (max_tokens, temperature, top_p)
        5. In strict mode: no conflicting type indicators

        Args:
            request: The request metadata to validate.

        Returns:
            ValidationResult with is_valid=True if validation passes,
            or is_valid=False with error details if validation fails.

        Examples:
            >>> classifier = RequestClassifier()
            >>>
            >>> # Valid embedding request
            >>> req = RequestMetadata(
            ...     request_id="r1",
            ...     request_type=RequestType.EMBEDDING,
            ...     embedding_texts=["Hello", "World"],
            ... )
            >>> result = classifier.validate_request(req)
            >>> result.is_valid
            True
            >>>
            >>> # Invalid: missing request_id
            >>> req = RequestMetadata(request_id="", prompt="Hello")
            >>> result = classifier.validate_request(req)
            >>> result.is_valid
            False
            >>> result.error_code
            ValidationErrorCode.MISSING_REQUEST_ID
        """
        warnings: list[str] = []

        # Check request_id
        if not request.request_id or not request.request_id.strip():
            return ValidationResult(
                is_valid=False,
                error_code=ValidationErrorCode.MISSING_REQUEST_ID,
                error_message="Request ID is required and cannot be empty",
            )

        # Classify the request for type-specific validation
        request_type = self.classify(request)

        # Validate based on request type
        if request_type == RequestType.EMBEDDING:
            # Embedding-specific validation
            if request.embedding_texts is None:
                return ValidationResult(
                    is_valid=False,
                    error_code=ValidationErrorCode.MISSING_EMBEDDING_TEXTS,
                    error_message="Embedding request requires embedding_texts",
                )
            if len(request.embedding_texts) == 0:
                return ValidationResult(
                    is_valid=False,
                    error_code=ValidationErrorCode.EMPTY_EMBEDDING_TEXTS,
                    error_message="Embedding request requires at least one text",
                )
            if request.embedding_batch_size <= 0:
                return ValidationResult(
                    is_valid=False,
                    error_code=ValidationErrorCode.INVALID_EMBEDDING_BATCH_SIZE,
                    error_message="embedding_batch_size must be positive",
                )
        else:
            # LLM-specific validation
            if not request.prompt:
                warnings.append("LLM request has no prompt; this may result in empty generation")

            # Validate max_tokens if set
            if request.max_tokens is not None and request.max_tokens <= 0:
                return ValidationResult(
                    is_valid=False,
                    error_code=ValidationErrorCode.INVALID_MAX_TOKENS,
                    error_message="max_tokens must be positive",
                )

            # Validate temperature
            if request.temperature < 0.0:
                return ValidationResult(
                    is_valid=False,
                    error_code=ValidationErrorCode.INVALID_TEMPERATURE,
                    error_message="temperature must be non-negative",
                )

            # Validate top_p
            if request.top_p < 0.0 or request.top_p > 1.0:
                return ValidationResult(
                    is_valid=False,
                    error_code=ValidationErrorCode.INVALID_TOP_P,
                    error_message="top_p must be between 0.0 and 1.0",
                )

        # Strict mode: check for conflicting indicators
        if self.strict_validation:
            has_prompt = request.prompt is not None and len(request.prompt) > 0
            has_embedding_texts = (
                request.embedding_texts is not None and len(request.embedding_texts) > 0
            )
            if has_prompt and has_embedding_texts:
                return ValidationResult(
                    is_valid=False,
                    error_code=ValidationErrorCode.CONFLICTING_REQUEST_TYPE,
                    error_message=(
                        "Request has both prompt and embedding_texts; please use only one"
                    ),
                )

        return ValidationResult(is_valid=True, warnings=warnings)

    def get_request_summary(self, request: RequestMetadata) -> dict[str, Any]:
        """Get a summary of request classification and validation.

        Provides a comprehensive summary useful for debugging and logging.

        Args:
            request: The request to summarize.

        Returns:
            Dictionary with classification and validation details.
        """
        request_type = self.classify(request)
        validation = self.validate_request(request)

        return {
            "request_id": request.request_id,
            "classified_type": request_type.value,
            "explicit_type": request.request_type.value,
            "has_prompt": request.prompt is not None and len(request.prompt or "") > 0,
            "has_embedding_texts": (
                request.embedding_texts is not None and len(request.embedding_texts) > 0
            ),
            "embedding_text_count": (
                len(request.embedding_texts) if request.embedding_texts else 0
            ),
            "is_valid": validation.is_valid,
            "validation_error": (validation.error_message if not validation.is_valid else None),
            "validation_warnings": validation.warnings,
            "effective_model": request.effective_model_name,
            "priority": request.priority.value,
        }


def create_classifier(strict_validation: bool = False) -> RequestClassifier:
    """Factory function to create a RequestClassifier.

    This is a convenience function for creating RequestClassifier instances.

    Args:
        strict_validation: Whether to use strict validation mode.

    Returns:
        A new RequestClassifier instance.

    Example:
        >>> classifier = create_classifier(strict_validation=True)
    """
    return RequestClassifier(strict_validation=strict_validation)
