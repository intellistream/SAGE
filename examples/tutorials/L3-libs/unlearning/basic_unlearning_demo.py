"""
Basic Unlearning Demo
======================

Demonstrates the basic usage of the SAGE Unlearning Library.

This example shows:
1. How to create vectors (simulating embeddings)
2. How to use the UnlearningEngine
3. How to evaluate unlearning quality

**For Students**: This is your starting point!
Modify and extend this example to test your algorithms.

@test:allow-demo
"""

import numpy as np

from sage.libs.privacy.unlearning import UnlearningEngine


def generate_synthetic_vectors(n_vectors: int = 100, dim: int = 128) -> tuple:
    """
    Generate synthetic embedding vectors for testing.

    In real usage, these would come from a RAG system's vector database.
    """
    # Generate random vectors
    vectors = np.random.randn(n_vectors, dim)
    # L2 normalize (common for embeddings)
    vectors = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-10)

    # Generate IDs
    ids = [f"doc_{i}" for i in range(n_vectors)]

    return vectors, ids


def main():
    print("=" * 70)
    print("SAGE Unlearning Library - Basic Demo")
    print("=" * 70)
    print()

    # Step 1: Generate synthetic data
    print("Step 1: Generating synthetic vectors...")
    all_vectors, all_ids = generate_synthetic_vectors(n_vectors=100, dim=128)
    print(f"  Generated {len(all_vectors)} vectors of dimension {all_vectors.shape[1]}")
    print()

    # Step 2: Select vectors to forget
    print("Step 2: Selecting vectors to forget...")
    n_forget = 5
    forget_indices = np.random.choice(len(all_vectors), size=n_forget, replace=False)
    vectors_to_forget = all_vectors[forget_indices]
    ids_to_forget = [all_ids[i] for i in forget_indices]
    print(f"  Selected {n_forget} vectors to forget: {ids_to_forget}")
    print()

    # Step 3: Initialize Unlearning Engine
    print("Step 3: Initializing Unlearning Engine...")
    engine = UnlearningEngine(
        epsilon=1.0,  # Privacy parameter
        delta=1e-5,  # Failure probability
        total_budget_epsilon=10.0,  # Total privacy budget
        enable_compensation=True,  # Enable neighbor compensation
    )
    print(f"  Engine initialized: {engine.mechanism}")
    print(f"  Privacy budget: ε={engine.privacy_accountant.total_epsilon_budget}")
    print()

    # Step 4: Perform unlearning
    print("Step 4: Performing unlearning...")
    print("  Strategy: uniform perturbation")

    result = engine.unlearn_vectors(
        vectors_to_forget=vectors_to_forget,
        vector_ids_to_forget=ids_to_forget,
        all_vectors=all_vectors,
        all_vector_ids=all_ids,
        perturbation_strategy="uniform",
    )

    print(f"\n  Result: {result}")
    print(
        f"  Privacy cost: ε={result.privacy_cost[0]:.4f}, δ={result.privacy_cost[1]:.6f}"
    )
    print(f"  Vectors unlearned: {result.num_vectors_unlearned}")
    print(f"  Neighbors compensated: {result.num_neighbors_compensated}")
    print()

    # Step 5: Check privacy budget
    print("Step 5: Checking remaining privacy budget...")
    status = engine.get_privacy_status()
    remaining = status["remaining_budget"]
    print(
        f"  Remaining: ε={remaining['epsilon_remaining']:.4f}, δ={remaining['delta_remaining']:.6f}"
    )
    print(
        f"  Budget utilization: {status['accountant_summary']['budget_utilization']:.1%}"
    )
    print()

    # Step 6: Try different strategies
    print("Step 6: Comparing perturbation strategies...")
    strategies = ["uniform", "selective", "adaptive"]

    for strategy in strategies:
        # Reset engine for fair comparison
        test_engine = UnlearningEngine(epsilon=1.0, enable_compensation=False)

        test_result = test_engine.unlearn_vectors(
            vectors_to_forget=vectors_to_forget[:2],  # Use fewer vectors for comparison
            vector_ids_to_forget=ids_to_forget[:2],
            perturbation_strategy=strategy,
        )

        perturbed = test_result.metadata["perturbed_vectors"]
        original = vectors_to_forget[:2]

        # Measure impact
        l2_dist = np.mean([np.linalg.norm(o - p) for o, p in zip(original, perturbed)])
        cos_sim = np.mean(
            [
                np.dot(o, p) / (np.linalg.norm(o) * np.linalg.norm(p))
                for o, p in zip(original, perturbed)
            ]
        )

        print(f"  {strategy:12s}: L2={l2_dist:.4f}, CosSim={cos_sim:.4f}")

    print()
    print("=" * 70)
    print("Demo completed successfully!")
    print("=" * 70)
    print()
    print("Next steps for students:")
    print("  1. Implement new privacy mechanisms in algorithms/")
    print(
        "  2. Design better perturbation strategies in dp_unlearning/vector_perturbation.py"
    )
    print(
        "  3. Enhance neighbor compensation in dp_unlearning/neighbor_compensation.py"
    )
    print("  4. Add comprehensive evaluation metrics in evaluation/metrics.py")
    print()


if __name__ == "__main__":
    main()
