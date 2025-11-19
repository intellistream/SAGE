#!/usr/bin/env python3
"""Convert mixed log lines from a FIFO into structured JSON logs."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import TextIO


def _now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load_json(line: str) -> dict | None:
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def _wrap_plain(line: str) -> dict:
    return {
        "timestamp": _now_ts(),
        "level": "TEXT",
        "context": "",
        "phase": "",
        "message": line,
    }


def _process_stream(reader: TextIO, writer: TextIO) -> None:
    for raw_line in reader:
        line = raw_line.rstrip("\n")
        if not line:
            continue

        payload = _load_json(line)
        if payload is None:
            payload = _wrap_plain(line)

        writer.write(json.dumps(payload, ensure_ascii=False) + "\n")
        writer.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description="Stream install logs into structured JSON format")
    parser.add_argument("pipe", type=Path, help="Path to the FIFO pipe to read raw log lines from")
    parser.add_argument("target", type=Path, help="Path to the JSON log file to append to")
    args = parser.parse_args()

    if not args.pipe.exists():
        print(f"[log_pipe_writer] Pipe not found: {args.pipe}", file=sys.stderr)
        return 1

    # Ensure parent directory exists for target file
    args.target.parent.mkdir(parents=True, exist_ok=True)

    with (
        args.pipe.open("r", encoding="utf-8", errors="replace") as reader,
        args.target.open("a", encoding="utf-8") as writer,
    ):
        _process_stream(reader, writer)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
