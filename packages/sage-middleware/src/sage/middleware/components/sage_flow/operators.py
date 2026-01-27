"""
SageFlow Operators for SAGE Pipeline Integration
=================================================

This module provides operators that integrate SageFlow's vector stream processing
capabilities into SAGE's DataStream pipeline.

Architecture:
    SAGE Source → SAGE Map (embedding) → SageFlowJoinOperator → SAGE Sink
                                              ↓
                                    SageFlow Engine (C++)
                                    - Join with document vectors
                                    - Similarity filtering
                                    - Real-time aggregation

Key Classes:
    - SageFlowJoinOperator: MapFunction that wraps SageFlow join pipeline
    - SageFlowVectorSource: SourceFunction that feeds from SageFlow output

Example:
    ```python
    from sage.kernel.api import LocalEnvironment
    from sage.middleware.components.sage_flow.operators import SageFlowJoinOperator

    # Create SAGE environment
    env = LocalEnvironment()

    # Create SageFlow join operator with pre-indexed documents
    flow_op = SageFlowJoinOperator(
        dim=128,
        doc_vectors=doc_embeddings,     # Pre-computed document vectors
        doc_ids=doc_ids,                # Document IDs
        similarity_threshold=0.7,
        join_method="bruteforce_lazy",
    )

    # Build SAGE pipeline with SageFlow as middle component
    (
        env.from_collection(queries)
        .map(EmbeddingFunction)          # SAGE upstream: compute embeddings
        .map(flow_op)                    # SageFlow: vector join
        .map(ContextAggregator)          # SAGE downstream: aggregate results
        .sink(ResponseSink)              # SAGE sink: output
    )

    env.execute()
    ```
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

import numpy as np

from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.source_function import SourceFunction

if TYPE_CHECKING:
    from sage_flow import SimpleStreamSource, Stream, StreamEnvironment


@dataclass
class VectorJoinResult:
    """Result from SageFlow join operation."""

    query_id: int
    query_vector: np.ndarray
    matched_doc_ids: list[int] = field(default_factory=list)
    matched_vectors: list[np.ndarray] = field(default_factory=list)
    similarity_scores: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SageFlowJoinOperator(MapFunction):
    """
    SAGE MapFunction that wraps SageFlow's vector join pipeline.

    This operator bridges SAGE's DataStream with SageFlow's C++ vector processing.
    It maintains a persistent SageFlow pipeline with pre-indexed document vectors,
    and performs real-time similarity joins on incoming query vectors.

    Data Flow:
        1. SAGE upstream sends dict with 'embedding' field
        2. This operator feeds embedding to SageFlow query stream
        3. SageFlow performs join with doc stream (pre-indexed)
        4. Results collected via callback and returned to SAGE downstream

    Args:
        dim: Vector dimension
        doc_vectors: Pre-computed document embeddings (N x dim numpy array)
        doc_ids: Document IDs corresponding to doc_vectors
        similarity_threshold: Minimum similarity for join match (0.0 - 1.0)
        join_method: Join algorithm ("bruteforce_lazy", "ivf", "hnsw")
        window_size_ms: Time window for streaming join (default: 10000ms)
        parallelism: SageFlow parallelism (default: 1)

    Input:
        dict with keys:
            - 'id': Query ID (int or str)
            - 'embedding': Query vector (list or numpy array)
            - Other fields passed through to output

    Output:
        dict with keys:
            - All input fields (passed through)
            - 'matched_docs': List of matched document IDs
            - 'matched_vectors': List of matched document vectors
            - 'similarity_scores': List of similarity scores
            - 'join_timestamp': Timestamp of join operation
    """

    def __init__(
        self,
        dim: int,
        doc_vectors: np.ndarray | list[list[float]],
        doc_ids: list[int] | None = None,
        similarity_threshold: float = 0.7,
        join_method: str = "bruteforce_lazy",
        window_size_ms: int = 10000,
        parallelism: int = 1,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.dim = dim
        self.similarity_threshold = similarity_threshold
        self.join_method = join_method
        self.window_size_ms = window_size_ms
        self.parallelism = parallelism

        # Convert doc_vectors to numpy array
        if not isinstance(doc_vectors, np.ndarray):
            doc_vectors = np.array(doc_vectors, dtype=np.float32)
        self.doc_vectors = doc_vectors.astype(np.float32)

        # Generate doc_ids if not provided
        if doc_ids is None:
            doc_ids = list(range(len(self.doc_vectors)))
        self.doc_ids = doc_ids

        # SageFlow components (lazy init)
        self._env: StreamEnvironment | None = None
        self._left_source: SimpleStreamSource | None = None
        self._right_source: SimpleStreamSource | None = None
        self._pipeline: Stream | None = None
        self._initialized = False
        self._lock = threading.Lock()

        # Result collection
        # Store pairs: (left_uid, right_uid, similarity)
        self._result_queue: queue.Queue[tuple[int, int, float]] = queue.Queue()

    def _init_sageflow(self) -> None:
        """Initialize SageFlow pipeline lazily."""
        if self._initialized:
            return

        # Import SageFlow bindings
        from sage_flow import SimpleStreamSource, StreamEnvironment

        self._env = StreamEnvironment()

        # Create query source (will receive live queries)
        self._query_source = SimpleStreamSource("query_stream")

        # Create document source and pre-populate
        self._doc_source = SimpleStreamSource("doc_stream")
        current_ts = int(time.time() * 1000)
        for i, (doc_id, vec) in enumerate(zip(self.doc_ids, self.doc_vectors)):
            self._doc_source.addRecord(int(doc_id), current_ts + i, vec)

        # Configure join parameters via setters
        self._query_source.setJoinMethod(self.join_method)
        self._query_source.setJoinSimilarityThreshold(self.similarity_threshold)

        # Build join pipeline with simple join_func
        # Note: Similarity calculation is done in C++ engine, join_func just combines vectors
        def join_func(left_vec: np.ndarray, right_vec: np.ndarray) -> np.ndarray:
            # Simply concatenate vectors - similarity already filtered by C++ engine
            return np.concatenate([left_vec, right_vec])

        self._pipeline = self._query_source.join(
            self._doc_source,
            join_func,
            dim=self.dim,
            parallelism=self.parallelism,
        )

        # Set up sink to collect results
        def collect_result(uid: int, ts: int) -> None:
            self._result_queue.put((uid, ts))

        self._pipeline.writeSink("sage_collector", collect_result)

        # Add to environment
        self._env.addStream(self._query_source)
        self._env.addStream(self._doc_source)

        self._initialized = True

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute SageFlow join on input data.

        Args:
            data: Dict containing 'id' and 'embedding' fields

        Returns:
            Dict with original fields plus join results
        """
        with self._lock:
            self._init_sageflow()

        # Extract query info
        query_id = data.get("id", 0)
        if isinstance(query_id, str):
            query_id = hash(query_id) % (2**31)

        embedding = data.get("embedding")
        if embedding is None:
            # Pass through if no embedding
            return {**data, "matched_docs": [], "similarity_scores": []}

        if not isinstance(embedding, np.ndarray):
            embedding = np.array(embedding, dtype=np.float32)
        embedding = embedding.astype(np.float32)

        # Add query to SageFlow
        current_ts = int(time.time() * 1000)
        with self._lock:
            self._current_query_id = query_id
            self._query_source.addRecord(query_id, current_ts, embedding)

            # Execute SageFlow pipeline
            self._env.execute()

        # Collect results (with timeout)
        matched_docs = []
        matched_vectors = []
        similarity_scores = []

        try:
            while True:
                uid, ts = self._result_queue.get_nowait()
                matched_docs.append(uid)
                # Find corresponding vector and compute similarity
                for i, doc_id in enumerate(self.doc_ids):
                    if doc_id == uid:
                        doc_vec = self.doc_vectors[i]
                        matched_vectors.append(doc_vec.tolist())
                        # Compute cosine similarity
                        sim = float(
                            np.dot(embedding, doc_vec)
                            / (np.linalg.norm(embedding) * np.linalg.norm(doc_vec) + 1e-8)
                        )
                        similarity_scores.append(sim)
                        break
        except queue.Empty:
            pass

        # Build output (pass through all original fields)
        result = {
            **data,
            "matched_docs": matched_docs,
            "matched_vectors": matched_vectors,
            "similarity_scores": similarity_scores,
            "join_timestamp": current_ts,
        }

        return result


