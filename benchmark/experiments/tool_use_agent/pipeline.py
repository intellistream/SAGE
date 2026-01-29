#!/usr/bin/env python3
"""
Tool Use Agent Pipeline
=======================

Main pipeline implementation integrating:
- sage-mem: HierarchicalMemoryService for agent memory (STM/MTM/LTM)
- sage-refiner: ContextService for context compression
- sage-db: SageDBService for vector search (RAG)
- ReAct planning: Thought-Action-Observation-Reflection loop

Pipeline Architecture:
    UserQuerySource -> ToolSelector -> ToolExecutor -> ResponseGenerator -> ResponseSink

Services are registered with env.register_service() and accessed via self.call_service().

Usage:
    # As module
    from examples.tutorials.L3_libs.agents.tool_use_agent import run_tool_use_demo
    run_tool_use_demo()

    # Command line
    python -m examples.tutorials.L3_libs.agents.tool_use_agent.pipeline
    python pipeline.py --interactive
    python pipeline.py --query "What is SAGE?"

# test_tags: category=agent, timeout=180, requires_llm=optional
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any

# Ensure package is importable
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]  # experiments/tool_use_agent -> SAGE
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment

try:
    from .models import AgentState
except ImportError:
    from models import AgentState
try:
    from .operators import (
        ResponseGenerator,
        ResponseSink,
        ToolExecutor,
        ToolSelector,
        UserQuerySource,
    )
except ImportError:
    from operators import (
        ResponseGenerator,
        ResponseSink,
        ToolExecutor,
        ToolSelector,
        UserQuerySource,
    )
try:
    from .agent_tools import create_default_registry
except ImportError:
    from agent_tools import create_default_registry


# =============================================================================
# Service Registration Helpers
# =============================================================================


def register_memory_service(env: LocalEnvironment, collection_name: str = "agent_memory") -> bool:
    """
    Register HierarchicalMemoryService for agent memory.

    Uses three-tier memory: STM (short-term), MTM (medium-term), LTM (long-term).
    Falls back gracefully if sage-mem is not available.
    """
    try:
        from sage.middleware.components.sage_mem.services import HierarchicalMemoryService

        env.register_service(
            "memory_service",
            HierarchicalMemoryService,
            collection_name=collection_name,
            tier_mode="three_tier",
            tier_capacities={"stm": 10, "mtm": 50, "ltm": -1},
        )
        print("[Pipeline] Registered memory_service (HierarchicalMemoryService)")
        return True
    except ImportError as e:
        print(f"[Pipeline] sage-mem not available: {e}")
        return False
    except Exception as e:
        print(f"[Pipeline] Failed to register memory_service: {e}")
        return False


def register_context_service(env: LocalEnvironment, max_length: int = 8192) -> bool:
    """
    Register ContextService for context compression.

    Uses sage-refiner to automatically compress long contexts.
    Falls back gracefully if sage-refiner is not available.
    """
    try:
        from sage.middleware.components.sage_refiner import ContextService

        env.register_service(
            "context_service",
            ContextService,
            config={
                "max_context_length": max_length,
                "auto_compress": True,
                "compress_threshold": 0.8,
                "refiner": {"algorithm": "simple", "budget": 2000},
            },
        )
        print("[Pipeline] Registered context_service (ContextService)")
        return True
    except ImportError as e:
        print(f"[Pipeline] sage-refiner not available: {e}")
        return False
    except Exception as e:
        print(f"[Pipeline] Failed to register context_service: {e}")
        return False


def register_vector_db_service(
    env: LocalEnvironment,
    dimension: int | None = None,
    knowledge_base: list[dict[str, Any]] | None = None,
) -> bool:
    """
    Register SageDBService for vector search (RAG).

    Pre-populates with SAGE documentation knowledge base using real embeddings.
    Falls back gracefully if sage-db is not available.

    Args:
        env: LocalEnvironment to register service
        dimension: Vector dimension (auto-detected from embedding if None)
        knowledge_base: List of documents to pre-load
    """
    try:
        import numpy as np

        from sage.middleware.components.sage_db.python.micro_service.sage_db_service import (
            SageDBService,
        )

        # Default SAGE knowledge base
        if knowledge_base is None:
            knowledge_base = [
                {
                    "title": "SAGE Framework Overview",
                    "text": "SAGE is a Python framework for building AI/LLM data processing pipelines with declarative dataflow. It consists of 6 layers from L1-Common to L6-Interface.",
                    "tags": "overview,architecture",
                },
                {
                    "title": "SAGE Installation",
                    "text": "To install SAGE, run ./quickstart.sh --dev --yes for development. Prerequisites: Python 3.10+, build-essential, cmake.",
                    "tags": "installation,setup",
                },
                {
                    "title": "Pipeline Operators",
                    "text": "SAGE uses SourceFunction, MapFunction, SinkFunction operators. Connect via LocalEnvironment and access services with self.call_service().",
                    "tags": "pipeline,operators",
                },
                {
                    "title": "Memory Services",
                    "text": "sage-mem provides HierarchicalMemoryService with STM/MTM/LTM tiers. Use MemoryServiceFactory.create_instance() to create services.",
                    "tags": "memory,sage-mem",
                },
                {
                    "title": "Context Compression",
                    "text": "sage-refiner ContextService provides automatic context compression. Supports simple, llmlingua2, provence, reform algorithms.",
                    "tags": "refiner,compression",
                },
            ]

        # Try to get embeddings for knowledge base
        def get_embeddings(texts: list[str]) -> tuple[list[list[float]], int] | None:
            """Get embeddings using UnifiedInferenceClient"""
            try:
                from sage.common.components.sage_llm import UnifiedInferenceClient
                from sage.common.components.sage_llm.unified_client import InferenceResult

                client = UnifiedInferenceClient.create()
                result = client.embed(texts)

                # embed() returns list[list[float]] or InferenceResult
                embeddings: list[list[float]]
                if isinstance(result, InferenceResult):
                    # Extract embeddings from InferenceResult.content
                    # content is str | list[list[float]], but for embed it is always list[list[float]]
                    embeddings = result.content  # type: ignore[assignment]
                else:
                    embeddings = result

                if embeddings and len(embeddings) > 0:
                    dim = len(embeddings[0])
                    return embeddings, dim
            except Exception as e:
                print(f"[Pipeline] Embedding error: {e}")
            return None

        # Create bootstrapped service with real embeddings
        class BootstrappedSageDBService(SageDBService):
            """SageDB with pre-loaded knowledge base using real embeddings"""

            def __init__(self, *, initial_data: list[dict], dimension: int, **kwargs):
                super().__init__(dimension=dimension, **kwargs)

                texts = [item.get("text", item.get("content", "")) for item in initial_data]

                # Try real embeddings first
                embed_result = get_embeddings(texts)

                if embed_result is not None:
                    embeddings, _ = embed_result
                    vectors = np.array(embeddings, dtype=np.float32)
                    print(f"[Pipeline] Using real embeddings (dim={dimension})")
                else:
                    # Fallback to simple hash-based mock embeddings
                    print(f"[Pipeline] Using mock embeddings (dim={dimension})")
                    vectors = []
                    for text in texts:
                        vec = np.zeros(dimension, dtype=np.float32)
                        for i, char in enumerate(text[:dimension]):
                            vec[i % dimension] += ord(char) / 1000.0
                        vec = vec / (np.linalg.norm(vec) + 1e-8)
                        vectors.append(vec)
                    vectors = np.array(vectors, dtype=np.float32)

                # Build metadata list
                metadata_list = []
                for item in initial_data:
                    metadata_list.append(
                        {
                            "title": item.get("title", ""),
                            "text": item.get("text", item.get("content", "")),
                            "tags": item.get("tags", ""),
                        }
                    )

                # Add to database
                self.add_batch(vectors, metadata_list)
                self._db.build_index()
                print(f"[Pipeline] Loaded {len(vectors)} documents into vector_db")

        # Auto-detect dimension from embedding service
        if dimension is None:
            texts = [kb[0].get("text", "") for kb in [knowledge_base] if kb]
            embed_result = get_embeddings(texts[:1]) if texts else None
            if embed_result:
                _, dimension = embed_result
                print(f"[Pipeline] Auto-detected embedding dimension: {dimension}")
            else:
                dimension = 1024  # Default for bge-large models
                print(f"[Pipeline] Using default dimension: {dimension}")

        env.register_service(
            "vector_db",
            BootstrappedSageDBService,
            initial_data=knowledge_base,
            dimension=dimension,
            index_type="AUTO",
        )
        print("[Pipeline] Registered vector_db (SageDBService)")
        return True

    except ImportError as e:
        print(f"[Pipeline] sage-db not available: {e}")
        return False
    except Exception as e:
        print(f"[Pipeline] Failed to register vector_db: {e}")
        return False


# =============================================================================
# Pipeline Entry Points
# =============================================================================


def run_tool_use_demo(
    queries: list[str] | None = None,
    verbose: bool = True,
    register_services: bool = True,
) -> None:
    """
    Run the Tool Use Agent Pipeline demo.

    Args:
        queries: List of queries to process. Uses defaults if None.
        verbose: Enable verbose output in ResponseSink.
        register_services: Whether to register middleware services.

    Example:
        >>> from examples.tutorials.L3_libs.agents.tool_use_agent import run_tool_use_demo
        >>> run_tool_use_demo(["What is SAGE?", "Calculate 2 + 2"])
    """
    # Suppress debug logging unless verbose
    if not verbose:
        CustomLogger.disable_global_console_debug()

    print("""
