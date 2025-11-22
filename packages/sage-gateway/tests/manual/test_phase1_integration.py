#!/usr/bin/env python3
"""
Phase 1 Integration Test

测试 sage-gateway 的基本功能
"""

import subprocess
import sys
import time


def test_gateway_installation():
    """测试 sage-gateway 是否正确安装"""
    print("Testing gateway installation...")
    try:
        import sage.gateway

        print(f"✅ sage-gateway version: {sage.gateway.__version__}")
        return True
    except ImportError:
        print("❌ sage-gateway not installed")
        return False


def test_gateway_server():
    """测试 gateway 服务器启动"""
    print("\nTesting gateway server...")

    # 启动服务器
    process = subprocess.Popen(
        [sys.executable, "-m", "sage.gateway.server"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # 等待启动
    print("  Waiting for server...", end="", flush=True)
    for _ in range(10):
        time.sleep(1)
        try:
            import urllib.request

            urllib.request.urlopen("http://localhost:8000/health", timeout=1)
            print(" ✅")
            break
        except Exception:
            print(".", end="", flush=True)
    else:
        print(" ❌")
        process.kill()
        return False

    # 测试完成，关闭服务器
    process.terminate()
    process.wait(timeout=5)
    return True


def test_session_manager():
    """测试会话管理器"""
    print("\nTesting session manager...")
    try:
        from sage.gateway.session import SessionManager

        manager = SessionManager()

        # 创建会话
        session = manager.get_or_create()
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")

        # 验证
        assert len(session.messages) == 2
        assert session.messages[0].role == "user"
        assert session.messages[1].role == "assistant"

        print("  ✅ Session manager works")
        return True
    except Exception as e:
        print(f"  ❌ Session manager failed: {e}")
        return False


def test_openai_adapter():
    """测试 OpenAI 适配器"""
    print("\nTesting OpenAI adapter...")
    try:
        from sage.gateway.adapters import ChatCompletionRequest, ChatMessage, OpenAIAdapter
        import asyncio

        adapter = OpenAIAdapter()

        # 创建请求
        request = ChatCompletionRequest(
            model="sage-default",
            messages=[ChatMessage(role="user", content="Test")],
            stream=False,
        )

        # 执行请求
        response = asyncio.run(adapter.chat_completions(request))

        # 验证响应
        assert response.model == "sage-default"
        assert len(response.choices) == 1
        assert response.choices[0].message.role == "assistant"

        print("  ✅ OpenAI adapter works")
        return True
    except Exception as e:
        print(f"  ❌ OpenAI adapter failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("SAGE Gateway Phase 1 - Integration Test")
    print("=" * 60)

    results = []

    # 运行所有测试
    results.append(("Installation", test_gateway_installation()))
    results.append(("Session Manager", test_session_manager()))
    results.append(("OpenAI Adapter", test_openai_adapter()))
    # results.append(("Gateway Server", test_gateway_server()))  # 可选，需要较长时间

    # 汇总结果
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name:20} {status}")

    print("=" * 60)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 60)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
