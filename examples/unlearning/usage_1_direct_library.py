"""
Usage 1: Direct Library Usage
==============================

最简单的方式：直接使用 unlearning 库，无需 SAGE 运行时。

适用场景：
- 独立脚本
- Jupyter Notebook 实验
- 快速原型验证
- 研究算法开发

优势：
- 零依赖 SAGE 运行时
- 代码简洁清晰
- 易于调试
- 适合快速实验
"""

import numpy as np
from sage.libs.unlearning import UnlearningEngine
from sage.libs.unlearning.algorithms import LaplaceMechanism


def generate_test_data(n_vectors=50, dim=128):
    """生成测试数据"""
    vectors = np.random.randn(n_vectors, dim).astype(np.float32)
    # L2 归一化（模拟真实 embeddings）
    vectors = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-10)
    ids = [f"doc_{i}" for i in range(n_vectors)]
    return vectors, ids


def example_basic_unlearning():
    """示例1：基础遗忘操作"""
    print("=" * 70)
    print("Example 1: Basic Unlearning")
    print("=" * 70)

    # 1. 生成数据
    all_vectors, all_ids = generate_test_data(n_vectors=50, dim=128)
    print(f"✓ Generated {len(all_vectors)} vectors")

    # 2. 选择要遗忘的向量
    forget_indices = [5, 10, 15, 20, 25]
    vectors_to_forget = all_vectors[forget_indices]
    ids_to_forget = [all_ids[i] for i in forget_indices]
    print(f"✓ Selected {len(ids_to_forget)} vectors to forget: {ids_to_forget}")

    # 3. 创建 unlearning engine
    engine = UnlearningEngine(
        epsilon=1.0, delta=1e-5, total_budget_epsilon=10.0, enable_compensation=True
    )
    print("✓ Created UnlearningEngine")

    # 4. 执行遗忘
    result = engine.unlearn_vectors(
        vectors_to_forget=vectors_to_forget,
        vector_ids_to_forget=ids_to_forget,
        all_vectors=all_vectors,
        all_vector_ids=all_ids,
        perturbation_strategy="uniform",
    )

    # 5. 查看结果
    print(f"\n🎯 Unlearning Result:")
    print(f"  Success: {result.success}")
    print(f"  Vectors unlearned: {result.num_vectors_unlearned}")
    print(f"  Neighbors compensated: {result.num_neighbors_compensated}")
    print(
        f"  Privacy cost: ε={result.privacy_cost[0]:.4f}, δ={result.privacy_cost[1]:.6f}"
    )

    # 6. 获取扰动后的向量
    perturbed = result.metadata["perturbed_vectors"]
    print(f"\n📊 Vector Comparison:")
    for i, (orig, pert, vec_id) in enumerate(
        zip(vectors_to_forget, perturbed, ids_to_forget)
    ):
        l2_dist = np.linalg.norm(orig - pert)
        cos_sim = np.dot(orig, pert) / (np.linalg.norm(orig) * np.linalg.norm(pert))
        print(f"  {vec_id}: L2={l2_dist:.4f}, CosSim={cos_sim:.4f}")

    print()


def example_custom_mechanism():
    """示例2：使用自定义隐私机制"""
    print("=" * 70)
    print("Example 2: Custom Privacy Mechanism")
    print("=" * 70)

    # 1. 生成数据
    vectors, ids = generate_test_data(n_vectors=30, dim=64)
    forget_vectors = vectors[:3]
    forget_ids = ids[:3]

    # 2. 创建自定义 Laplace 机制
    custom_mechanism = LaplaceMechanism(epsilon=0.5)
    print(f"✓ Created custom Laplace mechanism with ε=0.5")

    # 3. 使用自定义机制
    engine = UnlearningEngine(
        mechanism=custom_mechanism,
        total_budget_epsilon=5.0,
        enable_compensation=False,  # 不使用补偿
    )

    result = engine.unlearn_vectors(
        vectors_to_forget=forget_vectors,
        vector_ids_to_forget=forget_ids,
        perturbation_strategy="selective",
    )

    print(f"\n🎯 Result with custom mechanism:")
    print(f"  Success: {result.success}")
    print(f"  Privacy cost: ε={result.privacy_cost[0]:.4f}")
    print()


