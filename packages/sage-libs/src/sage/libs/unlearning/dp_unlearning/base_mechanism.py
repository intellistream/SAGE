"""
Base Privacy Mechanism
======================

Abstract base class for differential privacy mechanisms in unlearning.

Research Extension Points:
--------------------------
Students can implement new mechanisms by:
1. Subclassing BasePrivacyMechanism
2. Implementing compute_noise() with custom noise distribution
3. Implementing privacy_cost() with theoretical analysis
4. Optionally overriding perturb_vector() for advanced strategies

Example:
    class MyCustomMechanism(BasePrivacyMechanism):
        def compute_noise(self, sensitivity, epsilon, delta=None):
            # Your novel noise generation strategy
            pass

        def privacy_cost(self):
            # Your privacy budget calculation
            pass
"""

from abc import ABC, abstractmethod

import numpy as np


class BasePrivacyMechanism(ABC):
    """
    Abstract base class for differential privacy mechanisms.

    This class defines the interface that all privacy mechanisms must implement.
    Students should extend this class to create new unlearning algorithms.

    Attributes:
        epsilon: Privacy parameter (smaller = more private)
        delta: Failure probability (for (ε,δ)-DP)
        sensitivity: L1/L2 sensitivity of the query
        name: Human-readable name of the mechanism
    """

    def __init__(
        self,
        epsilon: float,
        delta: float | None = None,
        sensitivity: float = 1.0,
        name: str = "BasePrivacyMechanism",
    ):
        """
        Initialize privacy mechanism.

        Args:
            epsilon: Privacy budget (ε). Smaller values = stronger privacy.
            delta: Failure probability for approximate DP. If None, uses pure DP.
            sensitivity: Sensitivity of the query (Δf).
            name: Name of this mechanism (for logging/tracking).

        Raises:
            ValueError: If epsilon <= 0 or delta not in (0, 1)
        """
        if epsilon <= 0:
            raise ValueError(f"epsilon must be positive, got {epsilon}")
        if delta is not None and not (0 < delta < 1):
            raise ValueError(f"delta must be in (0, 1), got {delta}")

        self.epsilon = epsilon
        self.delta = delta
        self.sensitivity = sensitivity
        self.name = name

        # Track privacy cost
        self._privacy_spent = 0.0

    @abstractmethod
    def compute_noise(
        self,
        sensitivity: float | None = None,
        epsilon: float | None = None,
        delta: float | None = None,
    ) -> float:
        """
        Compute noise magnitude for this mechanism.

        **STUDENT RESEARCH POINT**: Implement novel noise distributions here.

        Args:
            sensitivity: Override default sensitivity
            epsilon: Override default epsilon
            delta: Override default delta

        Returns:
            Noise value to add to the true value

        Research Ideas:
            - Adaptive noise based on data distribution
            - Heavy-tailed distributions for robustness
            - Composition-aware noise scheduling
        """
        pass

    @abstractmethod
    def privacy_cost(self) -> tuple[float, float]:
        """
        Compute the privacy cost of this operation.

        **STUDENT RESEARCH POINT**: Derive tighter privacy bounds.

        Returns:
            Tuple of (epsilon_spent, delta_spent)

        Research Ideas:
            - Advanced composition theorems (Renyi DP, zCDP)
            - Data-dependent privacy accounting
            - Adaptive privacy budget allocation
        """
        pass

    def perturb_vector(
        self, vector: np.ndarray, indices_to_perturb: list[int] | None = None
    ) -> np.ndarray:
        """
        Perturb a vector with differential privacy.

        **STUDENT RESEARCH POINT**: Design advanced perturbation strategies.

        Args:
            vector: Original vector to perturb
            indices_to_perturb: Specific indices to perturb (None = all)

        Returns:
            Perturbed vector

        Research Ideas:
            - Dimension-selective perturbation
            - Correlation-preserving noise
            - Sparse perturbation patterns
        """
        if indices_to_perturb is None:
            indices_to_perturb = list(range(len(vector)))

        perturbed = vector.copy()
        for idx in indices_to_perturb:
            noise = self.compute_noise()
            perturbed[idx] += noise

        return perturbed

    def get_privacy_guarantee(self) -> dict[str, float]:
        """
        Get the privacy guarantee of this mechanism.

        Returns:
            Dictionary with 'epsilon' and optionally 'delta'
        """
        guarantee = {"epsilon": self.epsilon}
        if self.delta is not None:
            guarantee["delta"] = self.delta
        return guarantee

    def reset_privacy_budget(self):
        """Reset the privacy budget counter."""
        self._privacy_spent = 0.0

    def __repr__(self) -> str:
        delta_str = f", δ={self.delta}" if self.delta else ""
        return f"{self.name}(ε={self.epsilon}{delta_str}, Δf={self.sensitivity})"


# ============================================================================
# STUDENT TASK 1: Implement a simple mechanism as reference
# ============================================================================


class SimpleLaplaceMechanism(BasePrivacyMechanism):
    """
    Reference implementation: Laplace mechanism for pure ε-DP.

    Students can use this as a starting point and improve upon it.
    """

    def __init__(self, epsilon: float, sensitivity: float = 1.0):
        super().__init__(epsilon=epsilon, delta=None, sensitivity=sensitivity, name="Laplace")

    def compute_noise(
        self,
        sensitivity: float | None = None,
        epsilon: float | None = None,
        delta: float | None = None,
    ) -> float:
        """
        Generate Laplace noise: Lap(Δf / ε).

        Formula: scale = sensitivity / epsilon
        """
        sens = sensitivity or self.sensitivity
        eps = epsilon or self.epsilon
        scale = sens / eps
        return np.random.laplace(0, scale)

    def privacy_cost(self) -> tuple[float, float]:
        """
        Laplace mechanism satisfies pure ε-DP.

        Returns: (epsilon, 0)
        """
        return (self.epsilon, 0.0)


# ============================================================================
# STUDENT RESEARCH EXTENSION POINT
# ============================================================================
"""
TODO for Students:
------------------

1. **Advanced Mechanisms** (Medium difficulty):
   - Implement GaussianMechanism for (ε,δ)-DP
   - Implement ExponentialMechanism for non-numeric queries
   - Implement AnalyticGaussianMechanism with tighter bounds

2. **Novel Mechanisms** (Hard difficulty):
   - Design AdaptiveLaplaceMechanism that adjusts noise based on data
   - Implement TruncatedLaplaceMechanism for bounded domains
   - Create HybridMechanism that switches between Laplace/Gaussian

3. **Theoretical Extensions** (Research-level):
   - Prove privacy guarantees for your custom mechanism
   - Derive utility bounds (accuracy vs. privacy trade-off)
   - Analyze composition properties

Example skeleton for Gaussian mechanism:

class GaussianMechanism(BasePrivacyMechanism):
    def __init__(self, epsilon: float, delta: float, sensitivity: float = 1.0):
        super().__init__(epsilon, delta, sensitivity, name="Gaussian")

    def compute_noise(self, sensitivity=None, epsilon=None, delta=None):
        # TODO: Implement Gaussian noise with calibrated σ
        # Formula: σ = sqrt(2 * ln(1.25/δ)) * Δf / ε
        pass

    def privacy_cost(self):
        # TODO: Return (ε, δ) for Gaussian mechanism
        pass

See research papers:
- Dwork & Roth (2014): "The Algorithmic Foundations of Differential Privacy"
- Mironov (2017): "Renyi Differential Privacy"
"""
