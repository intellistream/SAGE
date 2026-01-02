"""Core AMM abstractions for approximate matrix multiplication.

These interfaces provide a unified API for various AMM algorithms,
similar to how AnnIndex provides interfaces for ANN algorithms.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np


@dataclass(frozen=True)
class AmmIndexMeta:
    """Static capabilities for an AMM implementation."""

    name: str
    algorithm_type: str  # e.g., "sketching", "sampling", "quantization"
    supports_streaming: bool = False
    supports_gpu: bool = False
    requires_training: bool = False


class AmmIndex(ABC):
    """Minimal AMM interface to standardize algorithm flows.

    This interface provides a unified API for various approximate matrix
    multiplication algorithms, including sketching-based, sampling-based,
    and quantization-based methods.
    """

    @property
    @abstractmethod
    def meta(self) -> AmmIndexMeta:
        """Return static metadata describing this AMM algorithm."""

    @abstractmethod
    def setup(self, config: dict[str, Any]) -> None:
        """Initialize the algorithm with configuration.

        Args:
            config: Algorithm-specific configuration dictionary.
                Common keys might include:
                - sketch_size: Size of sketch for sketching algorithms
                - sample_rate: Sampling rate for sampling algorithms
                - quantization_bits: Number of bits for quantization
                - use_gpu: Whether to use GPU acceleration
        """

    @abstractmethod
    def train(self, matrix_a: np.ndarray, matrix_b: Optional[np.ndarray] = None) -> None:
        """Train the algorithm on sample matrices (if required).

        Args:
            matrix_a: First matrix for training
            matrix_b: Optional second matrix for training
        """

    @abstractmethod
    def multiply(self, matrix_a: np.ndarray, matrix_b: np.ndarray) -> np.ndarray:
        """Perform approximate matrix multiplication.

        Args:
            matrix_a: First matrix (m x k)
            matrix_b: Second matrix (k x n)

        Returns:
            Approximate result matrix (m x n)
        """

    def batch_multiply(
        self,
        matrices_a: list[np.ndarray],
        matrices_b: list[np.ndarray],
    ) -> list[np.ndarray]:
        """Batch approximate matrix multiplication.

        Default implementation processes each pair sequentially.
        Subclasses can override for optimized batch processing.

        Args:
            matrices_a: List of first matrices
            matrices_b: List of second matrices

        Returns:
            List of approximate result matrices
        """
        if len(matrices_a) != len(matrices_b):
            raise ValueError(
                f"Matrix lists must have same length: {len(matrices_a)} vs {len(matrices_b)}"
            )

        return [self.multiply(a, b) for a, b in zip(matrices_a, matrices_b)]

    def get_memory_usage(self) -> dict[str, int]:
        """Return memory usage statistics in bytes.

        Returns:
            Dictionary with memory usage information:
            - sketch_size: Memory used by sketch/structure
            - total: Total memory usage
        """
        return {}

    def get_stats(self) -> dict[str, Any]:
        """Return optional diagnostic statistics.

        Returns:
            Dictionary with algorithm-specific statistics:
            - num_operations: Number of multiply operations performed
            - avg_error: Average approximation error (if tracked)
            - etc.
        """
        return {}


class StreamingAmmIndex(AmmIndex):
    """Extended interface for streaming AMM algorithms.

    Some AMM algorithms support incremental updates, allowing matrices
    to be processed in a streaming fashion.
    """

    @abstractmethod
    def update_row(self, matrix_id: str, row_idx: int, row_data: np.ndarray) -> None:
        """Update a single row of a matrix.

        Args:
            matrix_id: Identifier for the matrix ("A" or "B")
            row_idx: Index of the row to update
            row_data: New row data
        """

    @abstractmethod
    def update_column(self, matrix_id: str, col_idx: int, col_data: np.ndarray) -> None:
        """Update a single column of a matrix.

        Args:
            matrix_id: Identifier for the matrix ("A" or "B")
            col_idx: Index of the column to update
            col_data: New column data
        """

    @abstractmethod
    def get_current_result(self) -> np.ndarray:
        """Get current approximate result based on streamed updates.

        Returns:
            Current approximate matrix multiplication result
        """


# Type alias for backward compatibility
AmmAlgorithm = AmmIndex
