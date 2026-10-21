"""Bounded loopback HTTP adapter for SAGE advisory checks; no raw answer logs."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from sage.runtime.answer_advisory import audit_answer, validate_catalog


def create_server(catalog: list[dict], port: int = 55109) -> HTTPServer:
    validate_catalog(catalog)

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, *_args):
            pass

        def reply(self, status, body):
            encoded = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self):
            self.reply(
                200 if self.path == "/health" else 404,
                {
                    "service": "sage-answer-advisory",
                    "mode": "advisory",
                    "catalog_sources": len(catalog),
                },
            )

        def do_POST(self):
            if self.path != "/audit":
                self.reply(404, {"error": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 2_000_000:
                    self.reply(413, {"error": "advisory_size_limit", "status": "unchecked"})
                    return
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError("incomplete request")
                body = json.loads(raw)
                if not isinstance(body, dict) or set(body) != {"question", "answer"}:
                    raise ValueError("invalid request fields")
                result = audit_answer(body["question"], body["answer"], catalog)
            except (ValueError, TypeError, TimeoutError):
                self.reply(400, {"error": "invalid_advisory_request", "status": "unchecked"})
                return
            self.reply(200, result)

    return HTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--port", type=int, default=55109)
    args = parser.parse_args()
    catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    create_server(catalog, args.port).serve_forever()


if __name__ == "__main__":
    main()
