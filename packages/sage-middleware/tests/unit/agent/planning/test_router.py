from unittest.mock import MagicMock, patch

import pytest

from sage.middleware.operators.agent.planning.router import PlannerRouter


@pytest.fixture
def mock_generator():
    return MagicMock()


@pytest.fixture
def router(mock_generator):
    # We mock the internal planners to avoid instantiating real ones
    with (
        patch("sage.middleware.operators.agent.planning.router.SimpleLLMPlanner"),
        patch("sage.middleware.operators.agent.planning.router.SageLibsPlannerAdapter"),
        patch("sage.middleware.operators.agent.planning.router.GeneratorToClientAdapter"),
    ):
        # Setup mocks
        # mock_simple_instance = MockSimple.return_value
        # mock_adapter_instance = MockAdapter.return_value

        router = PlannerRouter(mock_generator)

        # Manually assign mocks to attributes if __init__ logic is complex or if we want specific control
        # But since we patched the classes used in __init__, router.simple_planner etc are already mocks

        return router


def test_classify_intent_react(router):
    # Mock llm_client.chat to return react strategy
    router.llm_client.chat.return_value = '{"strategy": "react"}'
    strategy = router._classify_intent("some query")
    assert strategy == "react"


def test_classify_intent_simple(router):
    router.llm_client.chat.return_value = '{"strategy": "simple"}'
    strategy = router._classify_intent("hello")
    assert strategy == "simple"


def test_classify_intent_fallback(router):
    # If LLM returns garbage, should default to simple
    router.llm_client.chat.side_effect = Exception("LLM error")
    strategy = router._classify_intent("query")
    assert strategy == "simple"


def test_plan_routing_react(router):
    # Force intent to react
    with patch.object(router, "_classify_intent", return_value="react"):
        router.react_planner.plan.return_value = [{"type": "reply", "text": "react plan"}]

        plan = router.plan("sys", "query", {})

        assert plan == [{"type": "reply", "text": "react plan"}]
        router.react_planner.plan.assert_called_once()
        router.simple_planner.plan.assert_not_called()


def test_plan_routing_simple(router):
    with patch.object(router, "_classify_intent", return_value="simple"):
        router.simple_planner.plan.return_value = [{"type": "reply", "text": "simple plan"}]

        plan = router.plan("sys", "query", {})

        assert plan == [{"type": "reply", "text": "simple plan"}]
        router.simple_planner.plan.assert_called_once()


def test_plan_routing_tot(router):
    with patch.object(router, "_classify_intent", return_value="tot"):
        router.tot_planner.plan.return_value = [{"type": "reply", "text": "tot plan"}]

        plan = router.plan("sys", "query", {})

        assert plan == [{"type": "reply", "text": "tot plan"}]
        router.tot_planner.plan.assert_called_once()


def test_plan_routing_hierarchical(router):
    with patch.object(router, "_classify_intent", return_value="hierarchical"):
        router.hierarchical_planner.plan.return_value = [
            {"type": "reply", "text": "hierarchical plan"}
        ]

        plan = router.plan("sys", "query", {})

        assert plan == [{"type": "reply", "text": "hierarchical plan"}]
        router.hierarchical_planner.plan.assert_called_once()
