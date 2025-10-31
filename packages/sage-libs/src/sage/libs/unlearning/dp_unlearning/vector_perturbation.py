"""
Vector Perturbation Module
===========================

Implements differential privacy perturbation strategies for embedding vectors.

Research Extension Points:
--------------------------
Students can design novel perturbation strategies:
1. Dimension-selective perturbation (perturb important dimensions less)
2. Correlation-preserving perturbation (maintain vector relationships)
3. Sparse perturbation (add noise to few dimensions)
4. Adaptive perturbation (adjust based on vector properties)
"""

import numpy as np

from .base_mechanism import BasePrivacyMechanism


class VectorPerturbation:
    """
    Applies differential privacy perturbation to embedding vectors.

    **STUDENT RESEARCH POINT**: Design advanced perturbation strategies.

    This class provides methods to perturb vectors while maintaining their
    semantic properties as much as possible under privacy constraints.

    Research Ideas:
        - Dimension importance weighting
        - Structured noise (preserving vector subspaces)
        - Multi-resolution perturbation
    """

    def __init__(self, mechanism: BasePrivacyMechanism):
        """
        Initialize vector perturbation.

        Args:
            mechanism: Privacy mechanism to use for noise generation
        """
        self.mechanism = mechanism

    def perturb_single_vector(self, vector: np.ndarray, strategy: str = "uniform") -> np.ndarray:
        """
        Perturb a single vector with DP noise.

        **STUDENT RESEARCH POINT**: Implement advanced strategies.

        Args:
            vector: Original embedding vector
            strategy: Perturbation strategy
                - "uniform": Add noise to all dimensions
                - "selective": Add noise to selected dimensions
                - "adaptive": Adaptive noise based on dimension importance

        Returns:
            Perturbed vector

        Research Ideas:
            - Implement dimension importance scoring
            - Design correlation-preserving noise
            - Create privacy-utility optimal perturbation
        """
        if strategy == "uniform":
            return self._uniform_perturbation(vector)
        elif strategy == "selective":
            return self._selective_perturbation(vector)
        elif strategy == "adaptive":
            return self._adaptive_perturbation(vector)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _uniform_perturbation(self, vector: np.ndarray) -> np.ndarray:
        """
        Add uniform noise to all dimensions.

        This is the baseline approach: simple but may destroy semantic structure.
        """
        perturbed = vector.copy()
        for i in range(len(vector)):
            noise = self.mechanism.compute_noise()
            perturbed[i] += noise
        return perturbed

    def _selective_perturbation(self, vector: np.ndarray) -> np.ndarray:
        """
        Add noise to selected dimensions only.

        **STUDENT TODO**: Implement dimension selection logic.

        Research Ideas:
            - Select dimensions with highest variance
            - Select dimensions that least affect semantic similarity
            - Use PCA to identify important dimensions
        """
        # Placeholder: Perturb random 50% of dimensions
        # TODO: Implement smart dimension selection
        perturbed = vector.copy()
        dim = len(vector)
        selected_dims = np.random.choice(dim, size=dim // 2, replace=False)

        for i in selected_dims:
            noise = self.mechanism.compute_noise()
            perturbed[i] += noise

        return perturbed

    def _adaptive_perturbation(self, vector: np.ndarray) -> np.ndarray:
        """
        Adaptive noise based on dimension importance.

        **STUDENT TODO**: Implement adaptive strategy.

        Research Ideas:
            - Weight noise inversely by dimension importance
            - Use gradient information (if available)
            - Learn optimal noise allocation
        """
        # Placeholder: Use magnitude as importance indicator
        # TODO: Implement sophisticated importance scoring
        perturbed = vector.copy()
        magnitudes = np.abs(vector)
        total_magnitude = np.sum(magnitudes) + 1e-10

        for i in range(len(vector)):
            # Less noise for important (high magnitude) dimensions
            importance = magnitudes[i] / total_magnitude
            adaptive_sensitivity = self.mechanism.sensitivity * (1 - importance)
            noise = self.mechanism.compute_noise(sensitivity=adaptive_sensitivity)
            perturbed[i] += noise

        return perturbed

    def perturb_batch_vectors(self, vectors: np.ndarray, strategy: str = "uniform") -> np.ndarray:
        """
        Perturb a batch of vectors.

        Args:
            vectors: Array of shape (n_vectors, dim)
            strategy: Perturbation strategy

        Returns:
            Array of perturbed vectors
        """
        perturbed_batch = np.zeros_like(vectors)
        for i, vector in enumerate(vectors):
            perturbed_batch[i] = self.perturb_single_vector(vector, strategy)
        return perturbed_batch

    def measure_perturbation_impact(self, original: np.ndarray, perturbed: np.ndarray) -> dict:
        """
        Measure the impact of perturbation on vector properties.

        Args:
            original: Original vector
            perturbed: Perturbed vector

        Returns:
            Dictionary with impact metrics
        """
        l2_distance = np.linalg.norm(original - perturbed)
        l1_distance = np.sum(np.abs(original - perturbed))
        cosine_similarity = np.dot(original, perturbed) / (
            np.linalg.norm(original) * np.linalg.norm(perturbed) + 1e-10
        )

        return {
            "l2_distance": l2_distance,
            "l1_distance": l1_distance,
            "cosine_similarity": cosine_similarity,
            "relative_change": l2_distance / (np.linalg.norm(original) + 1e-10),
        }


# ============================================================================
# STUDENT RESEARCH EXTENSION POINT
# ============================================================================
"""
TODO for Students:
------------------

1. **Advanced Perturbation Strategies** (Medium difficulty):
   - Implement PCA-based selective perturbation
   - Implement locality-sensitive perturbation
   - Implement subspace-preserving perturbation

2. **Semantic-Aware Perturbation** (Hard difficulty):
   - Design perturbation that preserves semantic clusters
   - Implement attention-weighted perturbation
   - Create learned perturbation (use neural networks)

3. **Theoretical Analysis** (Research-level):
   - Prove utility bounds for each strategy
   - Derive optimal dimension selection algorithm
   - Analyze privacy-utility Pareto frontier

Example skeleton for PCA-based perturbation:

class PCAPreservingPerturbation(VectorPerturbation):
    def __init__(self, mechanism, n_components=0.95):
        super().__init__(mechanism)
        self.n_components = n_components
        self.pca = None

    def fit_pca(self, vectors):
        # TODO: Fit PCA on representative vectors
        from sklearn.decomposition import PCA
        self.pca = PCA(n_components=self.n_components)
        self.pca.fit(vectors)

    def _pca_preserving_perturbation(self, vector):
        # TODO: Perturb in complement of principal subspace
        # This preserves main semantic structure
        pass

See research papers:
- Duchi et al. (2013): "Local Privacy and Statistical Minimax Rates"
- Hardt & Talwar (2010): "Geometry of Differential Privacy"
"""
