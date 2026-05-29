from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from socketserver import ThreadingMixIn
from typing import Any
from urllib.parse import urlparse, urlunparse
from xmlrpc.client import ServerProxy, Transport
from xmlrpc.server import SimpleXMLRPCServer

from .stages import LangChainGenerationStage, LangChainMemoryStage, LangChainRetrievalStage

DEFAULT_LANGCHAIN_RPC_PORT = 19500


def _normalize_endpoint(endpoint: str) -> str:
    normalized = str(endpoint).strip()
    if not normalized:
        raise ValueError("langchain_rpc endpoint cannot be empty")
    if "://" not in normalized:
        normalized = f"http://{normalized}"
    parsed = urlparse(normalized)
    path = parsed.path or "/RPC2"
    return urlunparse((parsed.scheme or "http", parsed.netloc, path, "", "", ""))


class _TimeoutTransport(Transport):
    def __init__(self, timeout_s: float) -> None:
        super().__init__()
        self._timeout_s = timeout_s

    def make_connection(self, host):  # type: ignore[override]
        connection = super().make_connection(host)
        connection.timeout = self._timeout_s
        return connection


def _json_safe_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(payload, ensure_ascii=False))


@dataclass
class _RpcRunProcessor:
    node_id: str
    retrieval: LangChainRetrievalStage
    memory: LangChainMemoryStage
    generation: LangChainGenerationStage

    @classmethod
    def from_config(cls, node_id: str, run_config: dict[str, Any]) -> _RpcRunProcessor:
        return cls(
            node_id=node_id,
            retrieval=LangChainRetrievalStage(
                documents=list(run_config.get("documents") or []),
                enable_retrieval=bool(run_config.get("enable_retrieval")),
                top_k=int(run_config.get("top_k") or 3),
                chunk_size=int(run_config.get("chunk_size") or 320),
                chunk_overlap=int(run_config.get("chunk_overlap") or 48),
                embedding_model=run_config.get("embedding_model"),
                embedding_base_url=run_config.get("embedding_base_url"),
                embedding_api_key=run_config.get("embedding_api_key"),
                offline_index_dir=run_config.get("retrieval_index_dir"),
            ),
            memory=LangChainMemoryStage(
                max_turns=int(run_config.get("max_memory_turns") or 4),
                enable_memory=bool(run_config.get("enable_memory")),
            ),
            generation=LangChainGenerationStage(
                variant_name=str(run_config.get("variant_name") or "unknown"),
                model=run_config.get("model"),
                model_provider=run_config.get("model_provider"),
                generation_base_url=run_config.get("generation_base_url"),
                generation_api_key=run_config.get("generation_api_key"),
                temperature=float(run_config.get("temperature") or 0.0),
            ),
        )

    def process_item(self, item: dict[str, Any]) -> dict[str, Any]:
        payload = self.retrieval.execute(dict(item))
        payload = self.memory.execute(payload)
        payload = self.generation.execute(payload)
        payload.pop("memory_history", None)
        payload["rpc_node_id"] = self.node_id
        return _json_safe_payload(payload)


