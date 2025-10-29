"""
SAGE Unlearning - Usage Examples

This file demonstrates how to use the SAGE machine unlearning algorithms.

Layer: L3 (Core - Algorithm Library)
"""


def example_basic_unlearning():
    """
    Example 1: Basic unlearning workflow

    Demonstrates the basic workflow of using machine unlearning
    algorithms to remove specific data from trained models.
    """
    print("=" * 60)
    print("Example 1: Basic Unlearning Workflow")
    print("=" * 60)

    try:
        from sage.libs.unlearning.algorithms import GaussianMechanism  # noqa: F401

        print("\n✓ Machine Unlearning Overview:")
        print("  1. Train initial model on full dataset")
        print("  2. Identify data to forget")
        print("  3. Apply unlearning algorithm")
        print("  4. Verify data removal")

        print("\nExample workflow:")
        print(
            """
        from sage.libs.unlearning.algorithms import GaussianMechanism
        from sage.libs.unlearning.dp_unlearning import UnlearningEngine

        # Initialize DP mechanism
        mechanism = GaussianMechanism(
            epsilon=1.0,
            delta=1e-5,
            sensitivity=0.1
        )

        # Initialize unlearning engine
        engine = UnlearningEngine(mechanism=mechanism)

        # Specify data to forget
        forget_indices = [10, 25, 42, 100]

        # Apply unlearning
        updated_params = engine.unlearn(
            model_parameters=current_params,
            forget_indices=forget_indices,
            retain_data=remaining_data
        )

        # Verify unlearning
        print(f"Model updated: {updated_params is not None}")
        """
        )

    except ImportError as e:
        print(f"✗ Import error: {e}")


def example_differential_privacy():
    """
    Example 2: Differential privacy mechanisms

    Demonstrates how to use differential privacy techniques
    in conjunction with machine unlearning.
    """
    print("\n" + "=" * 60)
    print("Example 2: Differential Privacy Unlearning")
    print("=" * 60)

    try:
        from sage.libs.unlearning.dp_unlearning import (  # noqa: F401
            NeighborCompensation,
            VectorPerturbation,
        )

        print("\n✓ DP-based unlearning components:")
        print("  - Vector Perturbation: Add calibrated noise")
        print("  - Neighbor Compensation: Compensate neighboring records")
        print("  - Privacy Accountant: Track privacy budget")

        print("\nExample: Vector perturbation")
        print(
            """
        from sage.libs.unlearning.dp_unlearning import VectorPerturbation
        from sage.libs.unlearning.algorithms import GaussianMechanism

        # Create DP mechanism
        mechanism = GaussianMechanism(
            epsilon=1.0,
            delta=1e-5,
            sensitivity=0.1
        )

        # Create vector perturbation component
        perturbation = VectorPerturbation(mechanism=mechanism)

        # Apply DP unlearning
        perturbed_params = perturbation.perturb(
            model_parameters=params,
            forget_gradient=forget_grad
        )
        """
        )

        print("\nExample: Privacy accounting")
        print(
            """
        from sage.libs.unlearning.dp_unlearning import PrivacyAccountant

        # Track privacy budget across multiple unlearning operations
        accountant = PrivacyAccountant(total_epsilon=3.0)

        # First unlearning operation
        accountant.spend(epsilon=1.0, delta=1e-5)

        # Check remaining budget
        remaining = accountant.get_remaining_budget()
        print(f"Remaining privacy budget: {remaining}")
        """
        )

    except ImportError as e:
        print(f"✗ Import error: {e}")


def example_evaluation_metrics():
    """
    Example 3: Evaluating unlearning effectiveness

    Demonstrates how to evaluate the effectiveness and quality
    of machine unlearning algorithms.
    """
    print("\n" + "=" * 60)
    print("Example 3: Unlearning Evaluation Metrics")
    print("=" * 60)

    try:
        from sage.libs.unlearning.evaluation import UnlearningMetrics  # noqa: F401

        print("\n✓ Evaluation metrics:")
        print("  - Forgetting accuracy: How well data is forgotten")
        print("  - Retention accuracy: Performance on remaining data")
        print("  - Unlearning time: Computational efficiency")
        print("  - Model utility: Overall model performance")

        print("\nExample evaluation:")
        print(
            """
        from sage.libs.unlearning.evaluation import UnlearningMetrics

        # Create metrics evaluator
        metrics = UnlearningMetrics(
            original_model=original_model,
            unlearned_model=unlearned_model,
            retrained_model=retrained_model  # Gold standard
        )

        # Evaluate forgetting quality
        forget_score = metrics.forgetting_quality(
            forget_set=forget_data
        )

        # Evaluate retention
        retain_score = metrics.retention_quality(
            retain_set=retain_data
        )

        # Compare with retraining
        similarity = metrics.model_similarity()

        print(f"Forgetting score: {forget_score:.4f}")
        print(f"Retention score: {retain_score:.4f}")
        print(f"Similarity to retrained model: {similarity:.4f}")
        """
        )

    except ImportError as e:
        print(f"✗ Import error: {e}")


