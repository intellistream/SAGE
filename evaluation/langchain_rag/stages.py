from __future__ import annotations

import hashlib
import json
import math
import re
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np

from sage.foundation import BatchFunction, MapFunction, SinkFunction

from .dependencies import (
    AIMessage,
    BaseMessage,
    ChatPromptTemplate,
    Document,
    Embeddings,
    HumanMessage,
    InMemoryChatMessageHistory,
    OpenAI,
    RecursiveCharacterTextSplitter,
    RunnableLambda,
    faiss,
    init_chat_model,
    require_faiss,
    require_langchain,
    require_openai,
)
from .metrics import build_run_summary, build_stage_reports
from .output import write_json


def _stable_hash(value: str) -> int:
    digest = hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False)


def _tokenize(text: str) -> list[str]:
    lowered = text.lower()
    latin_tokens = re.findall(r"[a-z0-9_]{2,}", lowered)
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", text)
    cjk_bigrams = ["".join(cjk_chars[index : index + 2]) for index in range(len(cjk_chars) - 1)]
    return latin_tokens + cjk_chars + cjk_bigrams


def _normalize_vector(values: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0.0:
        return values
    return [value / norm for value in values]


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split())) if text.strip() else 0


def _normalize_openai_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if not normalized.endswith("/v1"):
        normalized = f"{normalized}/v1"
    return normalized


def _truncate_for_embedding(text: str, *, token_limit: int = 96, char_limit: int = 768) -> str:
    normalized = " ".join(str(text).split())
    if len(normalized) > char_limit:
        normalized = normalized[:char_limit]
    tokens = normalized.split()
    if len(tokens) > token_limit:
        normalized = " ".join(tokens[:token_limit])
    return normalized


def _truncate_for_generation(text: str, *, token_limit: int, char_limit: int) -> str:
    normalized = " ".join(str(text).split())
    if len(normalized) > char_limit:
        normalized = normalized[:char_limit]
    tokens = normalized.split()
    if len(tokens) > token_limit:
        normalized = " ".join(tokens[:token_limit])
    return normalized


def _compress_generation_question(question: str) -> str:
    source = str(question)
    lowered = source.lower()
    focus_markers = ["follow_up_question", "user_query", "query:", "question:"]
    start = 0
    for marker in focus_markers:
        marker_index = lowered.rfind(marker)
        if marker_index >= 0:
            start = max(start, marker_index)
    focused = source[start:] if start > 0 else source
    return _truncate_for_generation(focused, token_limit=128, char_limit=1536)


def _compress_generation_context(retrieved_context: str, memory_context: str) -> tuple[str, str]:
    compact_retrieval = _truncate_for_generation(
        retrieved_context, token_limit=384, char_limit=3072
    )
    compact_memory = _truncate_for_generation(memory_context, token_limit=128, char_limit=1024)
    return compact_retrieval, compact_memory


def _normalize_faiss_matrix(matrix: np.ndarray) -> np.ndarray:
    normalized = np.asarray(matrix, dtype="float32")
    if normalized.size == 0:
        return normalized
    assert faiss is not None
    faiss.normalize_L2(normalized)
    return normalized


def _build_split_documents(
    documents: list[dict[str, str]],
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", "。", " ", ""],
    )
    base_documents = [
        Document(
            page_content=document["text"],
            metadata={
                "source_id": document["source_id"],
                "title": document["title"],
            },
        )
        for document in documents
    ]
    split_documents = splitter.split_documents(base_documents)
    for index, document in enumerate(split_documents, start=1):
        document.metadata["chunk_id"] = f"chunk-{index}"
    return split_documents


def _resolve_embeddings(
    *,
    embedding_dimensions: int,
    embedding_model: str | None,
    embedding_base_url: str | None,
    embedding_api_key: str,
) -> Embeddings:
    if embedding_model and embedding_base_url:
        return RemoteOpenAIEmbeddings(
            model=embedding_model,
            base_url=embedding_base_url,
            api_key=embedding_api_key,
        )
    return KeywordHashEmbeddings(embedding_dimensions)


