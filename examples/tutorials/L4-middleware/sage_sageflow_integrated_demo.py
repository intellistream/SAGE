#!/usr/bin/env python3
"""
SAGE + SageFlow Integrated Pipeline Demo
=========================================

This demo shows how to integrate SageFlow as a component within SAGE's DataStream pipeline.
SageFlow handles high-performance vector stream processing in C++, while SAGE manages
the overall pipeline orchestration.

Architecture:
    SAGE Source → SAGE Map (embedding) → SageFlow Join → SAGE Map (LLM) → SAGE Sink

Three Scenarios Demonstrated:
    1. Streaming RAG: Real-time document retrieval for LLM context
    2. Similar Query Aggregation: Group similar queries to reduce LLM calls
    3. Session Semantic State: Maintain conversation context via vector similarity

Requirements:
    - SAGE packages installed (sage-kernel, sage-middleware, sage-common)
    - SageFlow installed (pip install isage-flow)
    - Optional: sentence-transformers for real embeddings

Usage:
    python sage_sageflow_integrated_demo.py --scenario rag
    python sage_sageflow_integrated_demo.py --scenario aggregation
    python sage_sageflow_integrated_demo.py --scenario session
"""

from __future__ import annotations

import argparse
import random
import time
from typing import Any

import numpy as np

# SAGE imports
from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.kernel.runtime.communication.packet import StopSignal

# SageFlow operator (from sage-middleware)
from sage.middleware.components.sage_flow.operators import (
    SageFlowAggregationOperator,
    SageFlowJoinOperator,
)

# ============================================================================
# Mock Embedding Function (replace with real embedding model in production)
# ============================================================================


def generate_embedding(text: str, dim: int = 128) -> np.ndarray:
    """Generate a deterministic embedding based on text hash."""
    # Use hash to generate reproducible embedding
    seed = hash(text) % (2**32)
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(dim).astype(np.float32)
    return vec / (np.linalg.norm(vec) + 1e-8)


# ============================================================================
# Sample Data
# ============================================================================

SAMPLE_DOCUMENTS = [
    {"id": 1, "title": "SAGE Overview", "content": "SAGE is a Python framework for AI pipelines."},
    {"id": 2, "title": "Installation", "content": "Run ./quickstart.sh --dev to install SAGE."},
    {"id": 3, "title": "Architecture", "content": "SAGE has 6 layers: common, platform, kernel, libs, middleware, cli."},
    {"id": 4, "title": "SageFlow", "content": "SageFlow is a C++ vector stream processing engine."},
    {"id": 5, "title": "Vector Join", "content": "SageFlow performs real-time vector similarity joins."},
    {"id": 6, "title": "LLM Service", "content": "SAGE provides unified LLM inference via Control Plane."},
    {"id": 7, "title": "Memory", "content": "NeuroMem provides hierarchical memory management."},
    {"id": 8, "title": "RAG Pipeline", "content": "Build RAG pipelines with retrieval and generation."},
]

SAMPLE_QUERIES = [
    "What is SAGE framework?",
    "How to install SAGE?",
    "Explain SAGE architecture",
    "What is SageFlow?",
    "How does vector join work?",
    "What is SAGE used for?",  # Similar to first query
    "How to set up SAGE?",  # Similar to second query
]


# ============================================================================
# Scenario 1: Streaming RAG Pipeline
# ============================================================================


class QuerySource(SourceFunction):
    """Source that emits user queries."""

    def __init__(self, queries: list[str], **kwargs):
        super().__init__(**kwargs)
        self.queries = queries
        self.index = 0

    def execute(self, data=None):
        if self.index >= len(self.queries):
            return StopSignal("All queries processed")

        query = self.queries[self.index]
        self.index += 1
        return {"id": self.index, "query": query, "timestamp": time.time()}


class EmbeddingOperator(MapFunction):
    """Compute embeddings for queries."""

    def __init__(self, dim: int = 128, **kwargs):
        super().__init__(**kwargs)
        self.dim = dim

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        query = data.get("query", "")
        embedding = generate_embedding(query, self.dim)
        return {**data, "embedding": embedding}


