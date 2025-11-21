"""
Basic tests for DyFlow SAGE integration.

Tests core functionality after refactoring to ensure:
1. Imports work correctly
2. Core classes can be instantiated
3. Basic operations function properly
4. SAGE integration (logging, config) works

Layer: L3 (Core Library)
"""

from unittest.mock import patch

import pytest


# Test imports
def test_imports():
    """Test that all main components can be imported."""
    try:
        from sage.libs.workflow_generation.DyFlow.dyflow import (
            ExecuteSignal,
            InstructExecutorOperator,
            ModelService,
            Operator,
            State,
            WorkflowExecutor,
        )

        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")


def test_config_import():
    """Test configuration module import."""
    try:
        from sage.libs.workflow_generation.DyFlow.config import (
            get_model_config,
            get_operator_config,
            get_workflow_config,
            load_config,
        )

        assert True
    except ImportError as e:
        pytest.fail(f"Config import failed: {e}")


def test_state_creation():
    """Test State object creation and basic operations."""
    from sage.libs.workflow_generation.DyFlow.dyflow import State

    # Create state
    problem = "Test problem"
    state = State(original_problem=problem)

    # Verify attributes
    assert state.original_problem == problem
    assert state.final_answer is None
    assert state.final_status == "pending"
    assert len(state.stages) == 0
    assert len(state.actions) == 0
    assert len(state.workflow_log) == 0


def test_state_add_stage():
    """Test adding stages to State."""
    from sage.libs.workflow_generation.DyFlow.dyflow import State

    state = State(original_problem="Test")

    # Add stage
    stage_id = state.add_stage(description="Test stage", status="pending")

    assert stage_id in state.stages
    assert state.stages[stage_id]["description"] == "Test stage"
    assert state.stages[stage_id]["status"] == "pending"


def test_state_add_action():
    """Test adding actions to State."""
    from sage.libs.workflow_generation.DyFlow.dyflow import State

    state = State(original_problem="Test")
    stage_id = state.add_stage("Test stage")

    # Add solution action
    action_id = state.add_action(
        stage_id=stage_id, content="Solution content", action_type="solution", status="generated"
    )

    assert action_id in state.actions
    assert state.actions[action_id]["stage_id"] == stage_id
    assert state.actions[action_id]["content"] == "Solution content"
    assert state.actions[action_id]["status"] == "generated"


def test_state_path_access():
    """Test State path-based data access."""
    from sage.libs.workflow_generation.DyFlow.dyflow import State

    state = State(original_problem="Test")

    # Test get_data_by_path
    problem = state.get_data_by_path("original_problem")
    assert problem == "Test"

    # Test set_data_by_path
    success = state.set_data_by_path("intermediate_data.test_key", "test_value")
    assert success is True

    value = state.get_data_by_path("intermediate_data.test_key")
    assert value == "test_value"


def test_model_service_creation():
    """Test ModelService instantiation with mocked clients."""
    from sage.libs.workflow_generation.DyFlow.dyflow import ModelService

    # Mock the clients to avoid actual API calls
    with patch(
        "sage.libs.workflow_generation.DyFlow.dyflow.model_service.model_service.ModelClients"
    ):
        # Create model service
        service = ModelService.create(model="gpt-4o", temperature=0.7)

        assert service.model == "gpt-4o"
        assert service.temperature == 0.7
        assert service.get_current_model() == "gpt-4o"


def test_model_service_factory_methods():
    """Test ModelService factory methods."""
    from sage.libs.workflow_generation.DyFlow.dyflow import ModelService

    with patch(
        "sage.libs.workflow_generation.DyFlow.dyflow.model_service.model_service.ModelClients"
    ):
        # Test gpt4o factory
        gpt4 = ModelService.gpt4o(temperature=0.5)
        assert gpt4.model == "gpt-4o"
        assert gpt4.temperature == 0.5

        # Test claude factory
        claude = ModelService.claude(temperature=0.3)
        assert claude.model == "claude-3.5-sonnet"
        assert claude.temperature == 0.3


def test_workflow_executor_creation():
    """Test WorkflowExecutor instantiation."""
    from sage.libs.workflow_generation.DyFlow.dyflow import ModelService, WorkflowExecutor

    with patch(
        "sage.libs.workflow_generation.DyFlow.dyflow.model_service.model_service.ModelClients"
    ):
        designer = ModelService.create(model="gpt-4o")
        executor = ModelService.create(model="gpt-3.5-turbo")

        # Create workflow executor
        workflow = WorkflowExecutor(
            problem_description="Test problem",
            designer_service=designer,
            executor_service=executor,
            save_design_history=False,
        )

        assert workflow.state.original_problem == "Test problem"
        assert workflow.designer_llm == designer
        assert workflow.executor_llm == executor


def test_config_loading():
    """Test configuration loading."""
    from sage.libs.workflow_generation.DyFlow.config import load_config

    # Load default config
    config = load_config()

    # Check structure
    assert "model_service" in config
    assert "workflow" in config
    assert "operator" in config
    assert "logging" in config

    # Check model service config
    model_config = config["model_service"]
    assert "designer_model" in model_config
    assert "executor_model" in model_config
    assert "temperature" in model_config


def test_config_helper_functions():
    """Test configuration helper functions."""
    from sage.libs.workflow_generation.DyFlow.config import (
        get_model_config,
        get_operator_config,
        get_workflow_config,
    )

    # Get configs
    model_config = get_model_config()
    workflow_config = get_workflow_config()
    operator_config = get_operator_config()

    # Verify configs
    assert "designer_model" in model_config
    assert "max_stages" in workflow_config
    assert "sandbox" in operator_config


def test_logging_integration():
    """Test SAGE logging integration."""
    from sage.common.utils.logging.custom_logger import CustomLogger
    from sage.libs.workflow_generation.DyFlow.dyflow import State

    # Create logger
    logger = CustomLogger(__name__)

    # Verify logger works
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.error("Test error message")

    # Create state (which uses logger internally)
    state = State(original_problem="Test")
    stage_id = state.add_stage("Test stage")

    # Should not raise any errors
    assert stage_id is not None


def test_state_error_logging():
    """Test State error logging functionality."""
    from sage.libs.workflow_generation.DyFlow.dyflow import State

    state = State(original_problem="Test")

    # Add error
    state.add_error(source="test_component", message="Test error message", details={"key": "value"})

    # Verify error was logged
    assert len(state.error_log) == 1
    assert state.error_log[0]["source"] == "test_component"
    assert state.error_log[0]["message"] == "Test error message"
    assert state.error_log[0]["details"]["key"] == "value"


def test_state_operator_logging():
    """Test State operator execution logging."""
    from sage.libs.workflow_generation.DyFlow.dyflow import State

    state = State(original_problem="Test")

    # Log operator execution
    state.log_operator_execution(
        operator_id="op_1",
        operator_type="GENERATE_ANSWER",
        params={"instruction": "Test instruction"},
        status="completed",
        details={"tokens": 100},
    )

    # Verify log entry
    assert len(state.workflow_log) == 1
    log_entry = state.workflow_log[0]
    assert log_entry["operator_id"] == "op_1"
    assert log_entry["operator_type"] == "GENERATE_ANSWER"
    assert log_entry["status"] == "completed"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
