"""Lightweight chat helpers for the in-tree SAGE CLI."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from sage.foundation import SagePorts, get_user_paths
from sage.serving import SageServeConfig, gateway_openai_base_url, probe_gateway


def resolve_index_root(index_name: str | None) -> Path:
    """Return the storage directory for lightweight chat index metadata."""
    base = get_user_paths().data_dir / "chat" / "indexes"
    base.mkdir(parents=True, exist_ok=True)
    name = (index_name or "default").strip() or "default"
    path = base / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _default_model_for_engine(engine: str) -> str:
    if engine == "sagellm":
        return os.environ.get(
            "SAGE_CHAT_MODEL",
            os.environ.get("SAGELLM_MODEL_NAME", "Qwen/Qwen2.5-0.5B-Instruct"),
        )
    return os.environ.get("OPENAI_MODEL_NAME", "gpt-4o-mini")


def _env_value(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return None


def _has_real_api_key(args: Any) -> bool:
    candidates = [
        os.environ.get(args.api_key_env),
        os.environ.get("SAGE_CHAT_API_KEY"),
        os.environ.get("OPENAI_API_KEY"),
    ]
    for value in candidates:
        if value and value.strip() and value.strip().upper() != "EMPTY":
            return True
    return False


def _sagellm_executable() -> str | None:
    return _env_value("SAGELLM_BIN") or shutil.which("sagellm")


def _detect_backend(args: Any) -> tuple[str | None, str | None]:
    if args.backend == "direct":
        sagellm_bin = _sagellm_executable()
        if sagellm_bin:
            return "direct", f"使用本机 sagellm CLI: {sagellm_bin}"
        return None, "未找到 `sagellm` 可执行文件，无法使用 direct 模式。"
    if args.backend == "openai":
        return "openai", None

    probe = probe_gateway(
        SageServeConfig(
            host=args.host,
            port=args.port,
            model=args.model,
        )
    )
    if probe.ok:
        return "openai", f"已检测到本地 sagellm gateway: {probe.url}"

    sagellm_bin = _sagellm_executable()
    if sagellm_bin:
        return "direct", f"未检测到 gateway，改为直接调用 sagellm CLI: {sagellm_bin}"

    configured_base_url = _env_value("SAGE_CHAT_BASE_URL", "OPENAI_BASE_URL", "SAGELLM_BASE_URL")
    if configured_base_url and _has_real_api_key(args):
        return "openai", f"使用环境变量中配置的 OpenAI 兼容 endpoint: {configured_base_url}"
    if _has_real_api_key(args):
        return "openai", "检测到云端 API Key，将使用默认 OpenAI 兼容端点。"

    return (
        None,
        "未检测到可用的 sagellm gateway，也未配置可用的云端 API。"
        "同时本机也不存在 `sagellm` 命令，因此 `sage chat` 无法继续。",
    )


def _chat_base_url(args: Any) -> str:
    if args.base_url:
        return args.base_url.rstrip("/")
    env_url = _env_value("SAGE_CHAT_BASE_URL", "OPENAI_BASE_URL", "SAGELLM_BASE_URL")
    if env_url:
        return env_url.rstrip("/")
    if _has_real_api_key(args):
        return "https://api.openai.com/v1"
    return gateway_openai_base_url(args.host, args.port).rstrip("/")


def _api_key_for_request(args: Any) -> str:
    return _env_value(args.api_key_env, "SAGE_CHAT_API_KEY", "OPENAI_API_KEY") or "EMPTY"


def _run_direct_sagellm(prompt: str | None, args: Any) -> int:
    sagellm_bin = _sagellm_executable()
    if not sagellm_bin:
        print("未找到 `sagellm` 可执行文件，无法直接调用真实推理引擎。", file=sys.stderr)
        return 2

    command = [sagellm_bin]
    if prompt is None:
        command.append("chat")
    else:
        command.extend(["run", "-p", prompt])
        if args.stream:
            command.append("--stream")

    if args.model:
        command.extend(["-m", args.model])
    if args.direct_backend:
        command.extend(["--backend", args.direct_backend])
    if args.max_tokens is not None:
        command.extend(["--max-tokens", str(args.max_tokens)])
    if args.temperature is not None:
        command.extend(["-t", str(args.temperature)])
    if args.top_p is not None:
        command.extend(["--top-p", str(args.top_p)])
    if args.top_k is not None:
        command.extend(["--top-k", str(args.top_k)])
    if args.repetition_penalty is not None:
        command.extend(["--repetition-penalty", str(args.repetition_penalty)])
    if args.debug:
        command.append("--debug")

    completed = subprocess.run(command, check=False)
    return int(completed.returncode)


def _request_openai_chat(prompt: str, args: Any) -> int:
    model = args.model or _default_model_for_engine(args.engine)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": bool(args.stream),
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url=f"{_chat_base_url(args)}/chat/completions",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_api_key_for_request(args)}",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            if args.stream:
                _stream_sse_response(response)
            else:
                parsed = json.loads(response.read().decode("utf-8"))
                message = parsed.get("choices", [{}])[0].get("message", {}).get("content", "")
                print(message)
            return 0
    except urllib.error.URLError as exc:
        print(f"chat 请求失败: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"chat 响应解析失败: {exc}", file=sys.stderr)
        return 1


def _stream_sse_response(response: Any) -> None:
    for raw_line in response:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line or not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        delta = payload.get("choices", [{}])[0].get("delta", {})
        content = delta.get("content")
        if content:
            sys.stdout.write(content)
            sys.stdout.flush()
    sys.stdout.write("\n")
    sys.stdout.flush()


def run_chat(args: Any) -> int:
    """Run interactive or one-shot chat."""
    backend, note = _detect_backend(args)
    if backend is None:
        print(note, file=sys.stderr)
        return 2

    model = args.model or _default_model_for_engine(args.engine)

    if args.ask:
        prompt = args.ask
        if backend == "direct":
            args.model = model
            return _run_direct_sagellm(prompt, args)
        return _request_openai_chat(prompt, args)

    if backend == "direct":
        if note:
            print(note)
        args.model = model
        return _run_direct_sagellm(None, args)

    print(f"SAGE chat ({backend}, model={model})")
    if note:
        print(note)
    print("输入 exit / quit 退出")
    while True:
        try:
            prompt = input("sage chat> ").strip()
        except EOFError:
            print("")
            return 0
        except KeyboardInterrupt:
            print("\n已退出")
            return 0

        if not prompt:
            continue
        if prompt.lower() in {"exit", "quit"}:
            return 0

        status = _request_openai_chat(prompt, args)
        if status != 0:
            return status


def run_index_ingest(args: Any) -> int:
    """Persist lightweight ingest metadata for optional adapter workflows."""
    index_root = resolve_index_root(args.index)
    metadata = {
        "source": args.source,
        "index": args.index or "default",
        "embedding_method": args.embedding_method,
        "embedding_model": args.embedding_model,
        "embedding_base_url": args.embedding_base_url,
        "created_at": time.time(),
        "mode": "core-placeholder",
        "note": "Full retrieval ingestion remains an optional adapter capability.",
    }
    (index_root / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not args.quiet:
        print(f"已写入轻量索引元数据: {index_root}")
        print(
            "提示: 真正的 RAG ingestion 仍需安装可选 adapter（如 isage-rag / isage[capability-adapters]）。"
        )
    return 0


def add_chat_parser(subparsers: Any) -> None:
    """Register the `chat` command tree."""
    chat = subparsers.add_parser(
        "chat", help="Run chat via sagellm gateway / direct CLI / OpenAI-compatible backends"
    )
    chat.set_defaults(_handler=run_chat)
    chat.add_argument(
        "--engine", default="sagellm", choices=["sagellm"], help="Inference engine family"
    )
    chat.add_argument(
        "--backend",
        default="auto",
        choices=["auto", "openai", "direct"],
        help="Chat backend selection",
    )
    chat.add_argument("--model", default=None, help="Model id")
    chat.add_argument("--ask", default=None, help="Single-shot prompt")
    chat.add_argument("--stream", action="store_true", help="Enable streamed output when supported")
    chat.add_argument("--host", default="127.0.0.1", help="Gateway host")
    chat.add_argument("--port", type=int, default=SagePorts.SAGELLM_GATEWAY, help="Gateway port")
    chat.add_argument("--base-url", default=None, help="Explicit OpenAI-compatible base URL")
    chat.add_argument(
        "--api-key-env",
        default="SAGELLM_API_KEY",
        help="Environment variable used for API key lookup",
    )
    chat.add_argument("--timeout", type=float, default=30.0, help="Request timeout in seconds")
    chat.add_argument(
        "--direct-backend", default=None, help="Direct sagellm backend override (cpu/cuda/ascend)"
    )
    chat.add_argument("--max-tokens", type=int, default=None, help="Max output tokens")
    chat.add_argument("--temperature", type=float, default=None, help="Sampling temperature")
    chat.add_argument("--top-p", type=float, default=None, help="Nucleus sampling threshold")
    chat.add_argument("--top-k", type=int, default=None, help="Top-k sampling")
    chat.add_argument("--repetition-penalty", type=float, default=None, help="Repetition penalty")
    chat.add_argument("--debug", action="store_true", help="Enable verbose direct sagellm logs")


def add_index_parser(subparsers: Any) -> None:
    """Register the `index` command tree."""
    index = subparsers.add_parser(
        "index", help="Manage lightweight local index metadata for optional adapter workflows"
    )
    index_sub = index.add_subparsers(dest="index_command")

    ingest = index_sub.add_parser(
        "ingest", help="Record lightweight index metadata for optional adapter workflows"
    )
    ingest.set_defaults(_handler=run_index_ingest)
    ingest.add_argument("--source", default=".", help="Source directory or file")
    ingest.add_argument("--index", default="default", help="Index name")
    ingest.add_argument("--quiet", action="store_true", help="Suppress informational output")
    ingest.add_argument("--embedding-method", default="hf")
    ingest.add_argument("--embedding-model", default="BAAI/bge-m3")
    ingest.add_argument("--embedding-base-url", default=None)
