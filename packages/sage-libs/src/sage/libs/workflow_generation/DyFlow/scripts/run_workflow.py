import os
import sys

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dyflow import ModelService, WorkflowExecutor


def main():
    """
    Run DyFlow on a sample problem.
    """
    # Define the problem to solve
    problem_description = """
    Solve the following math problem:

    A farmer has 12 chickens and 8 rabbits on his farm.
    Each chicken has 2 legs and each rabbit has 4 legs.
    How many legs do all the animals have in total?

    Please provide a step-by-step solution.
    """

    # Create Designer and Executor services
    # Designer: Plans the problem-solving strategy
    # Executor: Executes the planned steps
    designer_service = ModelService(model="gpt-4.1")
    executor_service = ModelService(model="phi-4")

    # Alternative: Use local models
    # designer_service = ModelService.local()
    # executor_service = ModelService(model="phi-4")

    # Create workflow executor
    executor = WorkflowExecutor(
        problem_description=problem_description,
        designer_service=designer_service,
        executor_service=executor_service,
    )

    # Execute the adaptive workflow
    print("Starting DyFlow execution...")
    print("-" * 60)
    final_answer = executor.execute()

    # Display results
    print("\n" + "=" * 60)
    print("WORKFLOW EXECUTION COMPLETE")
    print("=" * 60)

    print("\n=== Final Answer ===")
    print(final_answer)

    print("\n=== Workflow Summary ===")
    print(executor.state.get_state_summary_for_designer())


if __name__ == "__main__":
    main()
