import logging
from typing import Any, AsyncGenerator, Optional

from sage.libs.agentic.agents.bots.searcher_bot import SearcherBot
from sage.libs.foundation.tools.tool import BaseTool
from sage.middleware.components.sage_refiner import RefinerConfig, RefinerService

logger = logging.getLogger(__name__)


class RefinedSearcherOperator:
    """
    L4 Operator that wraps L3 SearcherBot and adds L4 RefinerService capabilities.
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

        self.refiner = None
        if refiner_config:
            try:
                cfg = RefinerConfig(**refiner_config)
                self.refiner = RefinerService(cfg)
                logger.info("RefinedSearcherOperator: Initialized RefinerService")
            except Exception as e:
                logger.warning(f"RefinedSearcherOperator: Failed to init Refiner: {e}")

    def call(self, arguments: dict) -> Any:
        """MCP compatible call method"""
        import asyncio

        query = arguments.get("query")
        try:
            # Try to get running loop
            loop = asyncio.get_running_loop()
            if loop.is_running():
                # We are in a loop, but call is sync.
                # This is tricky. AgentRuntime calls tools synchronously?
                # AgentRuntime.step calls tools.call().
                # If AgentRuntime is run in a thread (run_in_executor), then we can use asyncio.run?
                # No, if we are in a thread, we can use asyncio.run.
                return asyncio.run(self.execute(query))
        except RuntimeError:
            # No running loop
            return asyncio.run(self.execute(query))

        # If we are here, we are in a loop. We can't use asyncio.run.
        # But AgentRuntime expects a sync result.
        # We need to block until future is done.
        # This is only possible if we are in a separate thread.
        # Gateway runs AgentRuntime in a thread executor. So we should be fine.
        return asyncio.run(self.execute(query))

    async def execute(self, query: str) -> dict[str, Any]:
        """
        Execute search and optionally refine results.
        """
        data = query
        # 1. Execute L3 Bot
        raw_result = await self.bot.execute(data)
        results = raw_result.get("results", [])

        # 2. Refine if enabled
        if self.refiner and results:
            query = data if isinstance(data, str) else data.get("query", "")
            try:
                logger.info(f"Refining {len(results)} results for query: {query}")
                refine_result = self.refiner.refine(query=query, documents=results)

                return {
                    "results": refine_result.refined_content,
                    "metrics": refine_result.metrics.to_dict(),
                    "original_count": len(results),
                    "refined": True,
                }
            except Exception as e:
                logger.error(f"Refinement failed: {e}")
                # Fallback
                return raw_result

        return raw_result

    async def execute_stream(self, data: Any) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream execution. Note: Refinement is usually a batch process,
        so we stream the search events, then maybe a refinement event?
        For now, just delegate to bot stream.
        """
        async for event in self.bot.execute_stream(data):
            yield event
