"""
Researcher Agent - Specialized agent for information retrieval
"""

import logging
from typing import AsyncGenerator

from sage.libs.agentic.agents.bots.searcher_bot import SearcherBot
from sage.studio.models.agent_step import AgentStep
from sage.studio.services.agents.base import BaseAgent
from sage.studio.tools.base import BaseTool

try:
    from sage.middleware.components.sage_refiner.python.service import RefinerService
except ImportError:
    RefinerService = None

logger = logging.getLogger(__name__)


class ResearcherAgent(BaseAgent):
    """
    Agent specialized in researching information from various sources
    (Arxiv, Nature, Internal Knowledge Base).

    Delegates core search logic to L3 SearcherBot.
    Uses L4 RefinerService for context compression.
    """

    def __init__(self, tools: list[BaseTool]):
        super().__init__(name="Researcher", role="Academic Researcher", tools=tools)
        # Initialize L3 Bot with L6 tools (SearcherBot is now async-compatible)
        self.bot = SearcherBot(tools=tools)

        # Initialize L4 Refiner
        if RefinerService:
            try:
                self.refiner = RefinerService()
            except Exception as e:
                logger.warning(f"Failed to initialize RefinerService: {e}")
                self.refiner = None
        else:
            self.refiner = None
            logger.warning(
                "RefinerService not available (sage-middleware not installed or import failed)"
            )

    async def run(self, query: str, history: list[dict] = None) -> AsyncGenerator[AgentStep, None]:
        """
        Execute research workflow:
        1. Delegate to SearcherBot for retrieval
        2. (Future) Refine results using Refiner
        3. Return formatted results
        """
        yield AgentStep.create(
            type="reasoning", content=f"Researcher Agent received task: {query}", status="running"
        )

        try:
            # Delegate to L3 SearcherBot
            logger.info(f"Delegating query '{query}' to SearcherBot")

            all_results = []

            # Use streaming execution to show progress
            async for event in self.bot.execute_stream(query):
                if event["type"] == "tool_start":
                    yield AgentStep.create(
                        type="tool_call",
                        content=f"Calling tool: {event['tool']}...",
                        status="running",
                        tool_name=event["tool"],
                    )
                elif event["type"] == "tool_result":
                    results = event.get("results", [])
                    all_results.extend(results)
                    yield AgentStep.create(
                        type="tool_result",
                        content=f"Tool {event['tool']} returned {len(results)} results.",
                        status="completed",
                        tool_name=event["tool"],
                    )
                elif event["type"] == "tool_error":
                    yield AgentStep.create(
                        type="tool_result",
                        content=f"Tool {event['tool']} failed: {event.get('error')}",
                        status="failed",
                        tool_name=event["tool"],
                    )

            if not all_results:
                yield AgentStep.create(
                    type="tool_result",
                    content="Search completed but no results were found.",
                    status="completed",
                    tool_name="SearcherBot",
                )
                return

            # Refine results if Refiner is available
            final_results = all_results
            if self.refiner:
                yield AgentStep.create(
                    type="reasoning",
                    content="Refining search results to extract relevant information...",
                    status="running",
                )
                try:
                    # Run refinement (CPU bound, but fast for simple algos)
                    # In a real async app, might want to run in executor
                    refine_result = self.refiner.refine(query, all_results)

                    # Refiner returns a RefineResult object with 'content' (str) or 'documents' (list)
                    # Depending on the algorithm. Assuming 'documents' contains the refined list.
                    # If the refiner returns a single string summary, we adapt.

                    if hasattr(refine_result, "documents") and refine_result.documents:
                        final_results = refine_result.documents
                        yield AgentStep.create(
                            type="reasoning",
                            content=f"Refinement complete. Reduced to {len(final_results)} relevant items.",
                            status="completed",
                        )
                    else:
                        # Fallback if refiner didn't return documents list
                        logger.warning(
                            "Refiner did not return documents list, using original results"
                        )

                except Exception as e:
                    logger.error(f"Refinement failed: {e}")
                    yield AgentStep.create(
                        type="reasoning",
                        content=f"Refinement failed ({str(e)}), using original results.",
                        status="failed",
                    )

            # Format results for display
            summary_lines = [f"Found {len(final_results)} results:"]

            for idx, item in enumerate(final_results, 1):
                source = item.get("source", "Unknown Source")
                content = item.get("content", "")
                # Truncate content for display
                preview = content[:200] + "..." if len(content) > 200 else content
                summary_lines.append(f"{idx}. **{source}**: {preview}")

            response_content = "\n\n".join(summary_lines)

            yield AgentStep.create(
                type="tool_result",
                content=response_content,
                status="completed",
                tool_name="SearcherBot",
                raw_results=final_results,
            )

        except Exception as e:
            logger.error(f"ResearcherAgent failed: {e}", exc_info=True)
            yield AgentStep.create(
                type="response", content=f"Research failed: {str(e)}", status="failed"
            )
