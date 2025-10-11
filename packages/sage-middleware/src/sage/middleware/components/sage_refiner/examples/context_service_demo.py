"""
Context Service使用示例
====================

演示如何使用全局Context Service管理应用上下文。
"""

from sage.middleware.components.sage_refiner.python.context_service import (
    ContextService,
)


def basic_context_service():
    """基础Context Service使用"""
    print("=" * 60)
    print("基础Context Service示例")
    print("=" * 60)

    # 1. 创建配置
    config = {
        "refiner": {"algorithm": "simple", "budget": 2000, "enable_cache": True},
        "max_context_length": 8192,
        "auto_compress": True,
        "compress_threshold": 0.8,
    }

    # 2. 创建服务
    service = ContextService.from_config(config)

    # 3. 准备数据
    query = "如何使用Python进行数据分析？"

    history = [
        {"role": "user", "content": "什么是Python？"},
        {"role": "assistant", "content": "Python是一种高级编程语言..."},
        {"role": "user", "content": "Python有什么优势？"},
        {"role": "assistant", "content": "Python简洁、易读、生态丰富..."},
    ]

    retrieved_docs = [
        "NumPy是Python中用于科学计算的基础包，提供多维数组对象。",
        "Pandas是建立在NumPy之上的数据分析库，提供DataFrame等数据结构。",
        "Matplotlib是Python的绘图库，用于创建静态、动态和交互式可视化。",
        "Scikit-learn是机器学习库，提供各种分类、回归和聚类算法。",
        "Jupyter Notebook是一个交互式计算环境，适合数据分析和可视化。",
    ]

    system_prompt = "你是一个专业的Python数据分析助手。"

    # 4. 管理上下文
    result = service.manage_context(
        query=query,
        history=history,
        retrieved_docs=retrieved_docs,
        system_prompt=system_prompt,
    )

    # 5. 查看结果
    print(f"\n上下文长度: {result['context_length']} tokens")
    print(f"应用压缩: {result['compression_applied']}")

    print("\n上下文组成:")
    for part in result["compressed_context"]:
        content_preview = part["content"][:100].replace("\n", " ")
        print(f"  - {part['type']}: {content_preview}...")

    if result["metrics"]:
        print("\n压缩指标:")
        for key, value in result["metrics"].items():
            print(f"  {key}: {value}")

    # 6. 清理
    service.shutdown()
    print("\n✓ 完成\n")


def conversation_with_context_service():
    """模拟多轮对话的上下文管理"""
    print("=" * 60)
    print("多轮对话上下文管理")
    print("=" * 60)

    config = {
        "refiner": {"algorithm": "simple", "budget": 1000},
        "max_context_length": 4096,
        "auto_compress": True,
    }

    with ContextService.from_config(config) as service:
        # 模拟3轮对话
        conversations = [
            {
                "query": "什么是机器学习？",
                "docs": ["机器学习是AI的一个分支，使计算机能从数据中学习。"],
                "response": "机器学习是人工智能的核心技术...",
            },
            {
                "query": "监督学习和无监督学习有什么区别？",
                "docs": ["监督学习使用标记数据训练。", "无监督学习寻找数据中的模式。"],
                "response": "监督学习需要标记数据，而无监督学习不需要...",
            },
            {
                "query": "能举个监督学习的例子吗？",
                "docs": [
                    "图像分类是典型的监督学习任务。",
                    "垃圾邮件检测也是监督学习。",
                ],
                "response": "比如图像分类，我们用标记好的图片训练模型...",
            },
        ]

        for i, conv in enumerate(conversations, 1):
            print(f"\n--- 第 {i} 轮对话 ---")
            print(f"用户: {conv['query']}")

            # 管理上下文
            context = service.manage_context(
                query=conv["query"],
                history=service.context_history,
                retrieved_docs=conv["docs"],
            )

            print(f"上下文长度: {context['context_length']} tokens")

            # 添加到历史
            service.add_to_history("user", conv["query"])
            service.add_to_history("assistant", conv["response"])

            print(f"助手: {conv['response']}")

        # 查看最终统计
        print("\n最终统计:")
        stats = service.get_stats()
        print(f"  历史记录数: {stats['context_history_size']}")
        print(f"  Refiner请求数: {stats['refiner_stats']['total_requests']}")

    print("\n✓ 完成\n")


def application_with_flag():
    """应用级别的flag控制示例"""
    print("=" * 60)
    print("应用级别Flag控制")
    print("=" * 60)

    # 应用配置 - 只需一个flag即可开关
    app_config = {
        "enable_context_service": True,  # ← 关键flag
        "context_service": {
            "refiner": {"algorithm": "simple", "budget": 2000},
            "max_context_length": 8192,
            "auto_compress": True,
        },
        # ... 其他应用配置
    }

    print("配置:")
    import json

    print(json.dumps(app_config, indent=2))

    # 初始化应用
    if app_config["enable_context_service"]:
        print("\n✓ Context Service已启用")
        service = ContextService.from_config(app_config["context_service"])

        # 模拟处理
        result = service.manage_context(
            query="测试查询",
            retrieved_docs=["文档1", "文档2"],
        )

        print(f"  上下文管理成功，长度: {result['context_length']} tokens")
        service.shutdown()
    else:
        print("\n✗ Context Service已禁用")
        print("  直接使用原始上下文，不进行压缩")

    print("\n✓ 完成\n")


if __name__ == "__main__":
    basic_context_service()
    conversation_with_context_service()
    application_with_flag()

    print("=" * 60)
    print("Context Service示例完成!")
    print("=" * 60)
