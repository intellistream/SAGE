"""
Basic Usage Example for DyFlow

Demonstrates how to use DyFlow's dynamic workflow execution system
with SAGE framework integration.

Layer: L5 (Application)
"""

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.libs.workflow_generation.DyFlow.config import load_config
from sage.libs.workflow_generation.DyFlow.dyflow import ModelService, WorkflowExecutor

# Initialize logger
logger = CustomLogger(__name__)


def example_basic_workflow():
    """
    Basic example: Solve a math problem using dynamic workflow.

    The Designer LLM will create stages dynamically, and the Executor LLM
    will carry out the instructions in each stage.
    """
    logger.info("=== Basic Workflow Example ===")

    # Load configuration
    config = load_config()
    model_config = config["model_service"]

    # Define the problem
    problem = "Solve the equation: 2x + 5 = 13. What is the value of x?"

    # Create model services
    designer = ModelService.create(
        model=model_config["designer_model"], temperature=model_config["temperature"]
    )

    executor = ModelService.create(
        model=model_config["executor_model"], temperature=model_config["temperature"]
    )

    logger.info(f"Problem: {problem}")
    logger.info(f"Designer Model: {designer.get_current_model()}")
    logger.info(f"Executor Model: {executor.get_current_model()}")

    # Create and execute workflow
    workflow = WorkflowExecutor(
        problem_description=problem,
        designer_service=designer,
        executor_service=executor,
        max_stages=5,
        verbose=True,
    )

    # Execute the workflow
    result = workflow.execute()

    # Display results
    logger.info("\n=== Workflow Execution Complete ===")
    logger.info(f"Final Answer: {result.final_answer}")
    logger.info(f"Final Status: {result.final_status}")
    logger.info(f"Total Stages Executed: {len(result.stages)}")

    # Display usage statistics
    logger.info("\n=== Token Usage Statistics ===")
    designer_stats = designer.get_usage_stats()
    executor_stats = executor.get_usage_stats()

    logger.info("Designer:")
    for model, stats in designer_stats.items():
        logger.info(f"  {model}: {stats['total_tokens']} tokens, ${stats['cost']:.4f}")

    logger.info("Executor:")
    for model, stats in executor_stats.items():
        logger.info(f"  {model}: {stats['total_tokens']} tokens, ${stats['cost']:.4f}")

    return result


def example_code_generation():
    """
    Example: Generate and test Python code using dynamic workflow.

    Demonstrates code generation with testing and review stages.
    """
    logger.info("\n=== Code Generation Example ===")

    # Define the problem
    problem = """
    Write a Python function called 'fibonacci' that:
    1. Takes an integer n as input
    2. Returns the nth Fibonacci number
    3. Handles edge cases (n < 0, n = 0, n = 1)
    4. Is efficient for large n values

    Include docstring and test the function with n = 10.
    """

    # Create model services with higher capability
    designer = ModelService.gpt4o(temperature=0.7)
    executor = ModelService.gpt4o(temperature=0.3)

    logger.info(f"Problem: {problem.strip()}")

    # Create workflow with code execution enabled
    workflow = WorkflowExecutor(
        problem_description=problem,
        designer_service=designer,
        executor_service=executor,
        max_stages=8,
        verbose=True,
    )

    # Execute the workflow
    result = workflow.execute()

    # Display results
    logger.info("\n=== Code Generation Complete ===")
    logger.info(f"Final Answer:\n{result.final_answer}")
    logger.info(f"Total Stages: {len(result.stages)}")

    return result


def example_with_state_inspection():
    """
    Example: Use State object to inspect workflow execution details.

    Demonstrates how to access intermediate results and execution logs.
    """
    logger.info("\n=== State Inspection Example ===")

    problem = "What is the sum of all prime numbers between 1 and 50?"

    # Create workflow
    designer = ModelService.create(model="gpt-4o")
    executor = ModelService.create(model="gpt-3.5-turbo")

    workflow = WorkflowExecutor(
        problem_description=problem,
        designer_service=designer,
        executor_service=executor,
        max_stages=6,
        verbose=False,  # Less verbose for cleaner inspection
    )

    # Execute
    state = workflow.execute()

    # Inspect state
    logger.info("\n=== State Inspection ===")
    logger.info(f"Original Problem: {state.original_problem}")
    logger.info(f"\nStages Executed: {len(state.stages)}")

    for stage_id, stage_data in state.stages.items():
        logger.info(f"\n  {stage_id}:")
        logger.info(f"    Description: {stage_data['description'][:80]}...")
        logger.info(f"    Status: {stage_data['status']}")

    logger.info(f"\nActions Taken: {len(state.actions)}")
    for action_id, action_data in list(state.actions.items())[:3]:  # Show first 3
        logger.info(f"\n  {action_id}:")
        logger.info(f"    Stage: {action_data['stage_id']}")
        logger.info(f"    Status: {action_data['status']}")
        logger.info(f"    Content: {str(action_data['content'])[:80]}...")

    # Inspect logs
    if state.error_log:
        logger.info(f"\nErrors Encountered: {len(state.error_log)}")
        for error in state.error_log:
            logger.warning(f"  {error['source']}: {error['message']}")

    logger.info(f"\nWorkflow Log Entries: {len(state.workflow_log)}")

    # Get state summary
    logger.info("\n=== State Summary for Designer ===")
    summary = state.get_state_summary_for_designer()
    logger.info(summary[:500] + "..." if len(summary) > 500 else summary)

    return state


if __name__ == "__main__":
    # Run examples
    try:
        # Example 1: Basic workflow
        result1 = example_basic_workflow()

        # Example 2: Code generation (commented out by default - requires API key)
        # result2 = example_code_generation()

        # Example 3: State inspection
        # result3 = example_with_state_inspection()

    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)