class LangChainRpcWorker:
    def __init__(self, node_id: str = "unknown-node") -> None:
        self._node_id = node_id
        self._lock = threading.Lock()
        self._runs: dict[str, _RpcRunProcessor] = {}
        self._shutdown_callback: callable[[], None] | None = None

    def set_shutdown_callback(self, callback: callable[[], None]) -> None:
        self._shutdown_callback = callback

    def ping(self) -> dict[str, Any]:
        return {"status": "ok", "node_id": self._node_id}

    def setup_run(self, run_id: str, run_config: dict[str, Any]) -> dict[str, Any]:
        processor = _RpcRunProcessor.from_config(self._node_id, run_config)
        with self._lock:
            self._runs[str(run_id)] = processor
        return {
            "status": "ready",
            "node_id": self._node_id,
            "run_id": str(run_id),
        }

    def process_item(self, run_id: str, item: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            processor = self._runs.get(str(run_id))
        if processor is None:
            raise RuntimeError(f"langchain rpc run not found: {run_id}")
        return processor.process_item(item)

    def teardown_run(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            removed = self._runs.pop(str(run_id), None)
        return {
            "status": "removed" if removed is not None else "missing",
            "node_id": self._node_id,
            "run_id": str(run_id),
        }

    def shutdown(self) -> dict[str, Any]:
        callback = self._shutdown_callback
        if callback is not None:
            callback()
        return {"status": "shutdown_requested", "node_id": self._node_id}


class _ThreadedXmlRpcServer(ThreadingMixIn, SimpleXMLRPCServer):
    daemon_threads = True
    allow_reuse_address = True


def create_langchain_rpc_worker_server(
    *,
    host: str = "0.0.0.0",
    port: int = DEFAULT_LANGCHAIN_RPC_PORT,
    node_id: str = "unknown-node",
) -> SimpleXMLRPCServer:
    server = _ThreadedXmlRpcServer((host, int(port)), allow_none=True, logRequests=False)
    worker = LangChainRpcWorker(node_id=node_id)

    def _shutdown_server() -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    worker.set_shutdown_callback(_shutdown_server)
    server.register_instance(worker, allow_dotted_names=False)
    server.register_introspection_functions()
    return server


def serve_langchain_rpc_worker(
    *,
    host: str = "0.0.0.0",
    port: int = DEFAULT_LANGCHAIN_RPC_PORT,
    node_id: str = "unknown-node",
) -> None:
    server = create_langchain_rpc_worker_server(host=host, port=port, node_id=node_id)
    try:
        server.serve_forever()
    finally:
        server.server_close()


class LangChainRpcClusterClient:
    def __init__(
        self,
        *,
        endpoints: tuple[str, ...] | list[str],
        request_timeout_s: float = 300.0,
    ) -> None:
        normalized = tuple(_normalize_endpoint(endpoint) for endpoint in endpoints)
        if not normalized:
            raise ValueError("langchain_rpc requires at least one endpoint")
        self._endpoints = normalized
        self._request_timeout_s = float(request_timeout_s)
        self._session_lock = threading.Lock()
        self._session_assignments: dict[str, str] = {}
        self._round_robin_index = 0
        self._run_id: str | None = None

    @property
    def endpoints(self) -> tuple[str, ...]:
        return self._endpoints

    def _call(self, endpoint: str, method_name: str, *args: Any) -> Any:
        proxy = ServerProxy(
            endpoint,
            allow_none=True,
            transport=_TimeoutTransport(self._request_timeout_s),
        )
        method = getattr(proxy, method_name)
        return method(*args)

    def ping_all(self) -> list[dict[str, Any]]:
        return [dict(self._call(endpoint, "ping")) for endpoint in self._endpoints]

    def setup_run(self, run_id: str, run_config: dict[str, Any]) -> None:
        self._run_id = str(run_id)
        with self._session_lock:
            self._session_assignments.clear()
            self._round_robin_index = 0
        for endpoint in self._endpoints:
            self._call(endpoint, "setup_run", self._run_id, run_config)

    def _assign_endpoint(self, session_key: str, *, sticky: bool) -> str:
        with self._session_lock:
            if sticky and session_key in self._session_assignments:
                return self._session_assignments[session_key]
            endpoint = self._endpoints[self._round_robin_index % len(self._endpoints)]
            self._round_robin_index += 1
            if sticky:
                self._session_assignments[session_key] = endpoint
            return endpoint

    def process_item(
        self,
        item: dict[str, Any],
        *,
        session_key: str,
        sticky_session: bool,
    ) -> dict[str, Any]:
        if self._run_id is None:
            raise RuntimeError("langchain_rpc cluster client has no active run")
        endpoint = self._assign_endpoint(session_key, sticky=sticky_session)
        return dict(self._call(endpoint, "process_item", self._run_id, item))

    def teardown_run(self) -> None:
        if self._run_id is None:
            return
        try:
            for endpoint in self._endpoints:
                self._call(endpoint, "teardown_run", self._run_id)
        finally:
            self._run_id = None
            with self._session_lock:
                self._session_assignments.clear()
                self._round_robin_index = 0


__all__ = [
    "DEFAULT_LANGCHAIN_RPC_PORT",
    "LangChainRpcClusterClient",
    "LangChainRpcWorker",
    "create_langchain_rpc_worker_server",
    "serve_langchain_rpc_worker",
]