def example_unlearning_algorithms():
    """
    Example 4: Different unlearning algorithms

    Demonstrates various unlearning algorithms available in SAGE.
    """
    print("\n" + "=" * 60)
    print("Example 4: Unlearning Algorithm Comparison")
    print("=" * 60)

    print("\n✓ Available algorithms:")
    print("  - Gaussian Mechanism: Gaussian noise-based (ε,δ)-DP")
    print("  - Laplace Mechanism: Laplace noise-based ε-DP")
    print("  - Unlearning Engine: Orchestrates unlearning process")

    print("\nExample: Gaussian vs Laplace mechanisms")
    print(
        """
    from sage.libs.unlearning.algorithms import (
        GaussianMechanism,
        LaplaceMechanism
    )
    from sage.libs.unlearning.dp_unlearning import UnlearningEngine

    # Gaussian mechanism (better for larger datasets, requires δ)
    gaussian = GaussianMechanism(
        epsilon=1.0,
        delta=1e-5,
        sensitivity=0.1
    )

    # Laplace mechanism (pure ε-DP, no δ required)
    laplace = LaplaceMechanism(
        epsilon=0.5,
        sensitivity=0.1
    )

    # Create engines with different mechanisms
    gaussian_engine = UnlearningEngine(mechanism=gaussian)
    laplace_engine = UnlearningEngine(mechanism=laplace)

    # Compare results
    gaussian_params = gaussian_engine.unlearn(forget_indices)
    laplace_params = laplace_engine.unlearn(forget_indices)
    """
    )

    print("\nExample: Advanced usage with neighbor compensation")
    print(
        """
    from sage.libs.unlearning.dp_unlearning import (
        UnlearningEngine,
        NeighborCompensation
    )
    from sage.libs.unlearning.algorithms import GaussianMechanism

    # Create mechanism
    mechanism = GaussianMechanism(epsilon=1.0, delta=1e-5)

    # Create neighbor compensation
    neighbor_comp = NeighborCompensation(
        mechanism=mechanism,
        num_neighbors=5
    )

    # Apply compensated unlearning
    updated_params = neighbor_comp.compensate(
        model_params=params,
        forget_indices=forget_indices,
        training_data=data
    )
    """
    )


def example_real_world_scenario():
    """
    Example 5: Real-world GDPR compliance scenario

    Demonstrates a complete workflow for handling data deletion
    requests in compliance with privacy regulations.
    """
    print("\n" + "=" * 60)
    print("Example 5: GDPR Compliance Workflow")
    print("=" * 60)

    print("\n✓ GDPR 'Right to be Forgotten' workflow:")
    print("  1. Receive deletion request")
    print("  2. Identify user data in model")
    print("  3. Apply certified unlearning")
    print("  4. Verify deletion")
    print("  5. Document compliance")

    print("\nComplete example:")
    print(
        """
    from sage.libs.unlearning.algorithms import GaussianMechanism
    from sage.libs.unlearning.evaluation import UnlearningMetrics
    from sage.libs.unlearning.dp_unlearning import (
        PrivacyAccountant,
        UnlearningEngine
    )

    # Step 1: Receive deletion request
    user_id = "user_12345"
    user_data_indices = identify_user_data(user_id)

    # Step 2: Apply certified unlearning
    accountant = PrivacyAccountant(total_epsilon=1.0)
    
    mechanism = GaussianMechanism(
        epsilon=0.5,
        delta=1e-5,
        sensitivity=0.1
    )
    
    engine = UnlearningEngine(mechanism=mechanism)

    updated_params = engine.unlearn(
        model_parameters=production_model.parameters,
        forget_indices=user_data_indices
    )

    # Step 3: Verify deletion
    metrics = UnlearningMetrics(
        original_model=production_model,
        unlearned_model=updated_model
    )

    # Check that user data cannot be recovered
    forgetting_score = metrics.forgetting_quality(user_data_indices)
    assert forgetting_score > 0.95, "Insufficient forgetting"

    # Check model still performs well
    retain_score = metrics.retention_quality(remaining_data)
    assert retain_score > 0.90, "Too much utility loss"

    # Step 4: Document compliance
    compliance_report = {
        "user_id": user_id,
        "deletion_date": datetime.now(),
        "forgetting_score": forgetting_score,
        "retention_score": retain_score,
        "privacy_spent": accountant.get_spent_budget(),
        "certified": True
    }

    log_compliance(compliance_report)
    print("✓ GDPR deletion request processed successfully")
    """
    )


def run_all_examples():
    """Run all examples in sequence."""
    print("\n" + "=" * 60)
    print("SAGE Unlearning - Complete Examples")
    print("=" * 60)

    example_basic_unlearning()
    example_differential_privacy()
    example_evaluation_metrics()
    example_unlearning_algorithms()
    example_real_world_scenario()

    print("\n" + "=" * 60)
    print("✓ All examples completed")
    print("=" * 60)
    print("\nFor more information:")
    print("- See packages/sage-libs/src/sage/libs/unlearning/README.md")
    print("- Check algorithms/ for mechanism implementations")
    print("- Visit docs/ for research papers and references")
    print("\nKey papers:")
    print("- Machine Unlearning (Cao & Yang, 2015)")
    print("- Certified Data Removal (Guo et al., 2020)")
    print("- The Algorithmic Foundations of DP (Dwork & Roth, 2014)")


if __name__ == "__main__":
    run_all_examples()