class ContextAggregator(MapFunction):
    """Aggregate retrieved documents into LLM context."""

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        matched_docs = data.get("matched_docs", [])
        similarity_scores = data.get("similarity_scores", [])

        # Build context from matched documents
        context_parts = []
        for doc_id, score in zip(matched_docs, similarity_scores):
            # Find document by ID
            for doc in SAMPLE_DOCUMENTS:
                if doc["id"] == doc_id:
                    context_parts.append(f"[{doc['title']}] {doc['content']} (score: {score:.3f})")
                    break

        context = "\n".join(context_parts) if context_parts else "No relevant documents found."

        return {
            **data,
            "context": context,
            "num_retrieved": len(matched_docs),
        }


class MockLLMOperator(MapFunction):
    """Mock LLM that generates response based on context."""

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        query = data.get("query", "")
        context = data.get("context", "")
        num_retrieved = data.get("num_retrieved", 0)

        # Mock LLM response
        response = f"Based on {num_retrieved} retrieved documents, here's the answer to '{query}':\n"
        if context:
            response += f"Context summary: {context[:100]}..."
        else:
            response += "I don't have enough context to answer this question."

        return {**data, "response": response}


class ResponseSink(SinkFunction):
    """Output responses."""

    def __init__(self, verbose: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.verbose = verbose
        self.results = []

    def execute(self, data: dict[str, Any]) -> None:
        self.results.append(data)
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Query: {data.get('query', 'N/A')}")
            print(f"Retrieved: {data.get('num_retrieved', 0)} documents")
            print(f"Response: {data.get('response', 'N/A')[:200]}...")
            print(f"{'='*60}")


def run_streaming_rag_demo():
    """
    Scenario 1: Streaming RAG Pipeline

    Data Flow:
        QuerySource → EmbeddingOperator → SageFlowJoinOperator → ContextAggregator → MockLLM → Sink

    SageFlow's role:
        - Maintains document index in C++ for fast retrieval
        - Performs real-time vector similarity join
        - Returns matched documents with similarity scores
    """
    print("\n" + "=" * 70)
    print("Scenario 1: Streaming RAG with SageFlow Vector Join")
    print("=" * 70)

    dim = 128

    # Pre-compute document embeddings
    doc_vectors = np.array(
        [generate_embedding(doc["content"], dim) for doc in SAMPLE_DOCUMENTS],
        dtype=np.float32,
    )
    doc_ids = [doc["id"] for doc in SAMPLE_DOCUMENTS]

    # Create SageFlow join operator
    sageflow_join = SageFlowJoinOperator(
        dim=dim,
        doc_vectors=doc_vectors,
        doc_ids=doc_ids,
        similarity_threshold=0.3,  # Lower threshold for demo
        join_method="bruteforce_lazy",
    )

    # Build SAGE pipeline
    from sage.kernel.api import LocalEnvironment

    env = LocalEnvironment()
    sink = ResponseSink(verbose=True)

    # Pipeline: Source → Embed → SageFlow Join → Context → LLM → Sink
    (
        env.from_source(QuerySource, queries=SAMPLE_QUERIES[:5])
        .map(EmbeddingOperator, dim=dim)
        .map(sageflow_join)  # SageFlow integration point
        .map(ContextAggregator)
        .map(MockLLMOperator)
        .sink(sink)
    )

    env.execute()

    print(f"\nProcessed {len(sink.results)} queries through SAGE+SageFlow pipeline")
    return sink.results


# ============================================================================
# Scenario 2: Similar Query Aggregation
# ============================================================================


class BatchQuerySource(SourceFunction):
    """Source that emits queries in batches."""

    def __init__(self, queries: list[str], batch_interval: float = 0.1, **kwargs):
        super().__init__(**kwargs)
        self.queries = queries
        self.batch_interval = batch_interval
        self.index = 0

    def execute(self, data=None):
        if self.index >= len(self.queries):
            return StopSignal("All queries emitted")

        query = self.queries[self.index]
        self.index += 1

        # Simulate batch arrival
        time.sleep(self.batch_interval)

        return {
            "id": self.index,
            "query": query,
            "user_id": f"user_{random.randint(1, 100)}",
            "timestamp": time.time(),
        }


class GroupProcessorOperator(MapFunction):
    """Process query groups - only process representative, distribute to others."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._group_results: dict[int, str] = {}

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        is_representative = data.get("is_representative", True)
        group_ids = data.get("group_ids", [])
        group_queries = data.get("group_queries", [])

        if is_representative:
            # This is the representative query - generate response for the group
            response = f"[GROUP RESPONSE] Answered for {len(group_ids)} similar queries: "
            response += f"'{data.get('query', '')[:50]}...'"

            # Store result for group members
            for gid in group_ids:
                self._group_results[gid] = response

            return {
                **data,
                "response": response,
                "is_processed": True,
                "group_size": len(group_ids),
            }
        else:
            # This is a group member - use cached response
            query_id = data.get("id")
            cached_response = self._group_results.get(query_id, "[CACHED] Using group representative's response")

            return {
                **data,
                "response": cached_response,
                "is_processed": False,
                "group_size": len(group_ids),
            }


class AggregationSink(SinkFunction):
    """Collect aggregation results and statistics."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.results = []
        self.total_processed = 0
        self.groups_formed = 0

    def execute(self, data: dict[str, Any]) -> None:
        self.results.append(data)
        if data.get("is_processed"):
            self.groups_formed += 1
            self.total_processed += data.get("group_size", 1)

        if data.get("is_representative"):
            print(f"[REP] Query {data.get('id')}: Group of {data.get('group_size', 1)} queries")
        else:
            print(f"[MEM] Query {data.get('id')}: Using cached response from group")


def run_aggregation_demo():
    """
    Scenario 2: Similar Query Aggregation

    Data Flow:
        BatchQuerySource → Embed → SageFlowAggregation → GroupProcessor → Sink

    SageFlow's role:
        - Groups semantically similar queries together
        - Identifies representative query for each group
        - Enables batch processing to reduce redundant LLM calls
    """
    print("\n" + "=" * 70)
    print("Scenario 2: Similar Query Aggregation with SageFlow")
    print("=" * 70)

    dim = 128

    # Create aggregation operator
    aggregation_op = SageFlowAggregationOperator(
        dim=dim,
        similarity_threshold=0.7,
        aggregation_window_ms=500,  # 500ms window
        min_group_size=1,
    )

    # Build SAGE pipeline
    from sage.kernel.api import LocalEnvironment

    env = LocalEnvironment()
    sink = AggregationSink()

    (
        env.from_source(BatchQuerySource, queries=SAMPLE_QUERIES, batch_interval=0.05)
        .map(EmbeddingOperator, dim=dim)
        .map(aggregation_op)  # SageFlow aggregation
        .map(GroupProcessorOperator)
        .sink(sink)
    )

    env.execute()

    print(f"\nAggregation Stats:")
    print(f"  Total queries: {len(sink.results)}")
    print(f"  Groups formed: {sink.groups_formed}")
    print(f"  LLM calls saved: {len(sink.results) - sink.groups_formed}")

    return sink.results


# ============================================================================
# Scenario 3: Session Semantic State Maintenance
# ============================================================================


class ConversationSource(SourceFunction):
    """Source that emits conversation turns."""

    def __init__(self, session_id: str = "session_001", **kwargs):
        super().__init__(**kwargs)
        self.session_id = session_id
        self.turns = [
            {"role": "user", "content": "Tell me about SAGE framework"},
            {"role": "assistant", "content": "SAGE is a Python framework for AI pipelines..."},
            {"role": "user", "content": "How do I install it?"},
            {"role": "assistant", "content": "Run ./quickstart.sh --dev to install..."},
            {"role": "user", "content": "What about the architecture?"},
            {"role": "assistant", "content": "SAGE has 6 layers..."},
            {"role": "user", "content": "Tell me more about the first thing you mentioned"},  # Reference to earlier
        ]
        self.index = 0

    def execute(self, data=None):
        if self.index >= len(self.turns):
            return StopSignal("Conversation ended")

        turn = self.turns[self.index]
        self.index += 1

        return {
            "session_id": self.session_id,
            "turn_id": self.index,
            "role": turn["role"],
            "content": turn["content"],
            "timestamp": time.time(),
        }


class SessionContextBuilder(MapFunction):
    """Build conversation context using SageFlow's semantic matching."""

    def __init__(self, dim: int = 128, context_window: int = 5, **kwargs):
        super().__init__(**kwargs)
        self.dim = dim
        self.context_window = context_window

        # Session history (would be persistent in production)
        self._history: list[dict[str, Any]] = []
        self._sageflow_join: SageFlowJoinOperator | None = None

    def _update_sageflow(self) -> None:
        """Update SageFlow with current history."""
        if len(self._history) < 2:
            return

        # Use all history as document index
        history_vectors = np.array(
            [h["embedding"] for h in self._history[:-1]],  # Exclude current turn
            dtype=np.float32,
        )
        history_ids = [h["turn_id"] for h in self._history[:-1]]

        self._sageflow_join = SageFlowJoinOperator(
            dim=self.dim,
            doc_vectors=history_vectors,
            doc_ids=history_ids,
            similarity_threshold=0.4,
            join_method="bruteforce_lazy",
        )

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        # Compute embedding
        content = data.get("content", "")
        embedding = generate_embedding(content, self.dim)
        data["embedding"] = embedding

        # Add to history
        self._history.append(data.copy())

        # Update SageFlow index
        self._update_sageflow()

        if self._sageflow_join is None:
            return {**data, "context_turns": [], "semantic_references": []}

        # Query SageFlow for semantically related turns
        result = self._sageflow_join.execute(data)
        matched_turns = result.get("matched_docs", [])
        scores = result.get("similarity_scores", [])

        # Build semantic context
        context_turns = []
        for turn_id, score in zip(matched_turns, scores):
            for h in self._history:
                if h.get("turn_id") == turn_id:
                    context_turns.append({
                        "turn_id": turn_id,
                        "role": h.get("role"),
                        "content": h.get("content"),
                        "similarity": score,
                    })
                    break

        return {
            **data,
            "context_turns": context_turns,
            "semantic_references": matched_turns,
            "history_length": len(self._history),
        }


class SessionResponseGenerator(MapFunction):
    """Generate response using semantic context."""

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        role = data.get("role")

        if role == "assistant":
            # Pass through assistant messages
            return data

        # User message - generate response with context
        content = data.get("content", "")
        context_turns = data.get("context_turns", [])

        if context_turns:
            context_summary = "; ".join(
                [f"[Turn {t['turn_id']}] {t['content'][:30]}..." for t in context_turns[:3]]
            )
            response = f"Based on our conversation ({context_summary}), here's my response to '{content[:50]}...'"
        else:
            response = f"Response to: '{content[:50]}...'"

        return {
            **data,
            "generated_response": response,
        }


class SessionSink(SinkFunction):
    """Display session state and responses."""

    def execute(self, data: dict[str, Any]) -> None:
        turn_id = data.get("turn_id")
        role = data.get("role")
        content = data.get("content", "")[:50]
        refs = data.get("semantic_references", [])

        print(f"Turn {turn_id} [{role}]: {content}...")
        if refs:
            print(f"  → Semantic refs: {refs}")
        if data.get("generated_response"):
            print(f"  → Response: {data['generated_response'][:80]}...")


def run_session_demo():
    """
    Scenario 3: Session Semantic State Maintenance

    Data Flow:
        ConversationSource → SessionContextBuilder (SageFlow) → ResponseGenerator → Sink

    SageFlow's role:
        - Maintains semantic index of conversation history
        - Finds relevant context for each new message
        - Enables reference resolution (e.g., "the first thing you mentioned")
    """
    print("\n" + "=" * 70)
    print("Scenario 3: Session Semantic State with SageFlow")
    print("=" * 70)

    from sage.kernel.api import LocalEnvironment

    env = LocalEnvironment()

    (
        env.from_source(ConversationSource, session_id="demo_session")
        .map(SessionContextBuilder, dim=128, context_window=5)
        .map(SessionResponseGenerator)
        .sink(SessionSink)
    )

    env.execute()


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="SAGE + SageFlow Integrated Pipeline Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python sage_sageflow_integrated_demo.py --scenario rag
    python sage_sageflow_integrated_demo.py --scenario aggregation
    python sage_sageflow_integrated_demo.py --scenario session
    python sage_sageflow_integrated_demo.py --scenario all
        """,
    )
    parser.add_argument(
        "--scenario",
        choices=["rag", "aggregation", "session", "all"],
        default="all",
        help="Which demo scenario to run",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("SAGE + SageFlow Integrated Pipeline Demo")
    print("=" * 70)
    print("\nThis demo shows SageFlow integrated as a component within SAGE's")
    print("DataStream pipeline, handling high-performance vector operations.")
    print("\nArchitecture:")
    print("  SAGE Source → SAGE Operators → SageFlow (C++) → SAGE Operators → SAGE Sink")

    if args.scenario in ("rag", "all"):
        run_streaming_rag_demo()

    if args.scenario in ("aggregation", "all"):
        run_aggregation_demo()

    if args.scenario in ("session", "all"):
        run_session_demo()

    print("\n" + "=" * 70)
    print("Demo Complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
