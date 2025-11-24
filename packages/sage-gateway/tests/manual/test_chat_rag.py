#!/usr/bin/env python3
"""
测试 Chat RAG 功能

模拟 Gateway 中的 RAG 流程，快速定位问题
"""

import os
import sys
from pathlib import Path


def test_rag_pipeline():
    """测试完整的 RAG Pipeline"""

    print("=" * 70)
    print("测试 Chat RAG 功能")
    print("=" * 70)

    # 1. 测试导入
    print("\n[步骤 1] 测试模块导入...")
    try:
        from sage.middleware.operators.rag.retriever import ChromaRetriever
        from sage.middleware.operators.rag.promptor import QAPromptor
        from sage.middleware.operators.rag.generator import OpenAIGenerator

        print("  ✅ 所有模块导入成功")
    except Exception as e:
        print(f"  ❌ 导入失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    # 2. 测试 ChromaRetriever 配置
    print("\n[步骤 2] 测试 ChromaRetriever 配置...")

    # Gateway 中使用的配置（正确格式）
    retriever_config = {
        "chroma": {
            "persist_directory": str(Path.home() / ".sage" / "vector_db"),
            "persistence_path": str(Path.home() / ".sage" / "vector_db"),
            "collection_name": "sage_docs",
        },
        "top_k": 5,
        "embedding": {
            "model_name": "BAAI/bge-small-zh-v1.5",
        },
    }

    print(f"  配置: {retriever_config}")

    try:
        retriever = ChromaRetriever(retriever_config)
        print("  ✅ ChromaRetriever 初始化成功")
    except Exception as e:
        print(f"  ❌ ChromaRetriever 初始化失败: {e}")
        import traceback

        traceback.print_exc()

        # 尝试诊断问题
        print("\n[诊断] 检查配置要求...")
        from sage.libs.integrations.chroma import ChromaUtils

        chroma_config = retriever_config.get("chroma", {})
        is_valid = ChromaUtils.validate_chroma_config(chroma_config)
        print(f"  Chroma 配置验证结果: {is_valid}")
        print(f"  Chroma 配置内容: {chroma_config}")

        if not is_valid:
            print("  问题: 配置缺少必需字段")
            print("  解决: 检查 ChromaUtils.validate_chroma_config() 的要求")

        return False

    # 3. 测试检索
    print("\n[步骤 3] 测试检索功能...")
    test_query = "什么是SAGE"

    try:
        result = retriever.execute(test_query)
        print("  ✅ 检索成功")
        print(f"  查询: {test_query}")
        print(f"  结果类型: {type(result)}")
        if isinstance(result, dict):
            print(f"  结果键: {list(result.keys())}")
            if "retrieval_results" in result:
                print(f"  检索到文档数: {len(result['retrieval_results'])}")
    except Exception as e:
        print(f"  ❌ 检索失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    # 4. 测试 Promptor
    print("\n[步骤 4] 测试 Promptor...")

    promptor_config = {
        "template": "根据以下文档回答问题：\n\n{{external_corpus}}\n\n问题：{{query}}\n\n回答："
    }

    try:
        promptor = QAPromptor(promptor_config)
        prompt_result = promptor.execute(result)
        print("  ✅ Promptor 执行成功")
        print(f"  Prompt 类型: {type(prompt_result)}")
        if isinstance(prompt_result, dict) and "prompt" in prompt_result:
            prompt_text = prompt_result["prompt"]
            print(f"  Prompt 长度: {len(prompt_text)} 字符")
            print(f"  Prompt 预览: {prompt_text[:200]}...")
    except Exception as e:
        print(f"  ❌ Promptor 失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    # 5. 测试 Generator（需要 API Key）
    print("\n[步骤 5] 测试 Generator...")

    api_key = (
        os.getenv("SAGE_CHAT_API_KEY")
        or os.getenv("ALIBABA_API_KEY")
        or os.getenv("DASHSCOPE_API_KEY")
    )

    if not api_key:
        print("  ⚠️  跳过 Generator 测试（缺少 API Key）")
        print("  提示: 设置 DASHSCOPE_API_KEY 环境变量以测试生成功能")
    else:
        generator_config = {
            "model_name": os.getenv("SAGE_CHAT_MODEL", "qwen-max"),
            "base_url": os.getenv(
                "SAGE_CHAT_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
            "api_key": api_key,
            "seed": 42,
        }

        try:
            generator = OpenAIGenerator(generator_config)
            final_result = generator.execute(prompt_result)
            print("  ✅ Generator 执行成功")
            print(f"  结果类型: {type(final_result)}")

            if isinstance(final_result, dict) and "generated" in final_result:
                answer = final_result["generated"]
                print(f"  生成回答长度: {len(answer)} 字符")
                print(f"  回答预览: {answer[:200]}...")
            elif isinstance(final_result, str):
                print(f"  生成回答: {final_result[:200]}...")
        except Exception as e:
            print(f"  ❌ Generator 失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    print("\n" + "=" * 70)
    print("✅ RAG Pipeline 测试完成！")
    print("=" * 70)

    return True


if __name__ == "__main__":
    success = test_rag_pipeline()
    sys.exit(0 if success else 1)
