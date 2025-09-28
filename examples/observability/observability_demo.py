#!/usr/bin/env python3
"""
SAGE Observability 24/7 RCA + ChatOps Demo

Scenario:
- A SaaS/Cloud platform streams logs/metrics/traces continuously
- When an alert fires, the system performs near-real-time root-cause analysis (RCA)
- It proposes remediation steps and posts a concise ChatOps message (Slack/terminal)

This demo is designed to be self-contained with graceful fallbacks:
- No real Prometheus/OpenTelemetry required: we synthesize telemetry in-process
- RAG uses Chroma if available; otherwise a lightweight in-memory store
- LLM generator (OpenAI-compatible) optional; falls back to rule-based response
- Hooks are provided to integrate future middleware: sage_flow, sage_db

Usage:
  python examples/observability/observability_demo.py --duration 20 --alert-cpu 0.85

Env/Test mode:
  Set SAGE_EXAMPLES_MODE=test for lightweight deterministic behavior

"""
import os
import sys
import time
import json
import random
import argparse
from typing import Dict, Any, List, Optional
try:
    import yaml
except ImportError:
    yaml = None

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CUR_DIR, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.map_function import MapFunction
from sage.core.api.function.sink_function import SinkFunction
from sage.common.utils.logging.custom_logger import CustomLogger

# RAG pieces
from sage.libs.rag.retriever import ChromaRetriever
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.generator import OpenAIGenerator

