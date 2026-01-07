#!/usr/bin/env python3
"""
Test Multi-Branch Adaptive-RAG Pipeline

This demonstrates SAGE's Multi-Branch Pipeline pattern:
- Source emits queries
- Classifier tags each query with complexity level
- Multiple filter() branches route data to different strategies
- Each branch processes independently and sinks results
"""

import sys
import time
sys.path.insert(0, ".")
import os
os.environ["SAGE_LOG_LEVEL"] = "ERROR"

from sage.kernel.api import LocalEnvironment
from sage.common.core.functions import MapFunction, SinkFunction, SourceFunction, FilterFunction

# Import classifier
from classifier import QueryComplexityLevel, create_classifier

# ============================================================================
# Define Operators
# ============================================================================


class QuerySource(SourceFunction):
    """Source that emits queries one by one."""

    def __init__(self, queries, delay=0.0, **kwargs):
        super().__init__(**kwargs)
        self.queries = queries
        self.delay = delay
        self.counter = 0

    def execute(self):
        if self.counter >= len(self.queries):
            return None
        query = self.queries[self.counter]
        self.counter += 1
        if self.delay > 0:
            time.sleep(self.delay)
        print(f"📤 Source [{self.counter}/{len(self.queries)}]: {query[:40]}...")
        return {"query": query, "complexity": None}


class ClassifierMap(MapFunction):
    """Classify query complexity (ZERO/SINGLE/MULTI)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._classifier = None

    def execute(self, data):
        if self._classifier is None:
            self._classifier = create_classifier("rule")
        result = self._classifier.classify(data["query"])
        data["complexity"] = result.complexity.name
        q = data["query"][:30]
        print(f"🏷️  Classified: {q}... -> {result.complexity.name}")
        return data


# ============ Branch Filters ============


class ZeroFilter(FilterFunction):
    """Pass through ZERO complexity queries only."""

    def execute(self, data):
        is_match = data.get("complexity") == "ZERO"
        if is_match:
            q = data["query"][:25]
            print(f"    ✅ ZERO branch accepts: {q}...")
        return is_match


class SingleFilter(FilterFunction):
    """Pass through SINGLE complexity queries only."""

    def execute(self, data):
        is_match = data.get("complexity") == "SINGLE"
        if is_match:
            q = data["query"][:25]
            print(f"    ✅ SINGLE branch accepts: {q}...")
        return is_match


class MultiFilter(FilterFunction):
    """Pass through MULTI complexity queries only."""

    def execute(self, data):
        is_match = data.get("complexity") == "MULTI"
        if is_match:
            q = data["query"][:25]
            print(f"    ✅ MULTI branch accepts: {q}...")
        return is_match


# ============ Strategy Processors ============


class NoRetrievalMap(MapFunction):
    """Process ZERO complexity: direct answer without retrieval."""

    def execute(self, data):
        q = data["query"][:25]
        print(f"    🔵 NoRetrieval processing: {q}...")
        data["strategy"] = "no_retrieval"
        data["steps"] = 0
        data["answer"] = f"Direct answer for: {data['query'][:20]}"
        return data


class SingleRetrievalMap(MapFunction):
    """Process SINGLE complexity: single-hop retrieval."""

    def execute(self, data):
        q = data["query"][:25]
        print(f"    🟡 SingleRetrieval processing: {q}...")
        data["strategy"] = "single_retrieval"
        data["steps"] = 1
        data["answer"] = f"Single-hop answer for: {data['query'][:20]}"
        return data


class IterativeRetrievalMap(MapFunction):
    """Process MULTI complexity: iterative retrieval."""

    def execute(self, data):
        q = data["query"][:25]
        print(f"    🔴 IterativeRetrieval processing: {q}...")
        data["strategy"] = "iterative_retrieval"
        data["steps"] = 3
        data["answer"] = f"Iterative answer for: {data['query'][:20]}"
        return data


# ============ Result Sink ============


class ResultSink(SinkFunction):
    """Collect results from all branches."""

    results = []  # Class-level collection

    def __init__(self, branch_name="", **kwargs):
        super().__init__(**kwargs)
        self.branch_name = branch_name

    def execute(self, data):
        ResultSink.results.append(data)
        ans = data["answer"][:40]
        print(f"🎯 [{self.branch_name}] Result: {data['strategy']} -> {ans}...")
        return data


# ============================================================================
# Main Test
# ============================================================================


def main():
    print("=" * 70)
    print("Testing Multi-Branch Adaptive-RAG Pipeline")
    print("=" * 70)

    test_queries = [
        "What is machine learning?",  # ZERO - simple factual
        "What are the key features of Python?",  # ZERO - simple factual
        "Compare Japan and Germany economic policies in 2008 crisis",  # MULTI
    ]

    print()
    print("🚀 Building Multi-Branch Pipeline...")
    print("Pipeline structure:")
    print("  Source -> Classifier -+-> filter(ZERO) -> NoRetrieval -> Sink")
    print("                        +-> filter(SINGLE) -> SingleRetrieval -> Sink")
    print("                        +-> filter(MULTI) -> IterativeRetrieval -> Sink")
    print()
    print("-" * 70)

    env = LocalEnvironment("adaptive-rag-branch")

    # Shared upstream: Source -> Classifier
    classified_stream = (
        env.from_source(QuerySource, queries=test_queries, delay=0.1)
        .map(ClassifierMap)
    )

    # Branch A: ZERO complexity
    (
        classified_stream
        .filter(ZeroFilter)
        .map(NoRetrievalMap)
        .sink(ResultSink, branch_name="ZERO", parallelism=1)
    )

    # Branch B: SINGLE complexity
    (
        classified_stream
        .filter(SingleFilter)
        .map(SingleRetrievalMap)
        .sink(ResultSink, branch_name="SINGLE", parallelism=1)
    )

    # Branch C: MULTI complexity
    (
        classified_stream
        .filter(MultiFilter)
        .map(IterativeRetrievalMap)
        .sink(ResultSink, branch_name="MULTI", parallelism=1)
    )

    print()
    print("Pipeline built. Executing...")
    print()

    try:
        env.submit(autostop=True)
        time.sleep(5)
    except Exception as e:
        print(f"Execution error: {e}")
    finally:
        env.close()

    print()
    print("=" * 70)
    print(f"📊 Summary: Processed {len(ResultSink.results)} queries via branches")
    print("=" * 70)

    for r in ResultSink.results:
        q = r["query"][:40]
        print(f"  - [{r['complexity']}] {r['strategy']}: {q}...")

    print()
    print("✅ Multi-Branch Pipeline test completed.")


if __name__ == "__main__":
    main()
