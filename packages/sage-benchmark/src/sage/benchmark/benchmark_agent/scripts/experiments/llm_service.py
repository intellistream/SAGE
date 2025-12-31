"""
LLM Service Manager - LLM 服务管理模块

提供统一的 LLM 服务管理功能:
- 启动/停止 vLLM 服务
- 检查服务状态
- 多端口管理
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# 端口配置
try:
    from sage.common.config.ports import SagePorts

    DEFAULT_LLM_PORT = SagePorts.BENCHMARK_LLM
except ImportError:
    DEFAULT_LLM_PORT = 8901

DEFAULT_LLM_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
LLM_PID_FILE = Path.home() / ".sage" / "benchmark_llm.pid"

# LLM 主机地址，支持 Docker 环境
# 优先使用环境变量 LLM_HOST，否则默认 localhost
DEFAULT_LLM_HOST = os.environ.get("LLM_HOST", "localhost")


def check_llm_service(port: int = DEFAULT_LLM_PORT, host: str | None = None) -> dict:
    """
    检查 LLM 服务状态。

    Args:
        port: 服务端口
        host: 服务主机地址，默认使用 LLM_HOST 环境变量或 localhost

    Returns:
        状态字典 {"running": bool, "port": int, "model": str, "error": str}
    """
    if host is None:
        host = DEFAULT_LLM_HOST

    try:
        import httpx
    except ImportError:
        return {"running": False, "port": port, "model": None, "error": "httpx not installed"}

    result = {"running": False, "port": port, "model": None, "error": None}

    try:
        response = httpx.get(f"http://{host}:{port}/v1/models", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            if models:
                result["running"] = True
                result["model"] = models[0].get("id", "unknown")
        else:
            result["error"] = f"HTTP {response.status_code}"
    except httpx.ConnectError:
        result["error"] = "Connection refused"
    except httpx.TimeoutException:
        result["error"] = "Timeout"
    except Exception as e:
        result["error"] = str(e)

    return result


def check_all_llm_services() -> dict[int, dict]:
    """
    检查所有可能的 LLM 服务端口。

    Returns:
        {port: status_dict, ...}
    """
    try:
        from sage.common.config.ports import SagePorts

        ports = [SagePorts.BENCHMARK_LLM] + SagePorts.get_llm_ports()
    except ImportError:
        ports = [DEFAULT_LLM_PORT, 8001, 8000]

    # 去重
    seen = set()
    unique_ports = []
    for port in ports:
        if port not in seen:
            seen.add(port)
            unique_ports.append(port)

    return {port: check_llm_service(port) for port in unique_ports}


def start_llm_service(
    model: str = DEFAULT_LLM_MODEL,
    port: int = DEFAULT_LLM_PORT,
    gpu_memory: float = 0.5,
    timeout: int = 120,
) -> bool:
    """
    启动 vLLM 服务。

    Args:
        model: 模型 ID
        port: 服务端口
        gpu_memory: GPU 显存使用比例
        timeout: 等待启动超时秒数

    Returns:
        是否成功启动
    """
    # 检查是否已运行
    status = check_llm_service(port)
    if status["running"]:
        print(f"✅ LLM 服务已在运行 (port={port}, model={status['model']})")
        return True

    print("🚀 启动 LLM 服务...")
    print(f"   模型: {model}")
    print(f"   端口: {port}")
    print(f"   GPU 显存: {gpu_memory * 100:.0f}%")

    # 确保 PID 文件目录存在
    LLM_PID_FILE.parent.mkdir(parents=True, exist_ok=True)

    # 构建命令
    cmd = [
        sys.executable,
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model",
        model,
        "--port",
        str(port),
        "--gpu-memory-utilization",
        str(gpu_memory),
        "--trust-remote-code",
    ]

    try:
        # 启动后台进程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )

        # 保存 PID
        with open(LLM_PID_FILE, "w") as f:
            f.write(str(process.pid))

        print(f"   PID: {process.pid}")
        print("   等待服务启动...")

        # 等待服务就绪
        for i in range(timeout):
            time.sleep(1)
            if check_llm_service(port)["running"]:
                print(f"\n✅ LLM 服务已启动 (耗时 {i + 1}s)")
                return True
            if i % 10 == 9:
                print(f"   已等待 {i + 1}s...")

        print("\n❌ 服务启动超时")
        return False

    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False


def stop_llm_service() -> bool:
    """
    停止 LLM 服务。

    Returns:
        是否成功停止
    """
    if not LLM_PID_FILE.exists():
        print("ℹ️  没有找到运行中的 LLM 服务")
        return True

    try:
        with open(LLM_PID_FILE) as f:
            pid = int(f.read().strip())

        print(f"🛑 停止 LLM 服务 (PID={pid})...")
        os.kill(pid, signal.SIGTERM)

        # 等待进程结束
        for _ in range(10):
            try:
                os.kill(pid, 0)  # 检查进程是否存在
                time.sleep(0.5)
            except OSError:
                break

        LLM_PID_FILE.unlink(missing_ok=True)
        print("✅ LLM 服务已停止")
        return True

    except ProcessLookupError:
        # 进程已不存在
        LLM_PID_FILE.unlink(missing_ok=True)
        print("✅ LLM 服务已停止")
        return True
    except Exception as e:
        print(f"❌ 停止失败: {e}")
        return False


def print_llm_status():
    """打印 LLM 服务状态。"""
    print("\n📡 LLM 服务状态")
    print("=" * 50)

    statuses = check_all_llm_services()

    for port, status in statuses.items():
        if status["running"]:
            print(f"  ✅ Port {port}: 运行中")
            print(f"     模型: {status['model']}")
        else:
            print(f"  ❌ Port {port}: {status['error'] or '未运行'}")


def ensure_llm_available(
    port: int = DEFAULT_LLM_PORT,
    model: str = DEFAULT_LLM_MODEL,
    auto_start: bool = True,
    allow_cloud: bool = True,
) -> bool:
    """
    确保 LLM 服务可用。

    如果服务未运行且 auto_start=True，会尝试启动服务。

    优先级:
    1. 检查 SAGE_CHAT_BASE_URL 环境变量（用户显式指定）
    2. 检查指定端口
    3. 检查其他常用端口
    4. 检查云端 API 配置
    5. 尝试自动启动

    Args:
        port: 服务端口
        model: 模型 ID
        auto_start: 是否自动启动
        allow_cloud: 是否允许使用云端 API (默认 True)

    Returns:
        服务是否可用
    """
    # 1. 首先检查用户是否通过环境变量显式指定了 LLM 端点
    env_base_url = os.environ.get("SAGE_CHAT_BASE_URL")
    if env_base_url:
        print(f"  ✅ 使用环境变量 SAGE_CHAT_BASE_URL: {env_base_url}")
        # 验证端点是否可用
        try:
            import httpx

            response = httpx.get(f"{env_base_url}/models", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                if models:
                    print(f"     模型: {models[0].get('id', 'unknown')}")
                    return True
            print(f"  ⚠️  环境变量指定的端点返回异常: HTTP {response.status_code}")
        except Exception as e:
            print(f"  ⚠️  环境变量指定的端点不可用: {e}")
        # 继续检查其他端口

    # 2. 检查指定端口
    print(f"  🔍 Checking LLM service on port {port}...")
    status = check_llm_service(port)
    if status["running"]:
        print(f"  ✅ Found running service on port {port}")
        # 设置环境变量供后续使用
        # 使用 LLM_HOST 环境变量（Docker 环境兼容）
        llm_host = os.environ.get("LLM_HOST", "localhost")
        os.environ["SAGE_LLM_PORT"] = str(port)
        os.environ["SAGE_CHAT_BASE_URL"] = f"http://{llm_host}:{port}/v1"
        return True

    # 3. 检查其他端口
    print("  🔍 Checking other common ports...")
    all_statuses = check_all_llm_services()
    for p, s in all_statuses.items():
        if s["running"]:
            print(f"  ℹ️  Found running service on port {p}")
            # 设置环境变量供后续使用
            llm_host = os.environ.get("LLM_HOST", "localhost")
            os.environ["SAGE_LLM_PORT"] = str(p)
            os.environ["SAGE_CHAT_BASE_URL"] = f"http://{llm_host}:{p}/v1"
            return True

    # 4. 检查云端 API 配置
    if allow_cloud and (os.environ.get("SAGE_CHAT_API_KEY") or os.environ.get("OPENAI_API_KEY")):
        print("  ℹ️  检测到云端 API 配置")
        return True

    # 5. 尝试自动启动
    if auto_start:
        print("  ⚠️  未检测到可用的 LLM 服务，尝试自动启动...")
        return start_llm_service(model=model, port=port)

    return False


# =============================================================================
# CLI 入口
# =============================================================================


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="LLM Service Manager",
    )

    subparsers = parser.add_subparsers(dest="action", help="操作")

    # start
    start_parser = subparsers.add_parser("start", help="启动 LLM 服务")
    start_parser.add_argument("--model", default=DEFAULT_LLM_MODEL, help="模型 ID")
    start_parser.add_argument("--port", type=int, default=DEFAULT_LLM_PORT, help="端口")
    start_parser.add_argument("--gpu-memory", type=float, default=0.5, help="GPU 显存比例")

    # stop
    subparsers.add_parser("stop", help="停止 LLM 服务")

    # status
    subparsers.add_parser("status", help="查看服务状态")

    args = parser.parse_args()

    if args.action == "start":
        success = start_llm_service(
            model=args.model,
            port=args.port,
            gpu_memory=args.gpu_memory,
        )
        return 0 if success else 1

    elif args.action == "stop":
        success = stop_llm_service()
        return 0 if success else 1

    elif args.action == "status":
        print_llm_status()
        return 0

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