# -----------------------------
# 1) Telemetry generator source
# -----------------------------
class TelemetryBatch(BatchFunction):
    """Continuously generate synthetic metrics/logs/traces events."""

    def __init__(self, interval: float = 0.25, services: Optional[List[str]] = None):
        super().__init__()
        self.interval = max(0.05, float(interval))
        self.services = services or ["api-gw", "orders", "payments", "db", "cache"]
        self.tick = 0
        self._last_time = time.time()

    def _synth_event(self) -> Dict[str, Any]:
        self.tick += 1
        svc = random.choice(self.services)
        # Baseline noise
        base_cpu = random.uniform(0.15, 0.45)
        base_err = random.choice([0.0] * 12 + [0.01, 0.02])
        base_lat = random.uniform(30, 120)  # ms
        # Periodic incidents
        incident = (self.tick // 40) % 7 == 3  # repeating pattern
        if incident and svc in ("orders", "db"):
            base_cpu += random.uniform(0.3, 0.5)
            base_err += random.uniform(0.05, 0.15)
            base_lat += random.uniform(150, 400)
        # Logs
        log_level = random.choices(["INFO", "WARN", "ERROR"], weights=[85, 10, 5])[0]
        if incident and svc == "db":
            log_level = random.choices(["WARN", "ERROR"], weights=[40, 60])[0]
        msg = {
            "INFO": "request served",
            "WARN": "slow query detected",
            "ERROR": "connection timeout to replica",
        }[log_level]
        return {
            "service": svc,
            "cpu": round(min(1.0, base_cpu), 3),
            "error_rate": round(base_err, 3),
            "latency_ms": round(base_lat, 1),
            "log": {"level": log_level, "message": msg},
            "trace": {"span": f"{svc}-op-{self.tick%5}", "duration_ms": round(base_lat * random.uniform(0.5, 1.5), 1)},
            "ts": time.time(),
        }

    def execute(self) -> Dict[str, Any]:
        # simple pacing
        now = time.time()
        dt = now - self._last_time
        if dt < self.interval:
            time.sleep(self.interval - dt)
        self._last_time = time.time()
        return self._synth_event()


# -----------------------------
# 2) Alert detector and enricher
# -----------------------------
class AlertDetector(MapFunction):
    def __init__(self, cpu_threshold: float = 0.85, err_threshold: float = 0.05, latency_ms: float = 250.0):
        super().__init__()
        self.cpu_th = cpu_threshold
        self.err_th = err_threshold
        self.lat_th = latency_ms

    def execute(self, ev: Dict[str, Any]) -> Dict[str, Any]:
        alerted = (
            ev["cpu"] >= self.cpu_th or ev["error_rate"] >= self.err_th or ev["latency_ms"] >= self.lat_th
        )
        ev["alert"] = alerted
        if alerted:
            # Map metric keys to their thresholds explicitly
            thresholds = {"cpu": self.cpu_th, "error_rate": self.err_th, "latency_ms": self.lat_th}
            ev["symptoms"] = {k: ev[k] for k in ("cpu", "error_rate", "latency_ms") if ev[k] >= thresholds[k]}
        return ev


# -------------------------------------
# 3) RCA via RAG over a KB (Chroma/mem)
# -------------------------------------
class RCAEngine(MapFunction):
    """Root-cause analysis using retriever+promptor+generator.
       Falls back to simple rules if generator unavailable."""

    def __init__(self, chroma_conf: Dict[str, Any], embedding_conf: Dict[str, Any], gen_conf: Optional[Dict[str, Any]] = None):
        super().__init__()
        self._use_chroma = True
        self._retriever = None
        self._docs: List[str] = []
        # Build retriever (or fallback)
        try:
            self._retriever = ChromaRetriever({
                "dimension": embedding_conf.get("dimension", 384),
                "top_k": 5,
                "embedding": embedding_conf,
                "chroma": chroma_conf,
            })
        except Exception as e:
            self._use_chroma = False
            self.logger.warning(f"Chroma not available; using in-memory KB. {e}")
        # Seed KB with incident playbooks / patterns
        self._seed_kb()
        # Promptor and optional generator
        self._promptor = QAPromptor({})
        self._generator = None
        if gen_conf:
            try:
                self._generator = OpenAIGenerator(gen_conf)
            except Exception as e:
                self.logger.warning(f"Generator unavailable: {e}")
                self._generator = None

    def _seed_kb(self):
        kb_snippets = [
            "High error_rate and latency in orders often indicate database replica lag; check connections, increase pool, or failover.",
            "Spike in db CPU with connection timeout logs suggests connection storms; enable circuit breaker and tune max_connections.",
            "Cache service WARN slow query detected with rising latency: warm caches and verify key hot-spotting.",
            "payments service high latency and low error: likely upstream api-gw throttling; inspect rate limits and logs.",
            "ERROR connection timeout to replica: verify network routes, DNS, and replica health; consider promoting a healthy replica.",
        ]
        if self._use_chroma and self._retriever is not None:
            try:
                self._retriever.add_documents(kb_snippets)
                return
            except Exception as e:
                self.logger.warning(f"Failed to seed Chroma KB; fallback to memory. {e}")
                self._use_chroma = False
        self._docs.extend(kb_snippets)

    def _search(self, question: str) -> List[str]:
        if self._use_chroma and self._retriever is not None:
            out = self._retriever.execute(question)
            return [ (d.get("text") if isinstance(d, dict) else str(d)) for d in out.get("results", []) ]
        q = question.lower()
        hits = [d for d in self._docs if any(w in d.lower() for w in q.split())]
        return hits[:5]

    def execute(self, ev: Dict[str, Any]) -> Dict[str, Any]:
        if not ev.get("alert"):
            return ev
        # Formulate RCA question from symptoms + recent logs
        service = ev.get("service", "unknown")
        sym = ev.get("symptoms", {})
        logline = f"{ev['log']['level']}: {ev['log']['message']}"
        question = (
            f"service={service} has alert with {json.dumps(sym)}, log='{logline}'. "
            f"What is the most likely root cause and remediation?"
        )
        context = self._search(question)
        prompt_input = {"query": question, "results": [{"text": c} for c in context]}
        user_query, messages = self._promptor.execute(prompt_input)
        if self._generator is None:
            # Rule-based fallback summarizing context
            cause = "db replica lag causing timeouts" if "replica" in (" ".join(context)).lower() else "upstream throttling or connection storms"
            remediation = "increase pool or failover replica" if "replica" in (" ".join(context)).lower() else "enable circuit breaker; tune rate limits"
            ans = f"Likely cause: {cause}. Suggestion: {remediation}."
        else:
            _, ans = self._generator.execute([user_query, messages])
        ev["rca"] = {"question": question, "context": context, "answer": ans}
        return ev


# ---------------------------
# 4) Remediation planner step
# ---------------------------
class RemediationPlanner(MapFunction):
    def execute(self, ev: Dict[str, Any]) -> Dict[str, Any]:
        if not ev.get("rca"):
            return ev
        svc = ev.get("service", "")
        plan: List[str] = []
        answer = ev["rca"]["answer"].lower()
        if "replica" in answer or "db" in answer:
            plan = [
                f"[db] Verify replica health and replication lag for {svc}",
                f"[db] Temporarily increase connection pool limits; enable circuit breaker",
                f"[db] If unhealthy, failover to a healthy replica",
            ]
        elif "circuit breaker" in answer or "throttling" in answer:
            plan = [
                f"[svc] Enable/adjust circuit breaker for {svc}",
                f"[svc] Check API gateway rate limits",
                f"[svc] Gradually roll out config change and monitor",
            ]
        else:
            plan = [
                f"Collect additional diagnostics for {svc}",
                f"Roll back recent changes if any",
                f"Escalate to on-call SRE",
            ]
        ev["remediation_plan"] = plan
        return ev


# ----------------
# 5) ChatOps sink
# ----------------
class ChatOpsSink(SinkFunction):
    def __init__(self, slack_webhook: Optional[str] = None, channel: str = "#oncall"):
        super().__init__()
        self.webhook = slack_webhook
        self.channel = channel

    def _format(self, ev: Dict[str, Any]) -> str:
        svc = ev.get("service")
        sym = ev.get("symptoms", {})
        rca = ev.get("rca", {})
        plan = ev.get("remediation_plan", [])
        txt = [
            f"[ALERT] service={svc} cpu={ev['cpu']} err={ev['error_rate']} lat={ev['latency_ms']}ms",
            f"log: {ev['log']['level']} - {ev['log']['message']}",
        ]
        if rca:
            txt += ["RCA:", f"- {rca['answer']}"]
        if plan:
            txt += ["Plan:"] + [f"- {p}" for p in plan]
        return "\n".join(txt)

    def _post_slack(self, text: str) -> bool:
        if not self.webhook:
            return False
        try:
            import requests  # type: ignore
            payload = {"text": text}
            resp = requests.post(self.webhook, json=payload, timeout=5)
            return resp.status_code // 100 == 2
        except Exception:
            return False

    def execute(self, ev: Dict[str, Any]):
        if not ev.get("alert") or not ev.get("remediation_plan"):
            return
        text = self._format(ev)
        posted = self._post_slack(text)
        if not posted:
            # Terminal fallback
            print("\n===== ChatOps Notification =====")
            print(text)
            print("==============================\n")


# Future hooks: integrate with sage_flow and sage_db middleware
# - Replace TelemetryBatch with a real streaming source wired via sage_flow runtime
# - Store incidents and RCA results in sage_db for historical analytics and drilldown


def run_demo(duration: int = 20, interval: float = 0.25, thresholds: Dict[str, float] = None,
             chroma_conf: Optional[Dict[str, Any]] = None,
             embedding_conf: Optional[Dict[str, Any]] = None,
             gen_conf: Optional[Dict[str, Any]] = None,
             slack_webhook: Optional[str] = None):
    thresholds = thresholds or {"cpu": 0.85, "err": 0.05, "lat": 250.0}

    chroma_conf = chroma_conf or {
        "collection_name": "observability_kb",
        "persistence_path": os.path.join(CUR_DIR, "chroma_obsv_store"),
        "host": "localhost",
        "port": 8000,
        "use_embedding_query": True,
        "metadata": {"hnsw:space": "cosine"},
    }
    embedding_conf = embedding_conf or {
        "method": "default",
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "dimension": 384,
    }
    if gen_conf is None and os.environ.get("SAGE_OPENAI_BASE_URL") and os.environ.get("OPENAI_API_KEY"):
        gen_conf = {
            "method": "openai",
            "model_name": os.environ.get("SAGE_OPENAI_MODEL", "gpt-4o-mini"),
            "base_url": os.environ["SAGE_OPENAI_BASE_URL"],
            "api_key": os.environ["OPENAI_API_KEY"],
        }

    env = LocalEnvironment("ObservabilityDemo")
    rca = RCAEngine(chroma_conf=chroma_conf, embedding_conf=embedding_conf, gen_conf=gen_conf)

    (
        env.from_batch(TelemetryBatch, interval=interval)
        .map(
            AlertDetector,
            cpu_threshold=thresholds["cpu"],
            err_threshold=thresholds["err"],
            latency_ms=thresholds["lat"],
        )
        .map(rca)
        .map(RemediationPlanner)
        .sink(ChatOpsSink, slack_webhook=slack_webhook or os.environ.get("SAGE_SLACK_WEBHOOK"))
    )

    print(f"Running demo for ~{duration}s... Press Ctrl-C to stop earlier.")
    t0 = time.time()
    try:
        env.submit(autostop=False)
        while time.time() - t0 < duration:
            time.sleep(0.2)
        env.close()
    except KeyboardInterrupt:
        env.close()


def main():
    parser = argparse.ArgumentParser(description="SAGE Observability RCA + ChatOps Demo")
    parser.add_argument("--duration", type=int, default=20, help="Run seconds")
    parser.add_argument("--interval", type=float, default=0.25, help="Telemetry event interval seconds")
    parser.add_argument("--alert-cpu", type=float, default=0.85)
    parser.add_argument("--alert-err", type=float, default=0.05)
    parser.add_argument("--alert-lat", type=float, default=250.0)
    parser.add_argument("--config", type=str, default="", help="Path to YAML config for demo")
    parser.add_argument("--slack-webhook", type=str, default="", help="Slack Incoming Webhook URL (optional)")
    args = parser.parse_args()

    CustomLogger.disable_global_console_debug()
    # Optional load config
    chroma_conf = None
    embedding_conf = None
    gen_conf = None
    if args.config and os.path.exists(args.config):
        with open(args.config, "r", encoding="utf-8") as f:
            conf = yaml.safe_load(f) or {}
        thresholds = conf.get("thresholds") or {"cpu": args.alert_cpu, "err": args.alert_err, "lat": args.alert_lat}
        chroma_conf = conf.get("chroma")
        embedding_conf = conf.get("embedding")
        gen_conf = conf.get("generator")
        slack = conf.get("slack", {}).get("webhook") or args.slack_webhook
    else:
        thresholds = {"cpu": args.alert_cpu, "err": args.alert_err, "lat": args.alert_lat}
        slack = args.slack_webhook

    run_demo(
        duration=args.duration,
        interval=args.interval,
        thresholds=thresholds,
        chroma_conf=chroma_conf,
        embedding_conf=embedding_conf,
        gen_conf=gen_conf,
        slack_webhook=slack,
    )


if __name__ == "__main__":
    main()
