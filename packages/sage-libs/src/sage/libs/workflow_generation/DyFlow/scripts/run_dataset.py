#!/usr/bin/env python3
"""
Script to run DyFlow on benchmark datasets.

This script demonstrates how to evaluate DyFlow on various benchmarks
such as HumanEval, MATH, LiveBench, PubMedQA, and SocialMaze.
"""

import os
import re
import sys
import warnings

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Suppress ResourceWarning and multiprocessing cleanup errors on NFS
warnings.filterwarnings("ignore", category=ResourceWarning)

from benchmarks import (
    HumanEvalBenchmark,
    LiveBenchBenchmark,
    MathBenchmark,
    PubMedQABenchmark,
    SocialMazeBenchmark,
)
from dyflow.core.workflow import WorkflowExecutor
from dyflow.model_service import ModelService

# Configure model services
# designer_service = ModelService(model='gpt-4.1')
designer_service = ModelService.local()
executor_service = ModelService(model="phi-4", temperature=0.01)
judge_service = ModelService(model="gpt-4.1-mini")


def run_workflow_single(question: str, task_name: str):
    """
    Run DyFlow workflow for reasoning tasks (MATH, LiveBench, PubMedQA, SocialMaze).

    Args:
        question: The problem description
        task_name: Name of the task (used to get the prompt)

    Returns:
        Tuple of (final_answer, design_history)
    """
    prompt = reasoning_task[task_name]["prompt"]
    executor = WorkflowExecutor(
        problem_description=question + "\n\n" + prompt,
        designer_service=designer_service,
        executor_service=executor_service,
        save_design_history=True,
    )
    final_answer = executor.execute()
    design_history = executor.get_design_history()
    return final_answer, design_history


def extract_code(final_answer: str):
    """Extract Python code from markdown code block."""
    code_pattern = r"```python\n(.*?)\n```"
    code_match = re.search(code_pattern, final_answer, re.DOTALL)
    if code_match:
        return code_match.group(1)
    return None


def run_workflow_code(question: str):
    """
    Run DyFlow workflow for code generation tasks (HumanEval).

    Args:
        question: The coding problem description

    Returns:
        Tuple of (generated_code, design_history)
    """
    executor = WorkflowExecutor(
        problem_description=question
        + "\n\n"
        + "Let's work out this problem and return all the imports and function in the final answer in a python code block. You can generate Assertions from the examples to test the function. You should not raise ValueError in your final function code.",
        designer_service=designer_service,
        executor_service=executor_service,
        save_design_history=True,
    )
    final_answer = executor.execute()
    design_history = executor.get_design_history()

    # If workflow failed (returned None), return empty string to mark as failure
    if final_answer is None:
        print("Warning: Workflow failed to produce final answer")
        return "", design_history

    extract_prompt = f"""
You are given:
- A partial or original function definition, which may be incomplete or missing logic.
- A complete working solution, possibly with different function names or wrapped inside another function like solve().

Your task is to:
- Reconstruct the full, correct version of the original function(s) using the logic from the complete solution. Even the entry point is not same.
- Preserve the original function names and signatures from the partial code.
- Include all necessary imports.
- Move everything to the global scope (no solve() wrapper).
- Output a single, clean Python code block with the complete implementation and without main entry point and any test cases.

Here is the input:
Original function definition:
{question}

Complete working solution:
{final_answer}
    """
    extract_answer = judge_service.generate(prompt=extract_prompt)
    code = extract_code(extract_answer["response"])
    return code if code else "", design_history


# Define reasoning tasks with their benchmarks and prompts
reasoning_task = {
    "math_reasoning": {
        "benchmark": MathBenchmark,
        "prompt": "Let's think step by step to solve the problem. Please output your answer in \\boxed{{}}.",
        "function": lambda question: run_workflow_single(question, "math_reasoning"),
    },
    "causal_reasoning": {
        "benchmark": LiveBenchBenchmark,
        "prompt": "Let's think step by step to solve the problem.",
        "function": lambda question: run_workflow_single(question, "causal_reasoning"),
    },
    "medical_reasoning": {
        "benchmark": PubMedQABenchmark,
        "prompt": "Let's think step by step to solve the problem.",
        "function": lambda question: run_workflow_single(question, "medical_reasoning"),
    },
    "social_reasoning": {
        "benchmark": SocialMazeBenchmark,
        "prompt": "Let's think step by step to solve the problem.",
        "function": lambda question: run_workflow_single(question, "social_reasoning"),
    },
    "code_reasoning": {
        "benchmark": HumanEvalBenchmark,
        "prompt": "Let's work out this problem step by step and return all the imports and function in the final answer in a python code block. But don't involve any test cases or assertions in the final python block!",
        "function": run_workflow_code,
    },
}


def run_workflow(
    task_name: str,
    baseline: str,
    mode: str,
    size: int = None,
    max_workers: int = 50,
    pass_k: int = None,
):
    """
    Run DyFlow on a specific benchmark task.

    Args:
        task_name: Name of the task ('math_reasoning', 'causal_reasoning', 'medical_reasoning', 'social_reasoning', 'code_reasoning')
        baseline: Name for the baseline (e.g., 'DyFlow', 'dyplanner')
        mode: 'test' or 'train'
        size: Number of problems to evaluate (None for all)
        max_workers: Maximum number of concurrent workers
        pass_k: Maximum k for pass@k calculations (None for default, int for pass@1 to pass@k)
    """
    print(f"\n{'=' * 60}")
    print(f"Running {task_name} Benchmark")
    print(f"Baseline: {baseline}")
    print(f"Mode: {mode}")
    print(f"Size: {size if size else 'All'}")
    print(f"Max Workers: {max_workers}")
    if pass_k:
        print(f"Pass@k: {pass_k}")
    print(f"{'=' * 60}\n")

    benchmark = reasoning_task[task_name]["benchmark"](
        execution_model="phi-4", baseline=baseline, mode=mode
    )
    benchmark.executor_service = executor_service

    if pass_k is not None and pass_k > 1:
        if benchmark.samples_per_task < pass_k:
            benchmark.samples_per_task = pass_k

        benchmark.k_list = list(range(1, pass_k + 1))

    # Handle different benchmark interfaces
    if task_name == "code_reasoning":
        # HumanEval uses solve_fn parameter
        benchmark.run(
            solve_fn=reasoning_task[task_name]["function"],
            judge_service=judge_service,
            generate_service=designer_service,
            executor_service=executor_service,
            size=size,
            max_workers=max_workers,
            pass_k=pass_k,
        )
    else:
        # Other benchmarks use function parameter
        benchmark.run(
            generate_service=designer_service,
            judge_service=judge_service,
            function=reasoning_task[task_name]["function"],
            size=size,
            max_workers=max_workers,
            pass_k=pass_k,
        )

    metrics = benchmark.calculate_metrics()
    print(f"\n{'=' * 60}")
    print("Evaluation Results:")
    print(f"{'=' * 60}")
    print(metrics)
    print(f"{'=' * 60}\n")

    return metrics


if __name__ == "__main__":
    # Example: Run on test set for evaluation
    # For training data generation, change mode='test' to mode='train'
    run_workflow(
        task_name="code_reasoning",
        baseline="DyFlow",
        mode="test",  # Change to 'train' for training data generation
        size=5,  # Test with 5 problems first
        max_workers=5,
        pass_k=1,
    )
