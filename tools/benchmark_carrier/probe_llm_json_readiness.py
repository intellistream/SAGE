#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from sage.workloads.large_scale_analysis import (
    OpenAICompletionIncidentReducer,
    _api_key_from_env_or_file,
    _extract_json_payload,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe whether an OpenAI-compatible endpoint can return strict JSON."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-key-env", default="VLLM_HUST_API_KEY")
    parser.add_argument("--env-file", default="~/vllm-hust-dev-hub/.env")
    parser.add_argument(
        "--endpoint-type",
        choices=("chat", "completion"),
        default="chat",
    )
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--timeout-sec", type=int, default=120)
    parser.add_argument(
        "--structured-output",
        action="store_true",
        help="Request an OpenAI-compatible JSON schema response.",
    )
    parser.add_argument(
        "--simple-prompt",
        action="store_true",
        help="Use a minimal JSON-object prompt instead of the incident schema.",
    )
    parser.add_argument(
        "--output",
        default=".sage/benchmarks/llm_json_readiness/probe.json",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    reducer = OpenAICompletionIncidentReducer(
        base_url=args.base_url,
        model=args.model,
        api_key=_api_key_from_env_or_file(args.api_key_env, args.env_file),
        max_tokens=args.max_tokens,
        timeout_sec=args.timeout_sec,
        endpoint_type=args.endpoint_type,
        structured_output=args.structured_output,
    )
    if args.simple_prompt:
        prompt = 'Return ONLY valid JSON: {"ok": true, "answer": 7}'
    else:
        prompt = (
            "Return ONLY valid JSON with exactly this shape: "
            '{"incidents":[{"service":"decode","region":"npu-a",'
            '"start_minute":10,"end_minute":20,"score":0.7,'
            '"signals":["latency"],"evidence_ids":[0]}]}'
        )
    started = time.perf_counter()
    status = "ok"
    raw_text = ""
    parsed: dict[str, Any] | None = None
    error = ""
    try:
        raw_text = reducer._completion(prompt)
        parsed = _extract_json_payload(raw_text)
        if args.simple_prompt:
            if parsed.get("ok") is not True or parsed.get("answer") != 7:
                status = "schema-error"
                error = "Parsed JSON does not match the simple probe object."
        elif not isinstance(parsed.get("incidents"), list):
            status = "schema-error"
            error = "Parsed JSON does not contain an incidents list."
    except Exception as exc:
        status = "error"
        error = f"{type(exc).__name__}: {exc}"

    report = {
        "provenance": "real-online json-readiness probe",
        "base_url": args.base_url,
        "model": args.model,
        "endpoint_type": args.endpoint_type,
        "structured_output": args.structured_output,
        "simple_prompt": args.simple_prompt,
        "status": status,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "parsed_keys": sorted(parsed.keys()) if parsed else [],
        "raw_preview": raw_text[:500],
        "error": error,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