def build_offline_faiss_index(
    *,
    index_dir: str | Path,
    documents: list[dict[str, str]],
    chunk_size: int,
    chunk_overlap: int,
    embedding_dimensions: int = 256,
    embedding_model: str | None = None,
    embedding_base_url: str | None = None,
    embedding_api_key: str | None = None,
) -> dict[str, Any]:
    require_langchain()
    require_faiss()
    assert faiss is not None

    started = time.perf_counter()
    resolved_index_dir = Path(index_dir)
    resolved_index_dir.mkdir(parents=True, exist_ok=True)

    split_documents = _build_split_documents(
        documents,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    embeddings = _resolve_embeddings(
        embedding_dimensions=embedding_dimensions,
        embedding_model=embedding_model,
        embedding_base_url=embedding_base_url,
        embedding_api_key=embedding_api_key or "EMPTY",
    )
    chunk_texts = [document.page_content for document in split_documents]
    matrix = _normalize_faiss_matrix(
        np.asarray(embeddings.embed_documents(chunk_texts), dtype="float32")
    )
    if matrix.ndim != 2 or matrix.shape[0] != len(split_documents):
        raise RuntimeError("offline FAISS build produced invalid embedding matrix")

    index = faiss.IndexFlatIP(int(matrix.shape[1]))
    index.add(matrix)
    faiss.write_index(index, str(resolved_index_dir / "index.faiss"))

    records = [
        {
            "page_content": document.page_content,
            "metadata": {key: str(value) for key, value in dict(document.metadata).items()},
        }
        for document in split_documents
    ]
    metadata = {
        "backend": "faiss_offline",
        "embedding_backend": (
            f"openai-compatible-embeddings:{embedding_model}"
            if embedding_model and embedding_base_url
            else f"keyword-hash:{embedding_dimensions}"
        ),
        "document_count": len(documents),
        "chunk_count": len(records),
        "index_build_ms": round((time.perf_counter() - started) * 1000.0, 3),
    }
    (resolved_index_dir / "records.json").write_text(
        json.dumps({"metadata": metadata, "records": records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return metadata


def load_offline_faiss_index(
    index_dir: str | Path,
) -> tuple[Any, list[dict[str, Any]], dict[str, Any]]:
    require_faiss()
    assert faiss is not None

    resolved_index_dir = Path(index_dir)
    index = faiss.read_index(str(resolved_index_dir / "index.faiss"))
    payload = json.loads((resolved_index_dir / "records.json").read_text(encoding="utf-8"))
    return index, list(payload.get("records") or []), dict(payload.get("metadata") or {})


def _message_role(message: BaseMessage) -> str:
    if isinstance(message, HumanMessage):
        return "user"
    if isinstance(message, AIMessage):
        return "assistant"
    return "message"


def _format_history(messages: list[BaseMessage]) -> str:
    if not messages:
        return "No previous turns."
    return "\n".join(f"{_message_role(message)}: {message.content}" for message in messages)


def _extract_section(text: str, start_label: str, end_label: str | None) -> str:
    start = text.find(start_label)
    if start < 0:
        return ""
    start += len(start_label)
    if end_label is None:
        return text[start:].strip()
    end = text.find(end_label, start)
    if end < 0:
        return text[start:].strip()
    return text[start:end].strip()


def _select_support_snippets(
    question: str, citations: list[dict[str, Any]], limit: int = 2
) -> list[str]:
    question_terms = set(_tokenize(question))
    scored: list[tuple[int, str]] = []
    for citation in citations:
        excerpt = str(citation.get("excerpt") or "").strip()
        if not excerpt:
            continue
        overlap = len(question_terms & set(_tokenize(excerpt)))
        scored.append((overlap, excerpt))
    scored.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
    return [excerpt for _, excerpt in scored[:limit]]


class KeywordHashEmbeddings(Embeddings):
    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions

    def _embed(self, text: str) -> list[float]:
        values = [0.0] * self.dimensions
        for token in _tokenize(text):
            index = _stable_hash(token) % self.dimensions
            sign = -1.0 if _stable_hash(f"sign:{token}") % 2 else 1.0
            values[index] += sign
        return _normalize_vector(values)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class RemoteOpenAIEmbeddings(Embeddings):
    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key: str = "EMPTY",
    ) -> None:
        require_openai()
        assert OpenAI is not None
        self.model = model
        self.base_url = _normalize_openai_base_url(base_url)
        self.client = OpenAI(base_url=self.base_url, api_key=api_key)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        response = self.client.embeddings.create(
            model=self.model,
            input=[_truncate_for_embedding(text)],
        )
        return list(response.data[0].embedding)


class WorkloadQuerySource(BatchFunction):
    def __init__(
        self,
        query_items: list[dict[str, Any]],
        request_rate_qps: float | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.query_items = [dict(item) for item in query_items]
        if request_rate_qps is not None and request_rate_qps <= 0.0:
            raise ValueError("request_rate_qps must be positive when provided")
        self.request_rate_qps = float(request_rate_qps) if request_rate_qps is not None else None
        self._items: list[dict[str, Any]] | None = None
        self._index = 0
        self._source_load_ms = 0.0
        self._loaded_at: float | None = None
        self._request_interval_s = 1.0 / self.request_rate_qps if self.request_rate_qps else None
        self._first_emitted_at: float | None = None
        self._last_emitted_at: float | None = None
        self._total_pacing_sleep_s = 0.0

    def _load_items(self) -> list[dict[str, Any]]:
        started = time.perf_counter()
        items = [dict(item) for item in self.query_items]
        self._source_load_ms = round((time.perf_counter() - started) * 1000.0, 3)
        self._loaded_at = time.perf_counter()
        return items

    def _pace_before_emit(self, item_index: int) -> float:
        if self._request_interval_s is None or self._loaded_at is None:
            return 0.0
        target_emit_at = self._loaded_at + (item_index * self._request_interval_s)
        remaining = target_emit_at - time.perf_counter()
        if remaining <= 0.0:
            return 0.0
        time.sleep(remaining)
        self._total_pacing_sleep_s += remaining
        return remaining

    def execute(self) -> dict[str, Any] | None:
        if self._items is None:
            self._items = self._load_items()
            self._index = 0

        if self._index >= len(self._items):
            return None

        pacing_sleep_s = self._pace_before_emit(self._index)
        started = time.perf_counter()
        emitted_at = time.perf_counter()
        payload = dict(self._items[self._index])
        self._index += 1
        if self._first_emitted_at is None:
            self._first_emitted_at = emitted_at
        self._last_emitted_at = emitted_at
        payload["source_emitted_at"] = emitted_at
        payload["source_metrics"] = {
            "source_load_ms": self._source_load_ms,
            "query_count": len(self._items),
            "target_request_rate_qps": self.request_rate_qps,
            "target_inter_request_delay_ms": round((self._request_interval_s or 0.0) * 1000.0, 3),
            "pacing_sleep_ms": round(pacing_sleep_s * 1000.0, 3),
            "total_pacing_sleep_ms": round(self._total_pacing_sleep_s * 1000.0, 3),
            "source_dispatch_offset_ms": round(
                (emitted_at - (self._loaded_at or emitted_at)) * 1000.0,
                3,
            ),
        }
        payload["latency_ms"] = dict(payload.get("latency_ms") or {})
        payload["latency_ms"]["source"] = round((time.perf_counter() - started) * 1000.0, 3)
        return payload


class LangChainRetrievalStage(MapFunction):
    def __init__(
        self,
        documents: list[dict[str, str]],
        enable_retrieval: bool,
        top_k: int = 3,
        chunk_size: int = 320,
        chunk_overlap: int = 48,
        embedding_dimensions: int = 256,
        embedding_model: str | None = None,
        embedding_base_url: str | None = None,
        embedding_api_key: str | None = None,
        offline_index_dir: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.documents = [dict(item) for item in documents]
        self.enable_retrieval = enable_retrieval
        self.top_k = top_k
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_dimensions = embedding_dimensions
        self.embedding_model = embedding_model
        self.embedding_base_url = embedding_base_url
        self.embedding_api_key = embedding_api_key or "EMPTY"
        self.offline_index_dir = Path(offline_index_dir) if offline_index_dir else None
        self._faiss_index: Any | None = None
        self._faiss_records: list[dict[str, Any]] = []
        self._embeddings = _resolve_embeddings(
            embedding_dimensions=self.embedding_dimensions,
            embedding_model=self.embedding_model,
            embedding_base_url=self.embedding_base_url,
            embedding_api_key=self.embedding_api_key,
        )
        self._index_build_ms = 0.0
        self._document_count = len(self.documents)
        self._chunk_count = 0
        self._embedding_backend = (
            f"openai-compatible-embeddings:{self.embedding_model}"
            if self.embedding_model and self.embedding_base_url
            else f"keyword-hash:{self.embedding_dimensions}"
        )
        self._index_backend = "faiss_offline"
        self._index_lock = threading.Lock()
        if self.enable_retrieval:
            self._load_index()

    def _load_index(self) -> None:
        if not self.enable_retrieval or self._faiss_index is not None:
            return
        with self._index_lock:
            if not self.enable_retrieval or self._faiss_index is not None:
                return
            if self.offline_index_dir is None:
                raise RuntimeError(
                    "offline FAISS index directory is required when retrieval is enabled"
                )
            index, records, metadata = load_offline_faiss_index(self.offline_index_dir)
            self._faiss_index = index
            self._faiss_records = records
            self._document_count = int(metadata.get("document_count") or self._document_count)
            self._chunk_count = int(metadata.get("chunk_count") or len(records))
            self._index_build_ms = round(float(metadata.get("index_build_ms") or 0.0), 3)
            self._embedding_backend = str(
                metadata.get("embedding_backend") or self._embedding_backend
            )
            self._index_backend = str(metadata.get("backend") or self._index_backend)

    def execute(self, item: dict[str, Any]) -> dict[str, Any]:
        payload = dict(item)
        payload["latency_ms"] = dict(payload.get("latency_ms") or {})
        if not self.enable_retrieval:
            payload["retrieval"] = {
                "enabled": False,
                "top_k": self.top_k,
                "retrieved_count": 0,
                "document_count": self._document_count,
                "chunk_count": 0,
                "index_build_ms": 0.0,
                "embedding_backend": self._embedding_backend,
                "index_backend": self._index_backend,
            }
            payload["citations"] = []
            payload["retrieved_context"] = "Retrieval disabled for this variant."
            payload["latency_ms"]["retrieval"] = 0.0
            return payload

        self._load_index()
        assert self._faiss_index is not None

        started = time.perf_counter()
        question = str(payload.get("question") or "")
        query_matrix = _normalize_faiss_matrix(
            np.asarray([self._embeddings.embed_query(question)], dtype="float32")
        )
        limit = min(self.top_k, len(self._faiss_records))
        if limit <= 0:
            indices = np.empty((1, 0), dtype="int64")
        else:
            _, indices = self._faiss_index.search(query_matrix, limit)
        retrieval_ms = round((time.perf_counter() - started) * 1000.0, 3)

        citations: list[dict[str, Any]] = []
        for rank, record_index in enumerate(indices[0], start=1):
            if int(record_index) < 0:
                continue
            record = self._faiss_records[int(record_index)]
            metadata = dict(record.get("metadata") or {})
            excerpt = " ".join(str(record.get("page_content") or "").split())
            if len(excerpt) > 220:
                excerpt = f"{excerpt[:217].rstrip()}..."
            citations.append(
                {
                    "rank": rank,
                    "source_id": str(metadata.get("source_id") or f"doc-{rank}"),
                    "title": str(metadata.get("title") or "document"),
                    "chunk_id": str(metadata.get("chunk_id") or f"chunk-{rank}"),
                    "excerpt": excerpt,
                }
            )

        payload["retrieval"] = {
            "enabled": True,
            "top_k": self.top_k,
            "retrieved_count": len(citations),
            "document_count": self._document_count,
            "chunk_count": self._chunk_count,
            "index_build_ms": self._index_build_ms,
            "embedding_backend": self._embedding_backend,
            "index_backend": self._index_backend,
        }
        payload["citations"] = citations
        payload["retrieved_context"] = (
            "\n\n".join(
                f"[{citation['rank']}] {citation['source_id']} ({citation['title']})\n{citation['excerpt']}"
                for citation in citations
            )
            or "No retrieved context."
        )
        payload["latency_ms"]["retrieval"] = retrieval_ms
        return payload


class LangChainMemoryStage(MapFunction):
    def __init__(self, max_turns: int = 4, enable_memory: bool = True, **kwargs) -> None:
        super().__init__(**kwargs)
        self.max_turns = max_turns
        self.enable_memory = enable_memory
        self._histories: dict[str, InMemoryChatMessageHistory] = {}
        self._history_lock = threading.Lock()

    def execute(self, item: dict[str, Any]) -> dict[str, Any]:
        payload = dict(item)
        payload["latency_ms"] = dict(payload.get("latency_ms") or {})
        if not self.enable_memory:
            payload["memory_history"] = None
            payload["memory"] = {
                "enabled": False,
                "session_id": str(payload.get("session_id") or "default-session"),
                "max_turns": self.max_turns,
                "turns_before": 0,
                "turns_after": 0,
            }
            payload["memory_context"] = "Memory disabled for this variant."
            payload["latency_ms"]["memory"] = 0.0
            return payload

        require_langchain()
        started = time.perf_counter()
        session_id = str(payload.get("session_id") or "default-session")
        with self._history_lock:
            history = self._histories.setdefault(session_id, InMemoryChatMessageHistory())
        payload["memory_history"] = history
        payload["memory"] = {
            "enabled": True,
            "session_id": session_id,
            "max_turns": self.max_turns,
        }
        payload["latency_ms"]["memory"] = round((time.perf_counter() - started) * 1000.0, 3)
        return payload


class LangChainGenerationStage(MapFunction):
    def __init__(
        self,
        variant_name: str,
        model: str | None = None,
        model_provider: str | None = None,
        generation_base_url: str | None = None,
        generation_api_key: str | None = None,
        temperature: float = 0.0,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        require_langchain()
        self.variant_name = variant_name
        self.model = model
        self.model_provider = model_provider
        self.generation_base_url = generation_base_url
        self.generation_api_key = generation_api_key or "EMPTY"
        self.temperature = temperature
        self.system_instruction = (
            "You are a concise RAG assistant. Use retrieved context first and memory second. "
            "If evidence is missing, say so plainly."
        )
        self.user_template = (
            "Question:\n{question}\n\nRetrieved context:\n{retrieved_context}\n\n"
            "Conversation memory:\n{memory_context}\n\nProvide one concise answer and cite the "
            "retrieved chunks you used."
        )
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    self.system_instruction,
                ),
                (
                    "human",
                    self.user_template,
                ),
            ]
        )
        self._heuristic_chain = self.prompt | RunnableLambda(self._heuristic_response)
        self._chat_model = None
        self._openai_client = None
        self._backend_name = "heuristic-local"
        self._fallback_reason: str | None = None
        if self.model and self.generation_base_url:
            try:
                require_openai()
                assert OpenAI is not None
                self._openai_client = OpenAI(
                    base_url=_normalize_openai_base_url(self.generation_base_url),
                    api_key=self.generation_api_key,
                )
                self._backend_name = f"openai-compatible:{self.model}"
            except Exception as exc:  # noqa: BLE001
                self._fallback_reason = str(exc)
                self._openai_client = None
                self._backend_name = f"heuristic-fallback:openai-compatible:{self.model}"
        elif self.model and self.model_provider:
            try:
                self._chat_model = init_chat_model(
                    self.model,
                    model_provider=self.model_provider,
                    temperature=self.temperature,
                )
                self._backend_name = f"{self.model_provider}:{self.model}"
            except Exception as exc:  # noqa: BLE001
                self._fallback_reason = str(exc)
                self._chat_model = None
                self._backend_name = f"heuristic-fallback:{self.model_provider}:{self.model}"

    def _heuristic_response(self, prompt_value: Any) -> str:
        prompt_text = (
            prompt_value.to_string() if hasattr(prompt_value, "to_string") else str(prompt_value)
        )
        question = _extract_section(prompt_text, "Question:", "Retrieved context:")
        context = _extract_section(prompt_text, "Retrieved context:", "Conversation memory:")
        memory = _extract_section(prompt_text, "Conversation memory:", "Provide one concise answer")

        cited_ids = re.findall(r"\[(\d+)\]", context)
        selected = _select_support_snippets(
            question,
            [
                {"excerpt": block.strip()}
                for block in re.split(r"\n\s*\n", context)
                if block.strip()
            ],
        )

        evidence = " ".join(selected).strip()
        answer = evidence or "I do not have enough retrieved evidence to answer reliably."
        if (
            memory
            and memory not in {"No previous turns.", "Memory disabled for this variant."}
            and re.search(
                r"earlier|previous|before|follow-up|memory|it|that|those|based on",
                question.lower(),
            )
        ):
            answer += " Memory keeps prior turns available so follow-up questions can reuse earlier intent."
        citation_text = ", ".join(f"[{identifier}]" for identifier in cited_ids[:2]) or "[1]"
        return f"{answer} Variant: {self.variant_name}. Citations: {citation_text}."

    def _invoke_model(self, prompt_inputs: dict[str, Any]) -> str:
        if self._openai_client is not None:
            try:
                response = self._openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_instruction},
                        {"role": "user", "content": self.user_template.format(**prompt_inputs)},
                    ],
                    temperature=self.temperature,
                )
                return str(response.choices[0].message.content or "")
            except Exception as exc:  # noqa: BLE001
                self._fallback_reason = str(exc)
                self._backend_name = f"heuristic-fallback:openai-compatible:{self.model}"
                self._openai_client = None
                return str(self._heuristic_chain.invoke(prompt_inputs))
        if self._chat_model is None:
            return str(self._heuristic_chain.invoke(prompt_inputs))
        try:
            result = (
                self.prompt
                | self._chat_model
                | RunnableLambda(lambda message: getattr(message, "content", str(message)))
            ).invoke(prompt_inputs)
            return str(result)
        except Exception as exc:  # noqa: BLE001
            self._fallback_reason = str(exc)
            self._backend_name = f"heuristic-fallback:{self.model_provider}:{self.model}"
            self._chat_model = None
            return str(self._heuristic_chain.invoke(prompt_inputs))

    def execute(self, item: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        payload = dict(item)
        payload["latency_ms"] = dict(payload.get("latency_ms") or {})
        history = payload.get("memory_history")
        max_turns = int((payload.get("memory") or {}).get("max_turns") or 4)
        if isinstance(history, InMemoryChatMessageHistory):
            recent_messages = history.messages[-(max_turns * 2) :]
            memory_context = _format_history(recent_messages)
            turns_before = len(history.messages) // 2
        else:
            memory_context = str(payload.get("memory_context") or "No previous turns.")
            turns_before = int((payload.get("memory") or {}).get("turns_before") or 0)

        compact_question = _compress_generation_question(str(payload.get("question") or ""))
        compact_retrieved_context, compact_memory_context = _compress_generation_context(
            str(payload.get("retrieved_context") or "No retrieved context."),
            memory_context,
        )

        prompt_inputs = {
            "question": compact_question,
            "retrieved_context": compact_retrieved_context,
            "memory_context": compact_memory_context,
        }
        answer = self._invoke_model(prompt_inputs)

        if isinstance(history, InMemoryChatMessageHistory):
            history.add_user_message(prompt_inputs["question"])
            history.add_ai_message(answer)
            turns_after = len(history.messages) // 2
        else:
            turns_after = turns_before

        payload["answer"] = answer
        payload["generator_backend"] = self._backend_name
        payload["generator_notes"] = self._fallback_reason
        payload["memory"] = dict(payload.get("memory") or {})
        payload["memory"]["turns_before"] = turns_before
        payload["memory"]["turns_after"] = turns_after
        payload["memory_context"] = compact_memory_context
        payload["generation"] = {
            "prompt_tokens_est": _estimate_tokens(
                f"{prompt_inputs['question']}\n{prompt_inputs['retrieved_context']}\n{prompt_inputs['memory_context']}"
            ),
            "answer_tokens_est": _estimate_tokens(answer),
        }
        payload["latency_ms"]["generation"] = round((time.perf_counter() - started) * 1000.0, 3)
        return payload


class WorkloadMetricsSink(SinkFunction):
    def __init__(self, run_output_dir: str, run_context: dict[str, Any], **kwargs) -> None:
        super().__init__(**kwargs)
        self.run_output_dir = Path(run_output_dir)
        self.run_context = dict(run_context)
        self.items: list[dict[str, Any]] = []
        self._started_at = time.perf_counter()

    def execute(self, item: dict[str, Any]) -> None:
        sink_started = time.perf_counter()
        payload = dict(item)
        payload.pop("memory_history", None)
        payload["latency_ms"] = dict(payload.get("latency_ms") or {})
        payload["latency_ms"]["sink"] = round((time.perf_counter() - sink_started) * 1000.0, 3)
        emitted_at = float(payload.get("source_emitted_at") or time.perf_counter())
        payload["latency_ms"]["end_to_end"] = round((time.perf_counter() - emitted_at) * 1000.0, 3)
        self.items.append(payload)

    def close(self) -> None:
        stage_reports = build_stage_reports(self.items, self.run_context)
        elapsed_s = max(time.perf_counter() - self._started_at, 1e-9)
        summary = build_run_summary(self.items, self.run_context, elapsed_s, stage_reports)

        write_json(
            self.run_output_dir / "query_results.json",
            {
                "run": self.run_context,
                "results": self.items,
            },
        )
        for stage_name, report in stage_reports.items():
            write_json(self.run_output_dir / "stage_metrics" / f"{stage_name}.json", report)
        write_json(self.run_output_dir / "summary.json", summary)


__all__ = [
    "LangChainGenerationStage",
    "LangChainMemoryStage",
    "LangChainRetrievalStage",
    "WorkloadMetricsSink",
    "WorkloadQuerySource",
]