========================================================================
                    Tool Use Agent Pipeline Demo
========================================================================
  Pipeline: UserQuery -> ToolSelector -> ToolExecutor -> ResponseGenerator

  Integrated Services:
    - memory_service: HierarchicalMemoryService (sage-mem)
    - context_service: ContextService (sage-refiner)
    - vector_db: SageDBService (sage-db)

  Features:
    - ReAct reasoning: Thought-Action-Observation-Reflection
    - Keyword fallback when LLM unavailable
    - Automatic context compression
    - Persistent memory across queries
========================================================================
    """)

    # Create environment
    env = LocalEnvironment("tool_use_agent")

    # Register services
    if register_services:
        print("\n[Pipeline] Registering services...")
        register_memory_service(env)
        register_context_service(env)
        register_vector_db_service(env)
        print()

    # Create tool registry
    tool_registry = create_default_registry()
    print(f"[Pipeline] Available tools: {tool_registry.list_tools()}\n")

    # Default queries
    if queries is None:
        queries = [
            "What is SAGE framework and how to install it?",
            "Calculate 15 * 23 + 47",
            "Search for information about memory services in SAGE",
        ]

    # In test mode, limit queries
    test_mode = os.getenv("SAGE_TEST_MODE") == "true"
    if test_mode:
        queries = queries[:1]
        print("[Pipeline] Test mode: processing 1 query only\n")

    # Build pipeline
    (
        env.from_source(UserQuerySource, queries=queries)
        .map(ToolSelector, tool_registry=tool_registry)
        .map(ToolExecutor, tool_registry=tool_registry)
        .map(ResponseGenerator)
        .sink(ResponseSink, verbose=verbose)
    )

    # Execute
    start_time = time.time()
    env.submit(autostop=True)
    total_time = time.time() - start_time

    print(f"\n[Pipeline] Completed in {total_time:.2f} seconds")
    env.close()


def run_interactive_mode() -> None:
    """
    Run the agent in interactive mode.

    User can input queries one at a time with persistent memory.
    """
    print("""
