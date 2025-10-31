"""
Privacy Accountant
==================

Tracks and manages privacy budget across multiple unlearning operations.

Research Extension Points:
--------------------------
Students can enhance privacy accounting by:
1. Implementing advanced composition theorems (RDP, zCDP, GDP)
2. Designing adaptive budget allocation strategies
3. Creating privacy-utility trade-off optimizers
4. Building privacy budget prediction models
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PrivacySpending:
    """Record of a single privacy-consuming operation."""

    timestamp: datetime
    operation: str
    epsilon: float
    delta: float
    mechanism: str
    metadata: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"PrivacySpending({self.operation}: ε={self.epsilon:.4f}, "
            f"δ={self.delta:.6f}, mechanism={self.mechanism})"
        )


class PrivacyAccountant:
    """
    Tracks privacy budget consumption across unlearning operations.

    This class maintains a ledger of all privacy-consuming operations and
    computes the total privacy cost using composition theorems.

    **STUDENT RESEARCH POINT**: Implement tighter composition bounds.

    Attributes:
        total_epsilon_budget: Maximum allowed epsilon
        total_delta_budget: Maximum allowed delta
        composition_type: Type of composition theorem to use

    Research Ideas:
        - Implement Renyi DP composition
        - Design adaptive budget allocation
        - Create budget prediction models
    """

    def __init__(
        self,
        total_epsilon_budget: float,
        total_delta_budget: float = 1e-5,
        composition_type: str = "basic",
    ):
        """
        Initialize privacy accountant.

        Args:
            total_epsilon_budget: Total privacy budget (ε)
            total_delta_budget: Total failure probability (δ)
            composition_type: Composition theorem to use
                - "basic": Basic composition (sum of epsilons)
                - "advanced": Advanced composition (tighter bounds)
                - "moments": Moments accountant (RDP-based)

        Raises:
            ValueError: If budgets are invalid
        """
        if total_epsilon_budget <= 0:
            raise ValueError(f"epsilon budget must be positive, got {total_epsilon_budget}")
        if not (0 < total_delta_budget < 1):
            raise ValueError(f"delta budget must be in (0,1), got {total_delta_budget}")

        self.total_epsilon_budget = total_epsilon_budget
        self.total_delta_budget = total_delta_budget
        self.composition_type = composition_type

        # Ledger of privacy spending
        self._spending_history: list[PrivacySpending] = []

        # Current spent budget
        self._epsilon_spent = 0.0
        self._delta_spent = 0.0

    def record_operation(
        self,
        epsilon: float,
        delta: float,
        operation: str,
        mechanism: str,
        metadata: dict | None = None,
    ) -> bool:
        """
        Record a privacy-consuming operation.

        Args:
            epsilon: Privacy cost (ε)
            delta: Failure probability (δ)
            operation: Description of the operation
            mechanism: Name of the privacy mechanism used
            metadata: Additional information

        Returns:
            True if operation was within budget, False otherwise

        Raises:
            ValueError: If operation would exceed budget
        """
        # Compute new total cost
        new_epsilon, new_delta = self._compute_composition(epsilon, delta)

        # Check budget
        if new_epsilon > self.total_epsilon_budget:
            raise ValueError(
                f"Operation would exceed epsilon budget: "
                f"{new_epsilon:.4f} > {self.total_epsilon_budget:.4f}"
            )
        if new_delta > self.total_delta_budget:
            raise ValueError(
                f"Operation would exceed delta budget: "
                f"{new_delta:.6f} > {self.total_delta_budget:.6f}"
            )

        # Record the operation
        spending = PrivacySpending(
            timestamp=datetime.now(),
            operation=operation,
            epsilon=epsilon,
            delta=delta,
            mechanism=mechanism,
            metadata=metadata or {},
        )
        self._spending_history.append(spending)

        # Update spent budget
        self._epsilon_spent = new_epsilon
        self._delta_spent = new_delta

        return True

    def _compute_composition(self, new_epsilon: float, new_delta: float) -> tuple[float, float]:
        """
        Compute total privacy cost using composition theorem.

        **STUDENT RESEARCH POINT**: Implement advanced composition theorems.

        Args:
            new_epsilon: Privacy cost of new operation
            new_delta: Failure probability of new operation

        Returns:
            Tuple of (total_epsilon, total_delta)

        Research Ideas:
            - Implement Renyi DP composition (tighter bounds)
            - Implement zero-concentrated DP (zCDP)
            - Implement Gaussian DP (GDP)
            - Design data-dependent composition
        """
        if self.composition_type == "basic":
            return self._basic_composition(new_epsilon, new_delta)
        elif self.composition_type == "advanced":
            return self._advanced_composition(new_epsilon, new_delta)
        elif self.composition_type == "moments":
            return self._moments_composition(new_epsilon, new_delta)
        else:
            raise ValueError(f"Unknown composition type: {self.composition_type}")

    def _basic_composition(self, new_epsilon: float, new_delta: float) -> tuple[float, float]:
        """
        Basic composition: ε_total = Σε_i, δ_total = Σδ_i.

        This is the simplest but loosest bound.
        """
        total_epsilon = self._epsilon_spent + new_epsilon
        total_delta = self._delta_spent + new_delta
        return (total_epsilon, total_delta)

    def _advanced_composition(self, new_epsilon: float, new_delta: float) -> tuple[float, float]:
        """
        Advanced composition theorem.

        **STUDENT TODO**: Implement advanced composition.

        For k compositions of (ε, δ)-DP mechanisms:
        ε_total = sqrt(2k ln(1/δ')) * ε + k * ε * (e^ε - 1)
        δ_total = k * δ + δ'

        See: Dwork, Rothblum, Vadhan (2010)
        """
        # Placeholder: Use basic composition for now
        # TODO: Implement advanced composition formula
        return self._basic_composition(new_epsilon, new_delta)

    def _moments_composition(self, new_epsilon: float, new_delta: float) -> tuple[float, float]:
        """
        Moments accountant (Renyi DP composition).

        **STUDENT TODO**: Implement moments accountant.

        This provides tighter bounds for Gaussian mechanisms.
        See: Abadi et al. (2016) "Deep Learning with Differential Privacy"
        """
        # Placeholder: Use basic composition for now
        # TODO: Implement moments accountant
        return self._basic_composition(new_epsilon, new_delta)

    def get_remaining_budget(self) -> dict[str, float]:
        """
        Get remaining privacy budget.

        Returns:
            Dictionary with remaining epsilon and delta budgets
        """
        return {
            "epsilon_remaining": self.total_epsilon_budget - self._epsilon_spent,
            "delta_remaining": self.total_delta_budget - self._delta_spent,
            "epsilon_spent": self._epsilon_spent,
            "delta_spent": self._delta_spent,
        }

    def can_afford(self, epsilon: float, delta: float) -> bool:
        """
        Check if we can afford a new operation.

        Args:
            epsilon: Privacy cost of proposed operation
            delta: Failure probability of proposed operation

        Returns:
            True if operation is within budget
        """
        new_epsilon, new_delta = self._compute_composition(epsilon, delta)
        return new_epsilon <= self.total_epsilon_budget and new_delta <= self.total_delta_budget

    def get_spending_history(self) -> list[PrivacySpending]:
        """Get history of all privacy-consuming operations."""
        return self._spending_history.copy()

    def reset(self):
        """Reset privacy accountant (clear all spending history)."""
        self._spending_history.clear()
        self._epsilon_spent = 0.0
        self._delta_spent = 0.0

    def summary(self) -> dict:
        """
        Get summary statistics of privacy spending.

        Returns:
            Dictionary with summary statistics
        """
        return {
            "total_operations": len(self._spending_history),
            "epsilon_spent": self._epsilon_spent,
            "delta_spent": self._delta_spent,
            "epsilon_remaining": self.total_epsilon_budget - self._epsilon_spent,
            "delta_remaining": self.total_delta_budget - self._delta_spent,
            "budget_utilization": self._epsilon_spent / self.total_epsilon_budget,
            "composition_type": self.composition_type,
        }

    def __repr__(self) -> str:
        return (
            f"PrivacyAccountant(spent: ε={self._epsilon_spent:.4f}/{self.total_epsilon_budget:.4f}, "
            f"δ={self._delta_spent:.6f}/{self.total_delta_budget:.6f}, "
            f"operations={len(self._spending_history)})"
        )


# ============================================================================
# STUDENT RESEARCH EXTENSION POINT
# ============================================================================
"""
TODO for Students:
------------------

1. **Advanced Composition** (Medium difficulty):
   - Implement advanced composition theorem (Dwork et al. 2010)
   - Implement optimal composition (Kairouz et al. 2015)
   - Implement privacy odometer (Rogers et al. 2016)

2. **Renyi DP Composition** (Hard difficulty):
   - Implement Renyi divergence-based accounting
   - Implement privacy amplification by subsampling
   - Implement privacy amplification by iteration

3. **Adaptive Budget Allocation** (Research-level):
   - Design algorithms to optimally allocate budget across operations
   - Implement budget prediction based on query patterns
   - Create budget-aware query optimization

Example skeleton for Renyi DP accountant:

class RenyiPrivacyAccountant(PrivacyAccountant):
    def __init__(self, total_epsilon_budget, total_delta_budget, orders=(2, 4, 8, 16, 32)):
        super().__init__(total_epsilon_budget, total_delta_budget, "moments")
        self.orders = orders
        self.rdp_epsilons = {order: 0.0 for order in orders}

    def _moments_composition(self, new_epsilon, new_delta):
        # TODO: Implement Renyi DP composition
        # Update RDP at each order
        # Convert back to (ε, δ)-DP
        pass

See research papers:
- Mironov (2017): "Renyi Differential Privacy"
- Bun & Steinke (2016): "Concentrated Differential Privacy"
- Abadi et al. (2016): "Deep Learning with Differential Privacy"
"""
