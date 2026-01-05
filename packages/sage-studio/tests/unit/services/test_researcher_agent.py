from typing import Any
from unittest.mock import MagicMock

import pytest

from sage.studio.services.agents.researcher import ResearcherAgent
from sage.studio.tools.base import BaseTool


class MockAsyncTool(BaseTool):
    name = "mock_search"
    description = "A mock search tool"

    async def _run(self, **kwargs) -> list[dict[str, Any]]:
        query = kwargs.get("query", "")
        return [{"source": "mock_source", "content": f"Result for {query}"}]


@pytest.mark.asyncio
async def test_researcher_agent_delegation():
    # Setup
    tool = MockAsyncTool()
    agent = ResearcherAgent(tools=[tool])

    # Verify Bot Initialization
    assert agent.bot is not None
    assert len(agent.bot.tools) == 1

    # Execute
    steps = []
    async for step in agent.run("test query"):
        steps.append(step)

    # Verify Steps
    # 1. Reasoning (Received task)
    # 2. Tool Call (Calling tool)
    # 3. Tool Result (Tool returned results)
    # 4. Tool Result (Final summary)
    assert len(steps) >= 2
    assert steps[0].type == "reasoning"
    # The last step should be the final summary
    assert steps[-1].type == "tool_result"
    assert steps[-1].metadata.get("tool_name") == "SearcherBot"

    # Verify Content
    last_step = steps[-1]
    assert "Found 1 results" in last_step.content
    assert "Result for test query" in last_step.content
    assert last_step.metadata["raw_results"][0]["content"] == "Result for test query"


@pytest.mark.asyncio
async def test_researcher_agent_no_results():
    # Setup tool that returns empty
    class EmptyTool(BaseTool):
        name = "empty_search"
        description = "Empty"

        async def _run(self, **kwargs):
            return []

    agent = ResearcherAgent(tools=[EmptyTool()])

    # Execute
    steps = []
    async for step in agent.run("nothing"):
        steps.append(step)

    # Verify
    assert "no results were found" in steps[-1].content


@pytest.mark.asyncio
async def test_researcher_agent_with_refiner(monkeypatch):
    # Mock RefinerService
    mock_refiner = MagicMock()
    mock_result = MagicMock()
    mock_result.documents = [{"source": "refined_source", "content": "Refined Content"}]
    mock_refiner.refine.return_value = mock_result

    # Patch the class in the module
    # Note: We need to patch where it's imported or used.
    # Since ResearcherAgent instantiates it in __init__, we can pass a mock if we modify __init__
    # or patch the class before instantiation.

    # Let's patch the class in the module
    import sage.studio.services.agents.researcher as researcher_module

    monkeypatch.setattr(researcher_module, "RefinerService", MagicMock(return_value=mock_refiner))

    # Setup
    tool = MockAsyncTool()
    agent = ResearcherAgent(tools=[tool])

    # Verify Refiner Initialization
    assert agent.refiner is not None

    # Execute
    steps = []
    async for step in agent.run("test query"):
        steps.append(step)

    # Verify Steps
    # We expect an extra reasoning step for refinement
    refinement_step = next((s for s in steps if "Refining search results" in s.content), None)
    assert refinement_step is not None

    # Verify Final Result uses refined content
    last_step = steps[-1]
    assert "Refined Content" in last_step.content
    assert last_step.metadata["raw_results"][0]["content"] == "Refined Content"
