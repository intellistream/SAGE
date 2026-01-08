"""  
UnifiedInferenceClient 完整使用示例

本示例演示如何使用 SAGE 统一推理客户端进行 LLM 对话和 Embedding 向量化。

Requirements:
    pip install isage-llm-core>=0.2.0

Prerequisites:
    1. 启动 Gateway: `sage gateway start`
    2. 启动 LLM 引擎: `sage llm engine start Qwen/Qwen2.5-0.5B-Instruct`
    3. 启动 Embedding 引擎: `sage llm engine start BAAI/bge-m3 --engine-kind embedding`

Test Configuration:
    @test_category: tutorials
    @test_speed: quick
    @test_skip_ci: true
    @test:skip - Requires Gateway and engines to be running
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

from sage.common.config.ports import SagePorts
from sage.llm import UnifiedInferenceClient

if TYPE_CHECKING:
    pass

# Check test mode
_IS_TEST_MODE = (
    os.getenv("SAGE_TEST_MODE") == "true"
    or os.getenv("SAGE_EXAMPLES_MODE") == "test"
    or os.getenv("CI") == "true"
)


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """计算两个向量的余弦相似度."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    return dot / (norm1 * norm2) if norm1 * norm2 > 0 else 0


def example_basic_chat():
    """示例 1: 基础对话"""
    print("=" * 60)
    print("示例 1: 基础对话")
    print("=" * 60)

    if _IS_TEST_MODE:
        print("\n[Test mode] Would connect to Gateway:")
        print(f"  URL: http://localhost:{SagePorts.GATEWAY_DEFAULT}/v1")
        print("  Skipping actual connection")
        return

    # 创建客户端 - 连接到 Gateway Control Plane
    client = UnifiedInferenceClient.create(
        control_plane_url=f"http://localhost:{SagePorts.GATEWAY_DEFAULT}/v1"
    )

    # 单轮对话
    messages = [{"role": "user", "content": "用一句话介绍什么是人工智能"}]
    response = client.chat(messages)

    print(f"\n用户: {messages[0]['content']}")
    print(f"助手: {response}")


def example_multi_turn_conversation():
    """示例 2: 多轮对话"""
    print("\n" + "=" * 60)
    print("示例 2: 多轮对话")
    print("=" * 60)

    if _IS_TEST_MODE:
        print("\n[Test mode] Multi-turn conversation demo")
        print("  Would send multiple messages to LLM")
        print("  Skipping actual connection")
        return

    client = UnifiedInferenceClient.create(
        control_plane_url=f"http://localhost:{SagePorts.GATEWAY_DEFAULT}/v1"
    )

    # 构建多轮对话历史
    messages = [
        {"role": "user", "content": "什么是机器学习?"},
    ]

    response1 = cast(str, client.chat(messages))
    print(f"\n用户: {messages[0]['content']}")
    print(f"助手: {response1}")

    # 添加助手回复和新的用户问题
    messages.append({"role": "assistant", "content": response1})
    messages.append({"role": "user", "content": "它和深度学习有什么区别?"})

    response2 = client.chat(messages)
    print(f"\n用户: {messages[-1]['content']}")
    print(f"助手: {response2}")


def example_embedding():
    """示例 3: 文本向量化"""
    print("\n" + "=" * 60)
    print("示例 3: 文本向量化 (Embedding)")
    print("=" * 60)

    if _IS_TEST_MODE:
        print("\n[Test mode] Embedding demo")
        print("  Would generate embeddings for sample texts")
        print("  Skipping actual connection")
        return

    client = UnifiedInferenceClient.create(
        control_plane_url=f"http://localhost:{SagePorts.GATEWAY_DEFAULT}/v1"
    )

    # 批量向量化
    texts = [
        "人工智能是计算机科学的一个分支",
        "机器学习是人工智能的子集",
        "深度学习使用多层神经网络",
    ]

    vectors = cast(list[list[float]], client.embed(texts))

    print(f"\n处理了 {len(texts)} 个文本:")
    for i, (text, vec) in enumerate(zip(texts, vectors), 1):
        print(f"  {i}. '{text[:30]}...' -> 向量维度: {len(vec)}")

    print("\n文本相似度:")
    sim_01 = _cosine_similarity(vectors[0], vectors[1])
    sim_02 = _cosine_similarity(vectors[0], vectors[2])
    sim_12 = _cosine_similarity(vectors[1], vectors[2])
    print(f"  文本1 vs 文本2: {sim_01:.4f}")
    print(f"  文本1 vs 文本3: {sim_02:.4f}")
    print(f"  文本2 vs 文本3: {sim_12:.4f}")


