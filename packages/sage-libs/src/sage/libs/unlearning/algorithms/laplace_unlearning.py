"""
Laplace Mechanism for Unlearning
=================================

Implements the Laplace mechanism for pure ε-differential privacy.

This is a reference implementation. Students can improve upon it!
"""

import numpy as np

from ..dp_unlearning.base_mechanism import BasePrivacyMechanism


class LaplaceMechanism(BasePrivacyMechanism):
    """
    Laplace mechanism for pure ε-DP.

    **STUDENT TODO**: Enhance this implementation!

    The Laplace mechanism adds noise from Lap(Δf/ε) to achieve ε-DP.

    Improvements to consider:
    - Implement truncated Laplace for bounded domains
    - Add adaptive sensitivity estimation
    - Implement privacy amplification techniques
    """

    def __init__(
        self,
        epsilon: float,
        sensitivity: float = 1.0,
        clip_bound: float | None = None,
    ):
        """
        Initialize Laplace mechanism.

        Args:
            epsilon: Privacy parameter
            sensitivity: Query sensitivity
            clip_bound: Optional clipping bound for noise
        """
        super().__init__(
            epsilon=epsilon,
            delta=None,  # Pure DP has no delta
            sensitivity=sensitivity,
            name="Laplace",
        )
        self.clip_bound = clip_bound

    def compute_noise(
        self,
        sensitivity: float | None = None,
        epsilon: float | None = None,
        delta: float | None = None,
    ) -> float:
        """
        Generate Laplace noise: Lap(Δf / ε).

        Formula:
            scale = sensitivity / epsilon
            noise ~ Laplace(0, scale)
        """
        sens = sensitivity or self.sensitivity
        eps = epsilon or self.epsilon

        scale = sens / eps
        noise = np.random.laplace(0, scale)

        # Optional: Clip noise to bound
        if self.clip_bound is not None:
            noise = np.clip(noise, -self.clip_bound, self.clip_bound)

        return noise

    def privacy_cost(self) -> tuple[float, float]:
        """
        Laplace mechanism satisfies pure ε-DP.

        Returns: (epsilon, 0)
        """
        return (self.epsilon, 0.0)


# ============================================================================
# STUDENT RESEARCH EXTENSION
# ============================================================================
"""
TODO for Students:
------------------

1. Implement TruncatedLaplaceMechanism:
   - Truncate noise to [-B, B] for bounded domains
   - Derive tighter privacy guarantees for truncated version
   - Prove utility bounds

2. Implement AdaptiveLaplaceMechanism:
   - Estimate sensitivity from data
   - Adjust epsilon based on query characteristics
   - Implement privacy amplification by subsampling

Example skeleton:

class TruncatedLaplaceMechanism(LaplaceMechanism):
    def __init__(self, epsilon, sensitivity=1.0, truncation_bound=5.0):
        super().__init__(epsilon, sensitivity)
        self.truncation_bound = truncation_bound
        self.name = "TruncatedLaplace"

    def compute_noise(self, sensitivity=None, epsilon=None, delta=None):
        # TODO: Generate truncated Laplace noise
        # Rejection sampling or inverse CDF method
        pass

    def privacy_cost(self):
        # TODO: Derive tighter epsilon for truncated case
        # See: Geng et al. (2019) "Tight Privacy Analysis"
        pass
"""
