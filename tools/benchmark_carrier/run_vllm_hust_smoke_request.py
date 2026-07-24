#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _api_key(args: argparse.Namespace) -> str:
    if args.api_key_env and os.environ.get(args.api_key_env):
        return os.environ[args.api_key_env]
    env_values = _load_env_file(Path(args.env_file).expanduser())
    if args.api_key_env and env_values.get(args.api_key_env):
        return env_values[args.api_key_env]
    raise RuntimeError(f"Missing API key. Set {args.api_key_env} or provide it in {args.env_file}.")


def _post_json(
    url: str, payload: dict[str, Any], api_key: str, timeout_sec: int
) -> tuple[int, dict[str, Any]]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed: dict[str, Any] = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed = {"raw_error": body}
        return exc.code, parsed


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send one OpenAI-compatible smoke request to a vLLM-HUST endpoint."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:18381")
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--prompt",
        default="SAGE smoke test: answer with one short sentence.",
    )
    parser.add_argument("--max-tokens", type=int, default=24)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout-sec", type=int, default=120)
    parser.add_argument("--api-key-env", default="VLLM_HUST_API_KEY")
    parser.add_argument(
        "--env-file",
        default="~/vllm-hust-dev-hub/.env",
        help="Optional dotenv file used only to read the API key.",
    )
    parser.add_argument(
        "--output",
        default=".sage/benchmarks/real_online_smoke/vllm_hust_smoke.json",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
    }
    started = time.perf_counter()
    status, response = _post_json(
        f"{args.base_url.rstrip('/')}/v1/completions",
        payload,
        _api_key(args),
        args.timeout_sec,
    )
    latency_ms = (time.perf_counter() - started) * 1000
    choices = response.get("choices") if isinstance(response, dict) else None
    usage = response.get("usage", {}) if isinstance(response, dict) else {}
    text = ""
    if choices:
        text = str(choices[0].get("text", ""))
    report = {
        "provenance": "real-online smoke",
        "endpoint": f"{args.base_url.rstrip('/')}/v1/completions",
        "model": args.model,
        "status": status,
        "latency_ms": round(latency_ms, 2),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "text_preview": text[:200],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"ARTIFACT={output}")
    return 0 if status == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