def example_combined_workflow():
    """示例 4: 综合工作流 (Chat + Embedding)"""
    print("\n" + "=" * 60)
    print("示例 4: 综合工作流 (RAG 简化示例)")
    print("=" * 60)

    if _IS_TEST_MODE:
        print("\n[Test mode] Combined workflow demo")
        print("  Would demonstrate RAG-like pipeline")
        print("  Skipping actual connection")
        return

    client = UnifiedInferenceClient.create(
        control_plane_url=f"http://localhost:{SagePorts.GATEWAY_DEFAULT}/v1"
    )

    # 模拟知识库
    knowledge_base = [
        "SAGE 是一个用于构建 AI/LLM 数据处理管道的 Python 框架",
        "SAGE 支持声明式数据流定义",
        "SAGE Gateway 提供统一的 API 入口和 Control Plane 引擎管理",
        "UnifiedInferenceClient 是 SAGE 的统一推理客户端",
    ]

    # 用户问题
    query = "什么是 SAGE Gateway?"
    print(f"\n用户问题: {query}")

    # Step 1: 向量化问题和知识库
    print("\nStep 1: 向量化...")
    query_vector = cast(list[list[float]], client.embed([query]))[0]
    kb_vectors = cast(list[list[float]], client.embed(knowledge_base))

    # Step 2: 检索最相关文档
    similarities = [_cosine_similarity(query_vector, kv) for kv in kb_vectors]
    best_idx = similarities.index(max(similarities))
    context = knowledge_base[best_idx]
    print(f"Step 2: 检索到相关文档: '{context}'")

    # Step 3: 生成回答
    print("Step 3: 生成回答...")
    messages = [
        {
            "role": "system",
            "content": f"根据以下上下文回答用户问题。\n\n上下文: {context}",
        },
        {"role": "user", "content": query},
    ]
    response = client.chat(messages)
    print(f"\n最终回答: {response}")


def example_auto_detection():
    """示例 5: 自动检测模式"""
    print("\n" + "=" * 60)
    print("示例 5: 自动检测模式")
    print("=" * 60)

    if _IS_TEST_MODE:
        print("\n[Test mode] Auto-detection demo")
        print("  Would try to auto-detect services")
        print("  Skipping actual connection")
        return

    # 自动检测可用服务
    # 会依次尝试: Control Plane (8000) -> 本地服务 (8901/8090) -> 云端 API
    client = UnifiedInferenceClient.create()

    print("\n自动检测到的服务配置:")
    print(f"  LLM available: {client._llm_available}")
    print(f"  Embedding available: {client._embedding_available}")

    # 使用自动检测的服务
    response = cast(str, client.chat([{"role": "user", "content": "Hello"}]))
    print(f"\n测试响应: {response[:100]}...")


def example_error_handling():
    """示例 6: 错误处理"""
    print("\n" + "=" * 60)
    print("示例 6: 错误处理")
    print("=" * 60)

    if _IS_TEST_MODE:
        print("\n[Test mode] Error handling demo")
        print("  Would demonstrate exception handling")
        return

    try:
        # 尝试连接不存在的服务
        client = UnifiedInferenceClient.create(control_plane_url="http://localhost:9999/v1")
        client.chat([{"role": "user", "content": "test"}])
    except ConnectionError as e:
        print(f"\n捕获到连接错误: {e}")
        print("提示: 请确保 Gateway 已启动 (sage gateway start)")
    except Exception as e:
        print(f"\n捕获到错误: {type(e).__name__}: {e}")


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("SAGE UnifiedInferenceClient 完整示例")
    print("=" * 60)

    if _IS_TEST_MODE:
        print("\n[Test Mode] 运行模式检测")
        print("  SAGE_TEST_MODE:", os.getenv("SAGE_TEST_MODE"))
        print("  SAGE_EXAMPLES_MODE:", os.getenv("SAGE_EXAMPLES_MODE"))
        print("  CI:", os.getenv("CI"))
        print("\n将跳过实际服务连接，仅显示配置信息")
    else:
        print("\n运行前请确保:")
        print("  1. Gateway 已启动: sage gateway start")
        print("  2. LLM 引擎已启动: sage llm engine start Qwen/Qwen2.5-0.5B-Instruct")
        print(
            "  3. Embedding 引擎已启动: sage llm engine start BAAI/bge-m3 --engine-kind embedding"
        )
        print("\n如需跳过连接测试，设置环境变量: SAGE_TEST_MODE=true")

    example_basic_chat()
    example_multi_turn_conversation()
    example_embedding()
    example_combined_workflow()
    example_auto_detection()
    example_error_handling()

    print("\n" + "=" * 60)
    print("所有示例执行完毕")
    print("=" * 60)


if __name__ == "__main__":
    main()