def example_batch_unlearning():
    """示例3：批量遗忘操作"""
    print("=" * 70)
    print("Example 3: Batch Unlearning")
    print("=" * 70)

    # 1. 生成数据
    all_vectors, all_ids = generate_test_data(n_vectors=100, dim=128)

    # 2. 创建 engine
    engine = UnlearningEngine(
        epsilon=0.5, delta=1e-5, total_budget_epsilon=20.0, enable_compensation=True
    )

    # 3. 分批遗忘
    batch_size = 5
    total_forgotten = 0

    for batch_idx in range(3):  # 遗忘3批
        start_idx = batch_idx * batch_size
        end_idx = start_idx + batch_size

        forget_vectors = all_vectors[start_idx:end_idx]
        forget_ids = all_ids[start_idx:end_idx]

        result = engine.unlearn_vectors(
            vectors_to_forget=forget_vectors,
            vector_ids_to_forget=forget_ids,
            all_vectors=all_vectors,
            all_vector_ids=all_ids,
            perturbation_strategy="uniform",
        )

        total_forgotten += result.num_vectors_unlearned
        print(
            f"  Batch {batch_idx + 1}: Forgotten {result.num_vectors_unlearned} vectors, "
            f"Privacy cost: ε={result.privacy_cost[0]:.4f}"
        )

    # 4. 检查剩余预算
    status = engine.get_privacy_status()
    remaining = status["remaining_budget"]

    print(f"\n📊 Summary:")
    print(f"  Total forgotten: {total_forgotten} vectors")
    print(f"  Remaining budget: ε={remaining['epsilon_remaining']:.4f}")
    print(
        f"  Budget utilization: {status['accountant_summary']['budget_utilization']:.1%}"
    )
    print()


def example_similarity_based_unlearning():
    """示例4：基于相似度的遗忘"""
    print("=" * 70)
    print("Example 4: Similarity-based Unlearning")
    print("=" * 70)

    # 1. 生成数据
    all_vectors, all_ids = generate_test_data(n_vectors=80, dim=128)

    # 2. 创建一个查询向量（要遗忘的主题）
    query_vector = np.random.randn(128).astype(np.float32)
    query_vector = query_vector / np.linalg.norm(query_vector)
    print("✓ Created query vector representing topic to forget")

    # 3. 创建 engine
    engine = UnlearningEngine(epsilon=1.0, delta=1e-5)

    # 4. 遗忘所有相似的向量
    result = engine.unlearn_by_similarity(
        query_vector=query_vector,
        all_vectors=all_vectors,
        all_vector_ids=all_ids,
        similarity_threshold=0.3,  # 相似度 > 0.3 的都遗忘
        max_unlearn=10,  # 最多遗忘10个
        perturbation_strategy="adaptive",
    )

    print(f"\n🎯 Similarity-based Unlearning Result:")
    print(f"  Success: {result.success}")
    print(f"  Vectors forgotten: {result.num_vectors_unlearned}")
    print(f"  Privacy cost: ε={result.privacy_cost[0]:.4f}")

    if result.num_vectors_unlearned > 0:
        forgotten_ids = result.metadata.get("perturbed_vectors", [])
        print(f"  Forgotten vector IDs: {result.metadata.get('message', 'N/A')}")

    print()


def example_privacy_budget_management():
    """示例5：隐私预算管理"""
    print("=" * 70)
    print("Example 5: Privacy Budget Management")
    print("=" * 70)

    # 创建 engine 带有较小的总预算
    engine = UnlearningEngine(
        epsilon=2.0,
        delta=1e-5,
        total_budget_epsilon=5.0,  # 小预算
        enable_compensation=False,
    )

    vectors, ids = generate_test_data(n_vectors=50, dim=64)

    print("📊 Privacy Budget Tracking:")
    print(f"  Initial budget: ε={engine.privacy_accountant.total_epsilon_budget}")

    # 尝试多次操作直到预算耗尽
    operation_count = 0
    while True:
        forget_idx = operation_count % len(vectors)
        result = engine.unlearn_vectors(
            vectors_to_forget=vectors[forget_idx : forget_idx + 1],
            vector_ids_to_forget=[ids[forget_idx]],
            perturbation_strategy="uniform",
        )

        operation_count += 1

        if not result.success:
            print(
                f"\n❌ Operation {operation_count} failed: {result.metadata.get('error')}"
            )
            print(f"  Remaining budget: {result.metadata.get('remaining_budget')}")
            break
        else:
            status = engine.get_privacy_status()
            remaining = status["remaining_budget"]
            print(
                f"  Operation {operation_count}: Success, "
                f"Remaining ε={remaining['epsilon_remaining']:.4f}"
            )

    print()


def main():
    """运行所有示例"""
    print("\n" + "=" * 70)
    print("SAGE Unlearning Library - Direct Usage Examples")
    print("=" * 70)
    print("\n这些示例展示了如何直接使用 unlearning 库，无需 SAGE 运行时。")
    print("适合：独立脚本、Jupyter 实验、快速原型验证\n")

    # 运行所有示例
    example_basic_unlearning()
    example_custom_mechanism()
    example_batch_unlearning()
    example_similarity_based_unlearning()
    example_privacy_budget_management()

    print("=" * 70)
    print("✅ All examples completed successfully!")
    print("=" * 70)
    print("\n💡 Next steps:")
    print("  1. Try modifying the parameters (epsilon, delta, strategies)")
    print("  2. Implement your own privacy mechanism")
    print("  3. Test on real embeddings from your RAG system")
    print("  4. See usage_2_sage_function.py for SAGE integration\n")


if __name__ == "__main__":
    main()
