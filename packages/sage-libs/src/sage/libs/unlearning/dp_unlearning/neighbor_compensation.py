"""
Neighbor Compensation Module
=============================

Prevents "collateral damage" to neighboring vectors when applying unlearning.

Research Extension Points:
--------------------------
Key research challenge: When we perturb/remove vector A, how do we ensure
that semantically similar vectors B, C, D are not affected?

Students can explore:
1. Graph-based compensation (build similarity graph)
2. Learned compensation (use neural networks)
3. Iterative refinement (multi-round compensation)
4. Budget-aware compensation (optimize privacy-utility trade-off)
"""

import numpy as np


class NeighborCompensation:
    """
    Compensates neighboring vectors to prevent collateral unlearning.

    **STUDENT RESEARCH POINT**: Design intelligent compensation strategies.

    Problem: When we perturb vector v_forget with noise, its k-nearest
    neighbors may see changed retrieval probabilities even though they
    should be retained.

    Solution: Apply compensatory adjustments to neighbors to restore their
    original retrieval probabilities.

    Research Ideas:
        - Graph-based propagation of compensation
        - Learning optimal compensation from data
        - Privacy-preserving compensation (avoid revealing neighbors)
    """

    def __init__(self, similarity_threshold: float = 0.8, max_neighbors: int = 10):
        """
        Initialize neighbor compensation.

        Args:
            similarity_threshold: Cosine similarity threshold for neighbors
            max_neighbors: Maximum number of neighbors to compensate
        """
        self.similarity_threshold = similarity_threshold
        self.max_neighbors = max_neighbors

    def identify_neighbors(
        self, target_vector: np.ndarray, all_vectors: np.ndarray, all_ids: list[str]
    ) -> list[tuple[str, float]]:
        """
        Identify neighbors of the target vector.

        **STUDENT RESEARCH POINT**: Design better neighbor identification.

        Args:
            target_vector: Vector being unlearned
            all_vectors: All vectors in the database
            all_ids: IDs corresponding to all_vectors

        Returns:
            List of (id, similarity) tuples for neighbors

        Research Ideas:
            - Use approximate nearest neighbor search (HNSW, FAISS)
            - Consider second-order neighbors (neighbors of neighbors)
            - Weight by multiple similarity metrics
        """
        # Compute cosine similarities
        similarities = self._compute_cosine_similarities(target_vector, all_vectors)

        # Find neighbors above threshold
        neighbors = []
        for i, sim in enumerate(similarities):
            if sim >= self.similarity_threshold:
                neighbors.append((all_ids[i], sim))

        # Sort by similarity and take top-k
        neighbors.sort(key=lambda x: x[1], reverse=True)
        return neighbors[: self.max_neighbors]

    def compute_compensation(
        self,
        original_vector: np.ndarray,
        perturbed_vector: np.ndarray,
        neighbor_vector: np.ndarray,
        neighbor_similarity: float,
    ) -> np.ndarray:
        """
        Compute compensation adjustment for a neighbor.

        **STUDENT RESEARCH POINT**: Design optimal compensation formula.

        Goal: After compensation, neighbor should have same retrieval
        probability as before perturbation.

        Args:
            original_vector: Original vector before perturbation
            perturbed_vector: Vector after perturbation
            neighbor_vector: Neighbor vector to compensate
            neighbor_similarity: Similarity between original and neighbor

        Returns:
            Compensation vector to add to neighbor

        Research Ideas:
            - Derive compensation from first-order Taylor expansion
            - Use second-order compensation for better accuracy
            - Learn compensation function from data
        """
        # Strategy 1: Linear compensation (simple but may not be optimal)
        # Idea: Adjust neighbor in opposite direction of perturbation
        perturbation = perturbed_vector - original_vector

        # Scale compensation by similarity (closer neighbors get more compensation)
        compensation_scale = neighbor_similarity
        compensation = -compensation_scale * perturbation

        return compensation

    def _compute_cosine_similarities(self, query: np.ndarray, vectors: np.ndarray) -> np.ndarray:
        """
        Compute cosine similarities efficiently.

        Args:
            query: Query vector (1D)
            vectors: Array of vectors (2D)

        Returns:
            Array of cosine similarities
        """
        # Normalize query
        query_norm = query / (np.linalg.norm(query) + 1e-10)

        # Normalize all vectors
        vectors_norm = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-10)

        # Compute dot products
        similarities = np.dot(vectors_norm, query_norm)

        return similarities

    def apply_compensation(
        self,
        original_vector: np.ndarray,
        perturbed_vector: np.ndarray,
        all_vectors: np.ndarray,
        all_ids: list[str],
    ) -> dict[str, np.ndarray]:
        """
        Apply compensation to all affected neighbors.

        Args:
            original_vector: Original vector before perturbation
            perturbed_vector: Vector after perturbation
            all_vectors: All vectors in database
            all_ids: IDs corresponding to all_vectors

        Returns:
            Dictionary mapping neighbor_id -> compensated_vector
        """
        # Identify neighbors
        neighbors = self.identify_neighbors(original_vector, all_vectors, all_ids)

        # Compute compensation for each neighbor
        compensated_vectors = {}
        for neighbor_id, similarity in neighbors:
            # Find neighbor vector
            neighbor_idx = all_ids.index(neighbor_id)
            neighbor_vector = all_vectors[neighbor_idx]

            # Compute compensation
            compensation = self.compute_compensation(
                original_vector, perturbed_vector, neighbor_vector, similarity
            )

            # Apply compensation
            compensated_vector = neighbor_vector + compensation
            compensated_vectors[neighbor_id] = compensated_vector

        return compensated_vectors

    def evaluate_compensation_quality(
        self,
        original_vector: np.ndarray,
        perturbed_vector: np.ndarray,
        neighbor_original: np.ndarray,
        neighbor_compensated: np.ndarray,
    ) -> dict[str, float]:
        """
        Evaluate quality of compensation.

        **STUDENT RESEARCH POINT**: Design better evaluation metrics.

        Args:
            original_vector: Original vector being unlearned
            perturbed_vector: Perturbed version
            neighbor_original: Original neighbor vector
            neighbor_compensated: Compensated neighbor vector

        Returns:
            Dictionary with quality metrics

        Research Ideas:
            - Measure retrieval probability change
            - Compare ranking before/after compensation
            - Evaluate semantic preservation
        """
        # Similarity before perturbation
        sim_before = np.dot(original_vector, neighbor_original) / (
            np.linalg.norm(original_vector) * np.linalg.norm(neighbor_original) + 1e-10
        )

        # Similarity after perturbation (without compensation)
        sim_after_no_comp = np.dot(perturbed_vector, neighbor_original) / (
            np.linalg.norm(perturbed_vector) * np.linalg.norm(neighbor_original) + 1e-10
        )

        # Similarity after compensation
        sim_after_comp = np.dot(perturbed_vector, neighbor_compensated) / (
            np.linalg.norm(perturbed_vector) * np.linalg.norm(neighbor_compensated) + 1e-10
        )

        # Change in neighbor vector
        neighbor_change = np.linalg.norm(neighbor_compensated - neighbor_original)

        return {
            "similarity_before": float(sim_before),
            "similarity_after_no_compensation": float(sim_after_no_comp),
            "similarity_after_compensation": float(sim_after_comp),
            "similarity_recovery": float(
                abs(sim_after_comp - sim_before) / (abs(sim_before) + 1e-10)
            ),
            "neighbor_change_magnitude": float(neighbor_change),
        }


