"""
Workflow Generation Examples

演示如何使用 sage.libs.agentic.workflow.generators 创建工作流
"""


def example_1_rule_based_generation():
    """示例1: 使用规则生成器"""
    print("\n" + "=" * 80)
    print("示例 1: 基于规则的工作流生成")
    print("=" * 80)

    from sage.libs.agentic.workflow import GenerationContext
    from sage.libs.agentic.workflow.generators import RuleBasedWorkflowGenerator

    # 创建生成器
    generator = RuleBasedWorkflowGenerator()

    # 定义生成上下文
    context = GenerationContext(
        user_input="创建一个 RAG 管道用于文档问答",
        domain="rag",
        constraints={"max_cost": 100, "max_latency": 5.0},
    )

    # 生成工作流
    result = generator.generate(context)

    # 查看结果
    if result.success:
        print(f"✓ 生成成功 (置信度: {result.confidence:.2f})")
        print(f"策略: {result.strategy_used.value}")
        print(f"检测到的意图: {result.detected_intents}")
        print(f"生成耗时: {result.generation_time:.2f}s")
        print(f"\n解释:\n{result.explanation}")
        print("\n生成的工作流:")
        print(f"  - 节点数: {len(result.visual_pipeline['nodes'])}")
        print(f"  - 连接数: {len(result.visual_pipeline['connections'])}")
    else:
        print(f"✗ 生成失败: {result.error}")


def example_2_llm_generation():
    """示例2: 使用 LLM 生成器"""
    print("\n" + "=" * 80)
    print("示例 2: 基于 LLM 的工作流生成")
    print("=" * 80)

    from sage.libs.agentic.workflow import GenerationContext
    from sage.libs.agentic.workflow.generators import LLMWorkflowGenerator

    # 创建生成器
    generator = LLMWorkflowGenerator(model="qwen-max", use_rag=True)

    # 定义生成上下文（更复杂的需求）
    context = GenerationContext(
        user_input="我需要一个数据管道，从 PDF 文档中提取信息，使用向量数据库检索相关内容，然后生成结构化的摘要报告",
        conversation_history=[
            {"role": "user", "content": "我有大量的技术文档需要处理"},
            {"role": "assistant", "content": "明白，请详细描述您的需求"},
        ],
        domain="document_processing",
        constraints={"max_latency": 10.0, "min_quality": 0.85},
        preferences={"prefer_local_models": False, "enable_streaming": True},
    )

    # 生成工作流
    result = generator.generate(context)

    # 查看结果
    if result.success:
        print(f"✓ 生成成功 (置信度: {result.confidence:.2f})")
        print(f"策略: {result.strategy_used.value}")
        print(f"检测到的意图: {result.detected_intents}")
        print(f"生成耗时: {result.generation_time:.2f}s")
        print(f"\n解释:\n{result.explanation}")

        if result.suggested_optimizations:
            print("\n建议的优化:")
            for opt in result.suggested_optimizations:
                print(f"  - {opt}")

        print("\n生成的工作流:")
        print(f"  - 名称: {result.visual_pipeline['name']}")
        print(f"  - 节点数: {len(result.visual_pipeline['nodes'])}")

        # 打印节点详情
        print("\n节点列表:")
        for node in result.visual_pipeline["nodes"]:
            node_data = node["data"]
            print(f"  {node['id']}: {node_data['label']} ({node_data['nodeId']})")
    else:
        print(f"✗ 生成失败: {result.error}")


def example_3_comparison():
    """示例3: 比较不同生成策略"""
    print("\n" + "=" * 80)
    print("示例 3: 比较规则生成 vs LLM 生成")
    print("=" * 80)

    from sage.libs.agentic.workflow import GenerationContext
    from sage.libs.agentic.workflow.generators import (
        LLMWorkflowGenerator,
        RuleBasedWorkflowGenerator,
    )

    # 相同的输入
    context = GenerationContext(
        user_input="帮我构建一个数据分析工作流，包括数据清洗、特征提取和可视化",
        constraints={"max_cost": 50},
    )

    # 规则生成
    rule_generator = RuleBasedWorkflowGenerator()
    rule_result = rule_generator.generate(context)

    # LLM 生成
    llm_generator = LLMWorkflowGenerator()
    llm_result = llm_generator.generate(context)

    # 比较结果
    print("\n比较结果:")
    print("\n规则生成器:")
    print(f"  ✓ 成功: {rule_result.success}")
    print(f"  ✓ 置信度: {rule_result.confidence:.2f}")
    print(f"  ✓ 耗时: {rule_result.generation_time:.2f}s")
    if rule_result.success:
        print(f"  ✓ 节点数: {len(rule_result.visual_pipeline['nodes'])}")

    print("\nLLM 生成器:")
    print(f"  ✓ 成功: {llm_result.success}")
    print(f"  ✓ 置信度: {llm_result.confidence:.2f}")
    print(f"  ✓ 耗时: {llm_result.generation_time:.2f}s")
    if llm_result.success:
        print(f"  ✓ 节点数: {len(llm_result.visual_pipeline['nodes'])}")

    print("\n总结:")
    print("  - 规则生成器：快速、可预测，但可能无法理解复杂需求")
    print("  - LLM 生成器：更智能、灵活，但速度较慢且需要 API")


def example_4_with_optimization():
    """示例4: 生成后优化（未来功能演示）"""
    print("\n" + "=" * 80)
    print("示例 4: 工作流生成 + 优化（未来集成）")
    print("=" * 80)

    from sage.libs.agentic.workflow import GenerationContext
    from sage.libs.agentic.workflow.generators import LLMWorkflowGenerator

    # Step 1: 生成初始工作流
    generator = LLMWorkflowGenerator()
    context = GenerationContext(
        user_input="创建一个多步骤的数据处理管道",
        constraints={"max_cost": 100, "max_latency": 10.0, "min_quality": 0.8},
    )

    result = generator.generate(context)

    if result.success:
        print("✓ 初始工作流已生成")
        print(f"  - 节点数: {len(result.visual_pipeline['nodes'])}")

        # Step 2: (未来) 应用优化
        print("\n注意: 工作流优化功能正在开发中")
        print("未来可以:")
        print("  1. 将 visual_pipeline 转换为 WorkflowGraph")
        print("  2. 应用 GreedyOptimizer / ParallelizationOptimizer")
        print("  3. 根据约束优化成本、延迟、质量")
        print("  4. 转回 visual_pipeline 格式")

        if result.suggested_optimizations:
            print("\n当前已有的优化建议:")
            for opt in result.suggested_optimizations:
                print(f"  - {opt}")


if __name__ == "__main__":
    import sys

    print("=" * 80)
    print("SAGE Workflow Generation Examples")
    print("=" * 80)

    try:
        # 运行示例
        example_1_rule_based_generation()
        # example_2_llm_generation()  # 需要 API 密钥
        # example_3_comparison()      # 需要 API 密钥
        example_4_with_optimization()

        print("\n" + "=" * 80)
        print("✓ 示例运行完成")
        print("=" * 80)

    except ImportError as e:
        print(f"\n✗ 导入错误: {e}")
        print("请确保已安装 sage-libs 和 sage-cli")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 运行错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
