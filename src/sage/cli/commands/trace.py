"""Read local trace timelines without starting an HTTP service."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

from sage.tracing.view import read_events, timeline


def add_trace_parser(subparsers):
    parser = subparsers.add_parser("trace", help="Inspect observable inference traces")
    commands = parser.add_subparsers(dest="trace_command")
    show = commands.add_parser("show", help="Show live/finished NDJSON timeline data")
    show.add_argument("--source", required=True, help="Trace spool directory or NDJSON file")
    show.add_argument("--trace-id")
    show.add_argument(
        "--include-summaries",
        action="store_true",
        help="Show producer-authored, pre-redacted public summaries",
    )
    show.add_argument("--json", action="store_true")
    show.add_argument(
        "--follow", action="store_true", help="Refresh complete records once per second"
    )
    show.set_defaults(_handler=show_trace)
    export = commands.add_parser(
        "export", help="Publish a bounded stable NDJSON snapshot for TraceLoom"
    )
    export.add_argument("--source", required=True)
    export.add_argument("--output", required=True)
    export.add_argument("--include-summaries", action="store_true")
    export.add_argument("--follow", action="store_true")
    export.set_defaults(_handler=export_trace)


def show_trace(args):
    previous = None
    try:
        while True:
            snapshot = timeline(
                read_events(args.source, include_summaries=args.include_summaries), args.trace_id
            )
            encoded = json.dumps(snapshot, sort_keys=True)
            if encoded != previous:
                if args.json:
                    print(encoded, flush=True)
                else:
                    for trace in snapshot["traces"]:
                        print(
                            f"{trace['trace_id']}  {trace['state']}  dropped={trace['dropped_events']}"
                        )
                        for span in trace["spans"]:
                            duration = span["duration_ns"]
                            elapsed = "open" if duration is None else f"{duration / 1e6:.3f} ms"
                            print(f"  {span['span_id']} {span['name']} {span['status']} {elapsed}")
                        path = trace["critical_path"]
                        print(
                            f"  Longest observed dependency path: {path['duration_ns'] / 1e6:.3f} ms (partial evidence)"
                        )
                previous = encoded
            if not args.follow:
                return 0
            time.sleep(1)
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        print("Unable to read trace: invalid, unsupported, inaccessible or over-budget input.")
        return 2


def export_trace(args):
    source, output = Path(args.source).resolve(), Path(args.output).resolve()
    if output == source or source in output.parents:
        print("Trace snapshot output must be separate from the source spool.")
        return 2
    previous = None
    try:
        while True:
            records = read_events(source, include_summaries=args.include_summaries)
            encoded = b"".join(
                (json.dumps(record, separators=(",", ":")) + "\n").encode() for record in records
            )
            if encoded != previous:
                output.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
                descriptor, temporary = tempfile.mkstemp(prefix=".sage-trace-", dir=output.parent)
                try:
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write(encoded)
                    os.replace(temporary, output)
                finally:
                    Path(temporary).unlink(missing_ok=True)
                previous = encoded
            if not args.follow:
                return 0
            time.sleep(1)
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        print("Unable to export trace: invalid, unsupported, inaccessible or over-budget input.")
        return 2
