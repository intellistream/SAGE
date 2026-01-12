"""Base classes and interfaces for privacy.

This module defines abstract interfaces for privacy-preserving algorithms:
- BaseUnlearner: Machine unlearning base class
- BasePrivacyMechanism: Differential privacy mechanism (re-export from unlearning)
- BaseDPOptimizer: Differentially private optimizer
- BaseFederatedClient: Federated learning client

Implementations are provided by the external 'isage-privacy' package.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

# Re-export existing implementation
from ..unlearning.dp_unlearning.base_mechanism import (
    BasePrivacyMechanism,
)


class UnlearningMethod(Enum):
    """Types of machine unlearning methods."""

    # Exact unlearning
    RETRAIN = "retrain"  # Full retraining from scratch
    SISA = "sisa"  # Sharded, Isolated, Sliced, Aggregated

    # Approximate unlearning
    GRADIENT_ASCENT = "gradient_ascent"
    INFLUENCE_FUNCTION = "influence_function"
    FISHER_FORGETTING = "fisher_forgetting"
    AMNESIAC = "amnesiac"

    # DP-based unlearning
    DP_SGD = "dp_sgd"
    PATE = "pate"

    # Custom
    CUSTOM = "custom"


class PrivacyLevel(Enum):
    """Privacy strength levels."""

    NONE = "none"
    LOW = "low"  # epsilon > 10
    MEDIUM = "medium"  # 1 < epsilon <= 10
    HIGH = "high"  # 0.1 < epsilon <= 1
    VERY_HIGH = "very_high"  # epsilon <= 0.1


@dataclass
class PrivacyBudget:
    """Privacy budget configuration."""

    epsilon: float  # Privacy loss parameter
    delta: float = 1e-5  # Failure probability

    # Optional: per-query budgets
    per_query_epsilon: Optional[float] = None
    max_queries: Optional[int] = None

    # Composition method
    composition: str = "advanced"  # "basic", "advanced", "rdp"

    @property
    def level(self) -> PrivacyLevel:
        """Determine privacy level from epsilon."""
        if self.epsilon > 10:
            return PrivacyLevel.LOW
        elif self.epsilon > 1:
            return PrivacyLevel.MEDIUM
        elif self.epsilon > 0.1:
            return PrivacyLevel.HIGH
        else:
            return PrivacyLevel.VERY_HIGH


@dataclass
class UnlearningResult:
    """Result of an unlearning operation."""

    success: bool
    method: UnlearningMethod
    samples_forgotten: int

    # Privacy guarantees
    privacy_budget_spent: Optional[PrivacyBudget] = None
    verification_score: Optional[float] = None  # How well unlearning succeeded

    # Performance
    time_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseUnlearner(ABC):
    """Abstract base class for machine unlearning.

    Examples of implementations:
    - SISAUnlearner: Sharded training for efficient unlearning
    - GradientAscentUnlearner: Approximate unlearning via gradient ascent
    - FisherUnlearner: Fisher information-based forgetting
    - AmnesiacUnlearner: Cached update-based unlearning
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unlearner name."""
        pass

    @property
    def method(self) -> UnlearningMethod:
        """Return the unlearning method type."""
        return UnlearningMethod.CUSTOM

    @abstractmethod
    def unlearn(
        self,
        model: Any,
        forget_data: Any,
        retain_data: Optional[Any] = None,
        **kwargs: Any,
    ) -> UnlearningResult:
        """Unlearn (forget) specific data from a model.

        Args:
            model: The trained model
            forget_data: Data to be forgotten
            retain_data: Data to retain (optional, for verification)
            **kwargs: Method-specific parameters

        Returns:
            UnlearningResult with success status and metrics
        """
        pass

    def verify_unlearning(
        self,
        model: Any,
        forget_data: Any,
        original_model: Optional[Any] = None,
        **kwargs: Any,
    ) -> float:
        """Verify that unlearning was successful.

        Args:
            model: Model after unlearning
            forget_data: Data that should have been forgotten
            original_model: Model before unlearning (optional)
            **kwargs: Verification parameters

        Returns:
            Verification score (0 = failed, 1 = perfect unlearning)
        """
        raise NotImplementedError("Verification not implemented for this unlearner")


class BaseDPOptimizer(ABC):
    """Abstract base class for differentially private optimizers.

    Examples of implementations:
    - DPSGDOptimizer: DP-SGD (Differentially Private Stochastic Gradient Descent)
    - DPAdamOptimizer: DP-Adam
    - PATEOptimizer: Private Aggregation of Teacher Ensembles
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the optimizer name."""
        pass

    @abstractmethod
    def step(
        self,
        params: Any,
        gradients: Any,
        privacy_budget: PrivacyBudget,
        **kwargs: Any,
    ) -> Any:
        """Perform one optimization step with DP guarantees.

        Args:
            params: Model parameters
            gradients: Computed gradients
            privacy_budget: Privacy budget for this step
            **kwargs: Optimizer-specific parameters

        Returns:
            Updated parameters
        """
        pass

    @abstractmethod
    def get_privacy_spent(self) -> PrivacyBudget:
        """Get total privacy budget spent so far.

        Returns:
            Cumulative privacy budget used
        """
        pass

    def clip_gradients(
        self,
        gradients: Any,
        max_norm: float,
    ) -> Any:
        """Clip gradients to bound sensitivity.

        Args:
            gradients: Raw gradients
            max_norm: Maximum L2 norm

        Returns:
            Clipped gradients
        """
        raise NotImplementedError("Gradient clipping not implemented")


class BaseFederatedClient(ABC):
    """Abstract base class for federated learning clients.

    Examples of implementations:
    - FedAvgClient: Federated averaging client
    - FedProxClient: FedProx with proximal term
    - DPFedClient: Differentially private federated client
    """

    @property
    @abstractmethod
    def client_id(self) -> str:
        """Return the client identifier."""
        pass

    @abstractmethod
    def local_train(
        self,
        model: Any,
        local_data: Any,
        num_epochs: int = 1,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Train model on local data.

        Args:
            model: Global model to fine-tune
            local_data: Client's local dataset
            num_epochs: Local training epochs
            **kwargs: Training parameters

        Returns:
            Dictionary with model updates and metrics
        """
        pass

    @abstractmethod
    def compute_update(
        self,
        old_model: Any,
        new_model: Any,
        **kwargs: Any,
    ) -> Any:
        """Compute model update to send to server.

        Args:
            old_model: Model before local training
            new_model: Model after local training
            **kwargs: Update parameters

        Returns:
            Model update (gradients or weight difference)
        """
        pass

    def add_noise_to_update(
        self,
        update: Any,
        privacy_mechanism: BasePrivacyMechanism,
    ) -> Any:
        """Add noise to update for differential privacy.

        Args:
            update: Model update
            privacy_mechanism: Privacy mechanism to use

        Returns:
            Noisy update
        """
        raise NotImplementedError("DP noise not implemented for this client")


