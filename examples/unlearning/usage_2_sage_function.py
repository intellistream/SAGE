"""
SAGE Unlearning - Function Integration

This module demonstrates how to integrate unlearning with SAGE Functions.

Note: This example shows architectural patterns. A complete Pipeline
requires a full SAGE runtime environment. For testing and quick verification,
use usage_1_direct_library.py.

This shows:
1. How to wrap unlearning in a Function class
2. How to integrate with SAGE data processing
3. How to manage state in functions
4. How to compose multiple functions

**For Students**: Study this to understand how to integrate unlearning
with SAGE's data processing framework.
"""

import numpy as np
from sage.libs.unlearning import UnlearningEngine


class UnlearningFunctionExample:
    """
    Demonstrates wrapping unlearning logic in a function-like class.

    In a full SAGE Pipeline, this would inherit from BaseFunction.
    Here we show the pattern without requiring the full runtime.
    """

    def __init__(self, epsilon=1.0):
        """Initialize the function"""
        self.engine = UnlearningEngine(
            total_budget_epsilon=epsilon, enable_compensation=True
        )
        self.vectors_processed = 0
        self.vectors_forgotten = 0

    def process_vector(self, vector_id, vector, should_forget=False):
        """
        Process a single vector.

        In a real Pipeline, this would be the execute() method.
        """
        self.vectors_processed += 1

        if should_forget:
            self.vectors_forgotten += 1
            # In a real scenario, this would be batched
            # For demo, we just track it
            return {
                "action": "forgot",
                "vector_id": vector_id,
                "privacy_cost": 0.1,  # Simplified
            }

        return {"action": "kept", "vector_id": vector_id, "vector": vector}


def example_function_pattern():
    """Example 1: Function Pattern Demonstration"""
    print("\n" + "=" * 70)
    print("Example 1: Unlearning Function Pattern")
    print("=" * 70)

    func = UnlearningFunctionExample(epsilon=1.0)

    # Simulate processing vectors
    vectors = np.random.randn(10, 64).astype(np.float32)
    vectors = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-10)

    forget_indices = {0, 3, 7}  # Which vectors to forget

    print(f"Processing {len(vectors)} vectors...")
    results = []

    for i, vector in enumerate(vectors):
        should_forget = i in forget_indices
        result = func.process_vector(f"doc_{i}", vector, should_forget)
        results.append(result)
        if should_forget:
            print(f"  - Vector {i}: Forgotten")

    print("\n📊 Summary:")
    print(f"  Vectors processed: {func.vectors_processed}")
    print(f"  Vectors forgotten: {func.vectors_forgotten}")
    forgotten_count = sum(1 for r in results if r["action"] == "forgot")
    print(f"  Verified forgotten: {forgotten_count}")


def example_batched_unlearning():
    """Example 2: Batched Unlearning in Functions"""
    print("\n" + "=" * 70)
    print("Example 2: Batched Unlearning")
    print("=" * 70)

    # Create function with batching
    engine = UnlearningEngine(total_budget_epsilon=10.0)

    # Simulate batching vectors
    all_vectors = np.random.randn(100, 128).astype(np.float32)
    all_vectors = all_vectors / (
        np.linalg.norm(all_vectors, axis=1, keepdims=True) + 1e-10
    )
    all_ids = [f"doc_{i}" for i in range(100)]

    # Forget vectors in batches
    batch_size = 10
    for batch_idx in range(3):
        start_idx = batch_idx * batch_size
        end_idx = start_idx + batch_size

        forget_vectors = all_vectors[start_idx:end_idx]
        forget_ids = all_ids[start_idx:end_idx]

        result = engine.unlearn_vectors(
            vectors_to_forget=forget_vectors,
            vector_ids_to_forget=forget_ids,
            all_vectors=all_vectors,
            all_vector_ids=all_ids,
            perturbation_strategy="selective",
        )

        if result.success:
            print(
                f"  Batch {batch_idx}: Forgotten {result.num_vectors_unlearned} vectors, "
                f"Privacy cost: ε={result.privacy_cost[0]:.4f}"
            )


def example_stateful_processing():
    """Example 3: Stateful Vector Processing"""
    print("\n" + "=" * 70)
    print("Example 3: Stateful Vector Processing")
    print("=" * 70)

    class StatefulProcessor:
        """Processor that maintains state across calls"""

        def __init__(self):
            self.state = {
                "vectors_accumulated": [],
                "ids_accumulated": [],
                "total_forgotten": 0,
                "privacy_spent": 0.0,
            }
            self.engine = UnlearningEngine(total_budget_epsilon=5.0)

        def add_vector(self, vector_id, vector):
            self.state["vectors_accumulated"].append(vector)
            self.state["ids_accumulated"].append(vector_id)

        def flush_and_forget(self, num_to_forget=3):
            """Accumulate and then forget"""
            if len(self.state["vectors_accumulated"]) < num_to_forget:
                return None

            forget_vectors = np.array(self.state["vectors_accumulated"][:num_to_forget])
            forget_ids = self.state["ids_accumulated"][:num_to_forget]
            all_vectors = np.array(self.state["vectors_accumulated"])
            all_ids = self.state["ids_accumulated"]

            result = self.engine.unlearn_vectors(
                vectors_to_forget=forget_vectors,
                vector_ids_to_forget=forget_ids,
                all_vectors=all_vectors,
                all_vector_ids=all_ids,
                perturbation_strategy="uniform",
            )

            if result.success:
                self.state["total_forgotten"] += result.num_vectors_unlearned
                self.state["privacy_spent"] += result.privacy_cost[0]
                # Clear processed vectors
                self.state["vectors_accumulated"] = self.state["vectors_accumulated"][
                    num_to_forget:
                ]
                self.state["ids_accumulated"] = self.state["ids_accumulated"][
                    num_to_forget:
                ]

            return result

    processor = StatefulProcessor()

    # Add vectors
    for i in range(10):
        vector = np.random.randn(64).astype(np.float32)
        vector = vector / (np.linalg.norm(vector) + 1e-10)
        processor.add_vector(f"doc_{i}", vector)

    print("Added 10 vectors to processor")

    # Flush and forget in batches
    result = processor.flush_and_forget(num_to_forget=5)
    if result:
        print(
            f"Batch 1: Forgotten {result.num_vectors_unlearned}, Privacy cost: ε={result.privacy_cost[0]:.4f}"
        )

    print("\n📊 Final state:")
    print(f"  Total vectors forgotten: {processor.state['total_forgotten']}")
    print(f"  Total privacy spent: ε={processor.state['privacy_spent']:.4f}")
    print(f"  Vectors still in buffer: {len(processor.state['vectors_accumulated'])}")


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("SAGE Unlearning Library - Function Integration Examples")
    print("=" * 70)
    print("\n这些示例展示了如何在 SAGE Function 中使用 unlearning 库。")
    print("These examples show how to integrate unlearning with SAGE Functions.\n")

    # Run examples
    example_function_pattern()
    example_batched_unlearning()
    example_stateful_processing()

    print("\n" + "=" * 70)
    print("✅ All examples completed successfully!")
    print("=" * 70)
    print("\n💡 Next steps:")
    print("  1. Study the patterns shown here")
    print("  2. Implement custom data processing logic")
    print("  3. See usage_3_memory_service.py for service integration\n")


if __name__ == "__main__":
    main()