class SageFlowAggregationOperator(MapFunction):
    """
    SAGE MapFunction for query aggregation using SageFlow.

    This operator groups similar queries together using SageFlow's join capability,
    enabling batch processing of semantically similar requests.

    Use Case: Similar Query Aggregation for LLM inference
        - Multiple users ask similar questions
        - Group them and process once
        - Distribute result to all similar queries

    Args:
        dim: Vector dimension
        similarity_threshold: Threshold for query grouping (0.0 - 1.0)
        aggregation_window_ms: Time window for aggregation
        min_group_size: Minimum queries to form a group

    Input:
        dict with 'id', 'embedding', 'query' fields

    Output:
        dict with:
            - 'is_representative': True if this query is group representative
            - 'group_ids': List of query IDs in the same group
            - 'group_queries': List of query texts in the group
    """

    def __init__(
        self,
        dim: int,
        similarity_threshold: float = 0.85,
        aggregation_window_ms: int = 5000,
        min_group_size: int = 1,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.dim = dim
        self.similarity_threshold = similarity_threshold
        self.aggregation_window_ms = aggregation_window_ms
        self.min_group_size = min_group_size

        # Query buffer for aggregation
        self._query_buffer: list[dict[str, Any]] = []
        self._buffer_lock = threading.Lock()
        self._buffer_start_time: float | None = None

        # SageFlow components
        self._env = None
        self._source = None
        self._initialized = False

    def _init_sageflow(self) -> None:
        """Initialize SageFlow for self-join (query-to-query)."""
        if self._initialized:
            return

        from sage_flow import SimpleStreamSource, StreamEnvironment

        self._env = StreamEnvironment()
        self._source = SimpleStreamSource("query_aggregation_stream")
        self._source.setJoinMethod("bruteforce_lazy")
        self._source.setJoinSimilarityThreshold(self.similarity_threshold)
        self._initialized = True

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process query and return aggregation result."""
        with self._buffer_lock:
            self._init_sageflow()

            current_time = time.time()
            if self._buffer_start_time is None:
                self._buffer_start_time = current_time

            # Add to buffer
            self._query_buffer.append(data)

            # Check if window expired
            window_expired = (current_time - self._buffer_start_time) * 1000 >= self.aggregation_window_ms

            if not window_expired:
                # Not ready to aggregate yet, mark as pending
                return {
                    **data,
                    "is_representative": False,
                    "group_ids": [],
                    "group_queries": [],
                    "aggregation_pending": True,
                }

            # Perform aggregation
            queries = self._query_buffer.copy()
            self._query_buffer.clear()
            self._buffer_start_time = None

        # Find similar query groups
        groups = self._find_similar_groups(queries)

        # Find which group this query belongs to
        query_id = data.get("id")
        for group in groups:
            if any(q.get("id") == query_id for q in group):
                representative = group[0]  # First query is representative
                is_rep = representative.get("id") == query_id

                return {
                    **data,
                    "is_representative": is_rep,
                    "group_ids": [q.get("id") for q in group],
                    "group_queries": [q.get("query", "") for q in group],
                    "group_size": len(group),
                    "aggregation_pending": False,
                }

        # Not in any group (shouldn't happen)
        return {
            **data,
            "is_representative": True,
            "group_ids": [query_id],
            "group_queries": [data.get("query", "")],
            "group_size": 1,
            "aggregation_pending": False,
        }

    def _find_similar_groups(
        self, queries: list[dict[str, Any]]
    ) -> list[list[dict[str, Any]]]:
        """Find groups of similar queries using cosine similarity."""
        if not queries:
            return []

        # Extract embeddings
        embeddings = []
        for q in queries:
            emb = q.get("embedding")
            if emb is not None:
                if not isinstance(emb, np.ndarray):
                    emb = np.array(emb, dtype=np.float32)
                embeddings.append(emb)
            else:
                embeddings.append(np.zeros(self.dim, dtype=np.float32))

        embeddings = np.array(embeddings)

        # Compute pairwise cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8
        normalized = embeddings / norms
        similarity_matrix = np.dot(normalized, normalized.T)

        # Group by similarity (simple greedy clustering)
        n = len(queries)
        assigned = [False] * n
        groups = []

        for i in range(n):
            if assigned[i]:
                continue

            group = [queries[i]]
            assigned[i] = True

            for j in range(i + 1, n):
                if not assigned[j] and similarity_matrix[i, j] >= self.similarity_threshold:
                    group.append(queries[j])
                    assigned[j] = True

            if len(group) >= self.min_group_size:
                groups.append(group)

        return groups


class SageFlowContextSource(SourceFunction):
    """
    SAGE SourceFunction that wraps SageFlow output as a data source.

    This allows SageFlow pipeline output to be consumed by SAGE DataStream
    as if it were a regular SAGE source.

    Use Case: SageFlow as upstream source for SAGE pipeline
        - SageFlow processes vector streams
        - Results feed into SAGE for further processing

    Args:
        sageflow_service: SageFlowService instance
        output_format: Format of output data ("dict" or "tuple")
    """

    def __init__(
        self,
        dim: int = 128,
        output_format: str = "dict",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.dim = dim
        self.output_format = output_format

        from sage.middleware.components.sage_flow import SageFlowService

        self._service = SageFlowService(dim=dim)
        self._output_queue: queue.Queue = queue.Queue()
        self._setup_sink()

    def _setup_sink(self) -> None:
        """Set up SageFlow sink to feed output queue."""

        def sink_callback(uid: int, ts: int) -> None:
            if self.output_format == "dict":
                self._output_queue.put({"id": uid, "timestamp": ts})
            else:
                self._output_queue.put((uid, ts))

        self._service.set_sink(sink_callback, "sage_source_sink")

    def push(self, uid: int, vec: np.ndarray) -> None:
        """Push a vector to SageFlow for processing."""
        self._service.push(uid, vec)

    def execute(self, data=None):
        """Execute source - return next available output or None."""
        # Run SageFlow to process any pending inputs
        self._service.run()

        try:
            return self._output_queue.get_nowait()
        except queue.Empty:
            return None


# Convenience type aliases
SageFlowJoin = SageFlowJoinOperator
SageFlowAggregation = SageFlowAggregationOperator