# ============================================================================
# STUDENT RESEARCH EXTENSION POINT
# ============================================================================
"""
TODO for Students:
------------------

1. **Graph-Based Compensation** (Medium difficulty):
   - Build similarity graph of all vectors
   - Propagate compensation through graph edges
   - Implement iterative refinement

2. **Learned Compensation** (Hard difficulty):
   - Train a neural network to predict optimal compensation
   - Use reinforcement learning to optimize compensation strategy
   - Implement meta-learning for adaptation

3. **Theoretical Analysis** (Research-level):
   - Prove bounds on retrieval probability changes
   - Derive privacy cost of compensation operations
   - Analyze convergence of iterative compensation

Example skeleton for graph-based compensation:

class GraphBasedCompensation(NeighborCompensation):
    def __init__(self, similarity_threshold=0.8, max_neighbors=10, propagation_depth=2):
        super().__init__(similarity_threshold, max_neighbors)
        self.propagation_depth = propagation_depth
        self.graph = None

    def build_similarity_graph(self, vectors, ids):
        # TODO: Build k-NN graph
        # Use networkx or custom graph implementation
        pass

    def propagate_compensation(self, source_id, initial_compensation):
        # TODO: Propagate compensation through graph
        # Use breadth-first or belief propagation
        pass

See research papers:
- Jia et al. (2019): "Certified Robustness to Adversarial Examples with DP"
- Guo et al. (2019): "Certified Robustness to Text Adversarial Attacks"
- Wang et al. (2020): "Differentially Private Graph Neural Networks"
"""
