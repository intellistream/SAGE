"""
RefinedSearcherOperator - Search with optional context compression.

Uses isage-refiner for context compression if enabled.

Installation:
    pip install isage-refiner  # Optional, only if refiner is used
"""

import logging
from typing import Any, AsyncGenerator, Optional

from sage_libs.sage_agentic.agents.bots.searcher_bot import SearcherBot

from sage.libs.foundation.tools.tool import BaseTool

logger = logging.getLogger(__name__)


class RefinedSearcherOperator:
    """
    L4 Operator that wraps L3 SearcherBot and adds optional refiner capabilities.

    Uses isage-refiner for context compression when refiner_config is provided.
    """

    name = "search_internet"
    description = "Search the internet for information using multiple sources (Arxiv, etc)."
    input_schema = {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "The search query"}},
        "required": ["query"],
    }

    input_types = {"query": "str - The search query"}

    def __init__(
        self, tools: list[BaseTool], refiner_config: Optional[dict[str, Any]] = None, **kwargs
    ):
        self.bot = SearcherBot(tools=tools, **kwargs)

        self.compressor = None
        if refiner_config:
            try:
                algorithm = refiner_config.get("algorithm", "long_refiner").lower()
                self._init_compressor(algorithm, refiner_config)
                logger.info(f"RefinedSearcherOperator: Initialized {algorithm} compressor")
            except ImportError as e:
                logger.warning(
                    f"RefinedSearcherOperator: isage-refiner not installed: {e}\n"
                    f"Install with: pip install isage-refiner"
                )
            except Exception as e:
                logger.warning(f"RefinedSearcherOperator: Failed to init compressor: {e}")

    def _init_compressor(self, algorithm: str, config: dict[str, Any]):
        """Initialize compressor from isage-refiner."""
        if algorithm == "long_refiner":
            from sage_refiner import LongRefinerCompressor

            self.compressor = LongRefinerCompressor(
                base_model_path=config.get("base_model_path", "Qwen/Qwen2.5-3B-Instruct"),
                score_model_path=config.get("score_model_path", "BAAI/bge-reranker-v2-m3"),
                max_model_len=config.get("max_model_len", 25000),
                gpu_memory_utilization=config.get("gpu_memory_utilization", 0.5),
            )
        elif algorithm == "reform":
            from sage_refiner import REFORMCompressor

            self.compressor = REFORMCompressor(**config.get("reform_config", {}))
        elif algorithm == "provence":
            from sage_refiner import ProvenceCompressor

            self.compressor = ProvenceCompressor(**config.get("provence_config", {}))
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        self.budget = config.get("budget", 2048)

    def call(self, arguments: dict) -> Any:
        """MCP compatible call method"""
        import asyncio

        query = arguments.get("query")
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                return asyncio.run(self.execute(query))
        except RuntimeError:
            return asyncio.run(self.execute(query))

        return asyncio.run(self.execute(query))

    async def execute(self, query: str) -> dict[str, Any]:
        """Execute search and optionally compress results."""
        data = query
        # 1. Execute L3 Bot
        raw_result = await self.bot.execute(data)
        results = raw_result.get("results", [])

        # 2. Compress if enabled
        if self.compressor and results:
            query_str = data if isinstance(data, str) else data.get("query", "")
            try:
                logger.info(f"Compressing {len(results)} results for query: {query_str}")

                # Normalize documents to isage-refiner format
                documents = [
                    {"contents": r.get("contents") or r.get("text") or str(r)} for r in results
                ]

                compress_result = self.compressor.compress(
                    question=query_str,
                    document_list=documents,
                    budget=self.budget,
                )

                return {
                    "results": compress_result.get("compressed_context", ""),
                    "original_count": len(results),
                    "compressed": True,
                }
            except Exception as e:
                logger.error(f"Compression failed: {e}")
                return raw_result

        return raw_result

    async def execute_stream(self, data: Any) -> AsyncGenerator[dict[str, Any], None]:
        """Stream execution. Compression is batch, so just stream search events."""
        async for event in self.bot.execute_stream(data):
            yield event
