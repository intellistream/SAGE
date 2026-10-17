#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

DEFAULT_PROMPT = (
    "You are validating a SAGE real-online benchmark. "
    "Reply with a concise technical sentence about semantic orchestration."
)


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


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return round(values[0], 2)
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 2)


def _mean(values: list[float]) -> float | None:
    return round(statistics.fmean(values), 2) if values else None


def _post_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
    request_id: int,
    timeout_sec: int,
    stream: bool,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
    }
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    started = time.perf_counter()
    first_token_at: float | None = None
    output_text = ""
    completion_tokens: int | None = None
    prompt_tokens: int | None = None
    status = 0
    error = ""
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as response:
            status = response.status
            if stream:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data = line.removeprefix("data: ").strip()
                    if data == "[DONE]":
                        break
                    event = json.loads(data)
                    choices = event.get("choices") or []
                    if choices:
                        text = choices[0].get("text") or ""
                        if text and first_token_at is None:
                            first_token_at = time.perf_counter()
                        output_text += text
                    usage = event.get("usage") or {}
                    prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
                    completion_tokens = usage.get(
                        "completion_tokens",
                        completion_tokens,
                    )
            else:
                body = response.read().decode("utf-8")
                parsed = json.loads(body) if body else {}
                choices = parsed.get("choices") or []
                if choices:
                    output_text = choices[0].get("text") or ""
                    first_token_at = time.perf_counter()
                usage = parsed.get("usage") or {}
                prompt_tokens = usage.get("prompt_tokens")
                completion_tokens = usage.get("completion_tokens")
    except urllib.error.HTTPError as exc:
        status = exc.code
        error = exc.read().decode("utf-8", errors="replace")[:500]
    except Exception as exc:  # pragma: no cover - environment dependent
        error = f"{type(exc).__name__}: {exc}"

    ended = time.perf_counter()
    output_token_estimate = len(output_text.split())
    completion_token_source = "usage"
    if completion_tokens is None:
        completion_tokens = output_token_estimate
        completion_token_source = "text_split_estimate"
    latency_ms = (ended - started) * 1000
    ttft_ms = (first_token_at - started) * 1000 if first_token_at else None
    decode_ms = latency_ms - ttft_ms if ttft_ms is not None else None
    tpot_ms = None
    if decode_ms is not None and completion_tokens and completion_tokens > 1:
        tpot_ms = decode_ms / max(completion_tokens - 1, 1)
    tokens_per_s = None
    if completion_tokens:
        tokens_per_s = completion_tokens / max(latency_ms / 1000, 0.001)
    return {
        "request_id": request_id,
        "status": status,
        "latency_ms": round(latency_ms, 2),
        "ttft_ms": round(ttft_ms, 2) if ttft_ms is not None else None,
        "decode_ms": round(decode_ms, 2) if decode_ms is not None else None,
        "tpot_ms": round(tpot_ms, 2) if tpot_ms is not None else None,
        "tokens_per_s": round(tokens_per_s, 4) if tokens_per_s is not None else None,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "completion_token_source": completion_token_source,
        "text_preview": output_text[:160],
        "error": error,
    }


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ok_rows = [row for row in rows if row["status"] == 200 and not row["error"]]
    aggregate: dict[str, Any] = {
        "request_count": len(rows),
        "ok_count": len(ok_rows),
        "error_count": len(rows) - len(ok_rows),
    }
    for metric in ("latency_ms", "ttft_ms", "decode_ms", "tpot_ms", "tokens_per_s"):
        values = [float(row[metric]) for row in ok_rows if row.get(metric) is not None]
        aggregate[metric] = {
            "mean": _mean(values),
            "p50": _percentile(values, 0.50),
            "p95": _percentile(values, 0.95),
            "min": round(min(values), 2) if values else None,
            "max": round(max(values), 2) if values else None,
        }
    aggregate["total_completion_tokens"] = sum(
        int(row.get("completion_tokens") or 0) for row in ok_rows
    )
    aggregate["total_prompt_tokens"] = sum(int(row.get("prompt_tokens") or 0) for row in ok_rows)
    aggregate["completion_token_sources"] = dict(
        sorted(
            {
                source: sum(1 for row in ok_rows if row.get("completion_token_source") == source)
                for source in {
                    str(row.get("completion_token_source"))
                    for row in ok_rows
                    if row.get("completion_token_source")
                }
            }.items()
        )
    )
    return aggregate


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a small real-online benchmark against vLLM-HUST."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:18381")
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--requests", type=int, default=8)
    parser.add_argument("--warmup-requests", type=int, default=2)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--timeout-sec", type=int, default=180)
    parser.add_argument("--stream", action="store_true", default=True)
    parser.add_argument("--no-stream", action="store_false", dest="stream")
    parser.add_argument("--api-key-env", default="VLLM_HUST_API_KEY")
    parser.add_argument("--env-file", default="~/vllm-hust-dev-hub/.env")
    parser.add_argument(
        "--output-dir",
        default=".sage/benchmarks/real_online_vllm_hust",
    )
    parser.add_argument("--run-id")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    api_key = _api_key(args)
    run_id = args.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    outdir = Path(args.output_dir) / run_id
    outdir.mkdir(parents=True, exist_ok=True)

    warmups = [
        _post_completion(
            base_url=args.base_url,
            api_key=api_key,
            model=args.model,
            prompt=args.prompt,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            request_id=-(index + 1),
            timeout_sec=args.timeout_sec,
            stream=args.stream,
        )
        for index in range(args.warmup_requests)
    ]

    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(
                _post_completion,
                base_url=args.base_url,
                api_key=api_key,
                model=args.model,
                prompt=args.prompt,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                request_id=request_id,
                timeout_sec=args.timeout_sec,
                stream=args.stream,
            )
            for request_id in range(args.requests)
        ]
        for future in as_completed(futures):
            rows.append(future.result())
    wall_ms = (time.perf_counter() - started) * 1000
    rows.sort(key=lambda row: row["request_id"])
    aggregate = _aggregate(rows)
    aggregate["measured_wall_ms"] = round(wall_ms, 2)
    aggregate["end_to_end_completion_tokens_per_s"] = round(
        aggregate["total_completion_tokens"] / max(wall_ms / 1000, 0.001),
        4,
    )

    metadata = {
        "provenance": "real-online",
        "base_url": args.base_url,
        "model": args.model,
        "prompt": args.prompt,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "requests": args.requests,
        "warmup_requests": args.warmup_requests,
        "concurrency": args.concurrency,
        "stream": args.stream,
        "run_id": run_id,
    }
    report = {
        "metadata": metadata,
        "warmup": warmups,
        "rows": rows,
        "aggregate": aggregate,
    }
    (outdir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (outdir / "requests.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    (outdir / "aggregate.json").write_text(
        json.dumps({"metadata": metadata, "aggregate": aggregate}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"metadata": metadata, "aggregate": aggregate}, ensure_ascii=False, indent=2))
    print(f"RESULT_DIR={outdir}")
    return 0 if aggregate["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
