"""Example: Using the AMMS unified interface.

This example demonstrates how to use the refactored AMMS interface
to perform approximate matrix multiplication.
"""

from sage.libs.amms import registered


def example_basic_usage():
    """Basic usage of AMMS interface."""
    print("=== Basic AMMS Usage ===\n")

    # Check available algorithms
    available = registered()
    print(f"Available algorithms: {available}\n")

    # Note: Actual algorithm implementations need to be registered first
    # This is a template showing how to use the interface

    # Example: Create a CountSketch AMM instance (once implemented)
    # amm = create("countsketch", sketch_size=1000)

    # Setup with configuration
    # config = {
    #     "sketch_size": 1000,
    #     "hash_functions": 5,
    #     "use_gpu": False
    # }
    # amm.setup(config)

    # Create sample matrices
    # matrix_a = np.random.randn(100, 50)
    # matrix_b = np.random.randn(50, 80)

    # Perform approximate multiplication
    # result = amm.multiply(matrix_a, matrix_b)

    # Compare with exact result
    # exact = matrix_a @ matrix_b
    # error = np.linalg.norm(result - exact) / np.linalg.norm(exact)
    # print(f"Relative error: {error:.4f}")

    print("Note: Algorithm implementations need to be registered first.")
    print("See implementations/ for C++ algorithm code.")


def example_streaming_amm():
    """Example of streaming AMM (for algorithms that support it)."""
    print("\n=== Streaming AMM Example ===\n")

    # For streaming algorithms, you can update matrices incrementally
    # streaming_amm = create("streaming_countsketch", sketch_size=1000)

    # Initial setup
    # streaming_amm.setup({"sketch_size": 1000})

    # Update rows incrementally
    # for i in range(100):
    #     row_data = np.random.randn(50)
    #     streaming_amm.update_row("A", i, row_data)

    # Get current result
    # result = streaming_amm.get_current_result()

    print("Note: Streaming AMM requires StreamingAmmIndex implementation.")


def example_batch_processing():
    """Example of batch matrix multiplication."""
    print("\n=== Batch Processing Example ===\n")

    # Batch processing multiple matrix pairs
    # amm = create("fastjlt", sketch_size=500)

    # matrices_a = [np.random.randn(100, 50) for _ in range(10)]
    # matrices_b = [np.random.randn(50, 80) for _ in range(10)]

    # results = amm.batch_multiply(matrices_a, matrices_b)

    print("Note: Batch processing uses default implementation.")
    print("Override batch_multiply() for optimized batch processing.")


def example_algorithm_metadata():
    """Example of accessing algorithm metadata."""
    print("\n=== Algorithm Metadata Example ===\n")

    # from sage.libs.amms import get_meta

    # meta = get_meta("countsketch")
    # if meta:
    #     print(f"Algorithm: {meta.name}")
    #     print(f"Type: {meta.algorithm_type}")
    #     print(f"Supports streaming: {meta.supports_streaming}")
    #     print(f"Supports GPU: {meta.supports_gpu}")
    #     print(f"Requires training: {meta.requires_training}")

    print("Note: Metadata is registered when algorithms are registered.")


if __name__ == "__main__":
    print("AMMS Interface Examples")
    print("=" * 50)

    example_basic_usage()
    example_streaming_amm()
    example_batch_processing()
    example_algorithm_metadata()

    print("\n" + "=" * 50)
    print("To use these examples:")
    print("1. Implement algorithms in implementations/")
    print("2. Create wrappers in wrappers/")
    print("3. Register algorithms using register()")
    print("4. Then run these examples")
