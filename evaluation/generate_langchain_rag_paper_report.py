#!/usr/bin/env python3
"""Generate paper-ready LangChain + SAGE RAG result reports."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

main = importlib.import_module("evaluation.langchain_rag.paper_report").main

if __name__ == "__main__":
    raise SystemExit(main())