========================================================================
              Tool Use Agent - Interactive Mode
  Type your query and press Enter.
  Type 'quit', 'exit', or 'q' to stop.
  Type 'clear' to clear memory.
========================================================================
    """)

    # Create tool registry with no services initially
    tool_registry = create_default_registry()
    print(f"Available tools: {tool_registry.list_tools()}\n")

    # Create operator instances for reuse
    selector = ToolSelector(tool_registry=tool_registry)
    executor = ToolExecutor(tool_registry=tool_registry)
    generator = ResponseGenerator()
    sink = ResponseSink(verbose=True)

    session_id = None

    while True:
        try:
            query = input("\n> Your query: ").strip()

            if not query:
                continue

            if query.lower() in ("quit", "exit", "q"):
                print("\nGoodbye.")
                break

            if query.lower() == "clear":
                session_id = None
                print("Memory cleared. Starting new session.")
                continue

            # Create state
            state = AgentState(query=query)
            if session_id:
                state.session_id = session_id
            else:
                session_id = state.session_id

            # Process through operators
            state = selector.execute(state)
            state = executor.execute(state)
            state = generator.execute(state)
            sink.execute(state)

        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye.")
            break
        except Exception as e:
            print(f"\nError: {e}")
            import traceback

            traceback.print_exc()


def main() -> None:
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Tool Use Agent Pipeline - SAGE demonstration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default queries
  python pipeline.py

  # Interactive mode
  python pipeline.py --interactive

  # Custom queries
  python pipeline.py --query "What is SAGE?" --query "Calculate 2+2"

  # Quiet mode (less output)
  python pipeline.py --quiet
        """,
    )

    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive mode",
    )

    parser.add_argument(
        "--query",
        "-q",
        action="append",
        help="Query to process (can be specified multiple times)",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity",
    )

    parser.add_argument(
        "--no-services",
        action="store_true",
        help="Skip registering middleware services (faster startup)",
    )

    args = parser.parse_args()

    # Suppress debug logging
    CustomLogger.disable_global_console_debug()

    if args.interactive:
        run_interactive_mode()
    else:
        run_tool_use_demo(
            queries=args.query,
            verbose=not args.quiet,
            register_services=not args.no_services,
        )


if __name__ == "__main__":
    main()
