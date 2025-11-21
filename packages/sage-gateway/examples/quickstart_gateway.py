#!/usr/bin/env python3
"""
Quick Start Script for SAGE Gateway Phase 1

启动 sage-gateway 服务并进行基本测试
"""

import subprocess
import sys
import time


def check_port(port: int) -> bool:
    """检查端口是否可用"""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("", port))
            return True
        except OSError:
            return False


def main():
    print("=" * 60)
    print("SAGE Gateway Phase 1 - Quick Start")
    print("=" * 60)

    # 1. 检查环境
    print("\n[1/5] Checking environment...")
    try:
        import importlib.util

        required = ["fastapi", "uvicorn", "pydantic", "sse_starlette"]
        for pkg in required:
            if importlib.util.find_spec(pkg) is None:
                raise ImportError(f"{pkg} not found")

        print("✅ All required packages installed")
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("\n📦 Installing sage-gateway...")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-e",
                "packages/sage-gateway",
            ],
            check=True,
        )
        print("✅ sage-gateway installed")

    # 2. 检查端口
    print("\n[2/5] Checking port 8000...")
    if not check_port(8000):
        print("⚠️  Port 8000 is in use")
        print("   Stopping existing services...")
        # 尝试关闭占用的进程（仅 Linux）
        try:
            subprocess.run(["pkill", "-f", "sage.gateway.server"], stderr=subprocess.DEVNULL)
            time.sleep(1)
        except Exception:
            pass

    # 3. 启动 gateway
    print("\n[3/5] Starting sage-gateway server...")
    print("   URL: http://localhost:8000")

    gateway_process = subprocess.Popen(
        [sys.executable, "-m", "sage.gateway.server"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # 等待服务启动
    print("   Waiting for server to start...", end="", flush=True)
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
        print("   Failed to start gateway")
        gateway_process.kill()
        return 1

    # 4. 运行测试
    print("\n[4/5] Running basic tests...")

    print("\n   a) Health Check:")
    try:
        import urllib.request
        import json

        response = urllib.request.urlopen("http://localhost:8000/health")
        data = json.loads(response.read())
        print(f"      ✅ Status: {data['status']}")
    except Exception as e:
        print(f"      ❌ Error: {e}")

    print("\n   b) Chat Completion (non-streaming):")
    try:
        import urllib.request
        import json

        req = urllib.request.Request(
            "http://localhost:8000/v1/chat/completions",
            data=json.dumps(
                {
                    "model": "sage-default",
                    "messages": [{"role": "user", "content": "Hello!"}],
                    "stream": False,
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        response = urllib.request.urlopen(req)
        data = json.loads(response.read())
        print(f"      ✅ Response: {data['choices'][0]['message']['content'][:50]}...")
    except Exception as e:
        print(f"      ❌ Error: {e}")

    # 5. 显示使用示例
    print("\n[5/5] Gateway is ready! 🚀")
    print("\n" + "=" * 60)
    print("📚 Usage Examples:")
    print("=" * 60)

    print("\n1️⃣  Using cURL:")
    print("""
    curl -X POST http://localhost:8000/v1/chat/completions \\
      -H "Content-Type: application/json" \\
      -d '{
        "model": "sage-default",
        "messages": [{"role": "user", "content": "Hello!"}]
      }'
    """)

    print("\n2️⃣  Using Python (OpenAI SDK):")
    print("""
    from openai import OpenAI

    client = OpenAI(
        base_url=\"http://localhost:8000/v1\",
        api_key=\"sage-token\"  # pragma: allowlist secret
    )

    response = client.chat.completions.create(
        model="sage-default",
        messages=[{"role": "user", "content": "Hello!"}]
    )

    print(response.choices[0].message.content)
    """)

    print("\n3️⃣  Test Examples:")
    print("   bash packages/sage-gateway/examples/curl_examples.sh")
    print("   python packages/sage-gateway/examples/openai_client_example.py")

    print("\n" + "=" * 60)
    print("Press Ctrl+C to stop the gateway")
    print("=" * 60)

    # 保持运行
    try:
        gateway_process.wait()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gateway...")
        gateway_process.terminate()
        gateway_process.wait(timeout=5)
        print("✅ Gateway stopped")

    return 0


if __name__ == "__main__":
    sys.exit(main())