class BaseFederatedServer(ABC):
    """Abstract base class for federated learning servers.

    Examples of implementations:
    - FedAvgServer: Federated averaging server
    - SecAggServer: Secure aggregation server
    - DPFedServer: DP-aware federated server
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the server name."""
        pass

    @abstractmethod
    def aggregate(
        self,
        updates: list[Any],
        weights: Optional[list[float]] = None,
        **kwargs: Any,
    ) -> Any:
        """Aggregate client updates.

        Args:
            updates: List of client updates
            weights: Optional weights for each client
            **kwargs: Aggregation parameters

        Returns:
            Aggregated update
        """
        pass

    @abstractmethod
    def update_global_model(
        self,
        model: Any,
        aggregated_update: Any,
        **kwargs: Any,
    ) -> Any:
        """Apply aggregated update to global model.

        Args:
            model: Current global model
            aggregated_update: Aggregated client updates
            **kwargs: Update parameters

        Returns:
            Updated global model
        """
        pass

    def select_clients(
        self,
        clients: list["BaseFederatedClient"],
        fraction: float = 1.0,
        **kwargs: Any,
    ) -> list["BaseFederatedClient"]:
        """Select clients for a training round.

        Args:
            clients: All available clients
            fraction: Fraction of clients to select
            **kwargs: Selection parameters

        Returns:
            Selected clients
        """
        import random

        k = max(1, int(len(clients) * fraction))
        return random.sample(clients, k)


__all__ = [
    # Enums
    "UnlearningMethod",
    "PrivacyLevel",
    # Data classes
    "PrivacyBudget",
    "UnlearningResult",
    # Base classes
    "BasePrivacyMechanism",
    "BaseUnlearner",
    "BaseDPOptimizer",
    "BaseFederatedClient",
    "BaseFederatedServer",
]
