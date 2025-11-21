import concurrent.futures
import contextlib
import datetime
import io
import json
import multiprocessing
import os
import re
import shutil  # Needed for check_correctness cleanup
import sys
import time

import numpy as np

# Add project root to sys.path if necessary
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Assuming framework and sandbox are importable
from typing import Any, Callable, Optional

from dyflow.model_service import ModelService  # Assuming this is your model service
from tqdm import tqdm

from .framework import BaseBenchmark, get_relative_path


class TimeoutException(Exception):
    pass


def time_limit(seconds):
    # Simplified placeholder - the original likely uses signals (Unix) or threads
    # A real implementation is needed for functional timeouts.
    # This is a context manager.
    import _thread
    from threading import Thread

    class TimeLimit:
        def __init__(self, sec):
            self._seconds = sec

        def __enter__(self):
            self.timed_out = False
            thread_id = _thread.get_ident()

            def timeout_func():
                time.sleep(self._seconds)
                # Only raise if the main thread is still running the guarded block
                # This basic check might not be perfectly race-condition free
                # A more robust solution would involve shared state or signals
                print(f"Timeout triggered for thread {thread_id}")
                _thread.interrupt_main()  # Request interruption

            self.timer_thread = Thread(target=timeout_func)
            self.timer_thread.daemon = True  # Allow program exit even if thread is running
            self.timer_thread.start()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            # If KeyboardInterrupt was raised due to timeout
            if exc_type is KeyboardInterrupt:
                # Check if it was *our* timeout
                # This is tricky. We might accidentally suppress user Ctrl+C
                # A more robust mechanism is needed. Let's assume for now it was timeout.
                raise TimeoutException(f"Timed out after {self._seconds} seconds")
            # No need to explicitly stop the timer thread as it's a daemon
            # Allow any other exceptions to propagate

    return TimeLimit(seconds)


@contextlib.contextmanager
def swallow_io():
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        yield


@contextlib.contextmanager
def create_tempdir():
    # Basic placeholder, original might have more safety/cleanup
    import tempfile

    dirpath = tempfile.mkdtemp()
    cwd = os.getcwd()
    os.chdir(dirpath)
    try:
        yield dirpath
    finally:
        os.chdir(cwd)
        shutil.rmtree(dirpath)


def reliability_guard(maximum_memory_bytes: Optional[int] = None):
    pass


# --- End Sandbox Utilities ---


class HumanEvalBenchmark(BaseBenchmark):
    def __init__(
        self,
        execution_model: str,
        baseline: str = "DyFlow",
        mode: str = "test",
        samples_per_task: int = 1,
    ):
        """
        Initialize the HumanEval benchmark.

        Args:
            execution_model: Name of the model to use for generating solutions
            baseline: Baseline method name (e.g., "DyFlow", "CoT", etc.)
            mode: Evaluation mode
            samples_per_task: Number of completions to generate per problem
        """
        super().__init__(execution_model, baseline, mode)

        self.generate_service = None
        self.dataset_path = get_relative_path(f"data/humaneval/humaneval_{mode}.json")
        self.output_path = get_relative_path(
            f"results/humaneval/{mode}/{baseline}_{execution_model}.json"
        )
        self.cost_path = get_relative_path(
            f"results/humaneval/{mode}/{baseline}_{execution_model}_cost.json"
        )

        # Set common parameters
        self.max_workers_problems = 50
        self.samples_per_task = max(1, samples_per_task)

        # Define k values for pass@k calculations
        self.k_list = [1]
        if self.samples_per_task > 1:
            possible_k = [min(k, self.samples_per_task) for k in [1, 3, 5, 10]]
            self.k_list = sorted(set(possible_k))

    def filter_code(self, completion: str) -> str:
        """
        Extract Python code from a model's completion.

        Args:
            completion: The model's text completion

        Returns:
            Extracted Python code
        """
        # Try to extract code from a Python code block
        pattern = r"```python\s*(.*?)```"
        match = re.search(pattern, completion, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Also check for just triple backticks without language specification
        pattern = r"```\s*(.*?)```"
        match = re.search(pattern, completion, re.DOTALL)
        if match:
            return match.group(1).strip()

        # If no code block is found, check if the completion looks like raw Python code
        completion = completion.strip()
        if completion.startswith(("def ", "import ", "class ", "\n", "#")):
            return completion

        return completion  # Return whatever we have

    def check_correctness(self, problem: dict, completion: str, timeout: float = 10.0) -> dict:
        """
        Evaluate the functional correctness of a completion by executing the code.

        Args:
            problem: The HumanEval problem
            completion: The code completion to evaluate
            timeout: Maximum execution time in seconds

        Returns:
            Dictionary with evaluation results
        """
        manager = multiprocessing.Manager()
        result = manager.list()  # Shared list to get result back from process

        def unsafe_execute():
            temp_dir_path = None
            original_cwd = os.getcwd()

            try:
                with create_tempdir() as temp_dir_path_context:
                    temp_dir_path = temp_dir_path_context

                    # Keep references locally

                    # Set resource limits
                    reliability_guard()

                    # Construct the check program and run it
                    check_program = (
                        # Add common imports for the execution environment
                        "import math\n"
                        + "import numpy as np\n"
                        + "import re\n"
                        + "import collections\n"
                        + "import itertools\n"
                        + "import functools\n"
                        + "import random\n"
                        + "import string\n"
                        + "import datetime\n"
                        + "import json\n"
                        + "import copy\n"
                        + "from typing import *\n\n"
                        +
                        # Original code follows
                        completion
                        + "\n\n"
                        + problem["test"]
                        + "\n\n"
                        + f"check({problem['entry_point']})"
                    )

                    try:
                        exec_globals = {}
                        with swallow_io():
                            with time_limit(timeout * 0.95):
                                exec(check_program, exec_globals)
                        result.append("passed")
                    except TimeoutException:
                        result.append("timed out")
                    except Exception as e:
                        result.append(f"failed: {type(e).__name__}: {e}")

            except Exception as e:
                result.append(f"execution setup failed: {type(e).__name__}: {e}")
            finally:
                # Cleanup
                try:
                    if original_cwd and os.getcwd() != original_cwd:
                        os.chdir(original_cwd)
                    if temp_dir_path and os.path.exists(temp_dir_path):
                        shutil.rmtree(temp_dir_path, ignore_errors=True)
                except Exception as cleanup_err:
                    print(f"Warning: Error during sandbox cleanup: {cleanup_err}")

                if not result:
                    result.append("subprocess error")

        # Execute the code in a separate process for isolation
        process = multiprocessing.Process(target=unsafe_execute)
        process.start()
        process.join(timeout=timeout + 1)

        if process.is_alive():
            print(
                f"Warning: Killing process for task {problem.get('task_id', 'N/A')} due to timeout."
            )
            process.kill()
            process.join(timeout=1)

        if not result:
            result.append("timed out")

        final_result = result[0] if result else "unknown error"

        # Clean up manager to avoid NFS file lock issues
        try:
            manager.shutdown()
        except Exception:
            pass  # Ignore cleanup errors on NFS

        return {"task_id": problem.get("task_id"), "completion": completion, "result": final_result}

    def compute_pass_at_k(self, n: int, c: int, k: int) -> float:
        """
        Compute pass@k metric.

        Args:
            n: Number of samples
            c: Number of correct samples
            k: K value for pass@k

        Returns:
            pass@k probability
        """
        if c == 0:
            return 0.0
        if n < k:
            return 1.0 if c > 0 else 0.0

        return 1.0 - np.prod([(n - c - i) / (n - i) for i in range(k)])

    def evaluate_problem(
        self, problem: dict, generation_function: Callable, eval_timeout: float = 10.0
    ) -> dict:
        """
        Evaluate a problem using the specified generation function.

        Args:
            problem: The HumanEval problem
            generation_function: Function to generate completions
            eval_timeout: Maximum execution time for evaluation

        Returns:
            Results dictionary for the problem
        """
        prompt = problem["prompt"]
        task_id = problem["task_id"]

        result = {
            "task_id": task_id,
            "prompt": prompt,
            "tests": problem["test"],
            "completions": [],
            "results": [],
            "correct": 0,
            "entry_point": problem["entry_point"],
        }

        try:
            # Generate multiple completions by calling function multiple times in parallel
            design_histories = []
            if generation_function.__name__ == "get_code_workflow":
                # Special case for workflow functions that already handle the problem structure
                completions = generation_function(problem)
                if not isinstance(completions, list):
                    completions = [completions]
            else:
                # Generate multiple completions by calling function multiple times in parallel
                completions = []
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=self.samples_per_task
                ) as executor:
                    futures = [
                        executor.submit(generation_function, prompt)
                        for _ in range(self.samples_per_task)
                    ]
                    for future in concurrent.futures.as_completed(futures):
                        result_data = future.result()
                        if isinstance(result_data, tuple):
                            completion, design_history = result_data
                            completions.append(completion)
                            design_histories.append(design_history)
                        else:
                            completions.append(result_data)
                            design_histories.append(None)

            if completions is None:
                result["correct"] = None
                return result

            # Filter code from completions
            filtered_completions = [self.filter_code(c) for c in completions]

            # Check correctness of each completion in parallel
            eval_results = []
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=len(filtered_completions)
            ) as executor:
                # Create a mapping of futures to completions
                future_to_completion = {}
                for completion in filtered_completions:
                    if not completion:
                        # For empty completions, we don't need to execute anything
                        eval_results.append(
                            {"task_id": task_id, "completion": "", "result": "invalid completion"}
                        )
                    else:
                        # Submit the task to check correctness
                        future = executor.submit(
                            self.check_correctness, problem, completion, eval_timeout
                        )
                        future_to_completion[future] = completion

                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_completion):
                    try:
                        eval_result = future.result(
                            timeout=eval_timeout + 5
                        )  # Add 5 seconds buffer
                        eval_results.append(eval_result)
                    except concurrent.futures.TimeoutError:
                        # Handle timeout in getting the result
                        completion = future_to_completion[future]
                        eval_results.append(
                            {
                                "task_id": task_id,
                                "completion": completion,
                                "result": "executor timeout",
                            }
                        )
                    except Exception as e:
                        # Handle any other exception
                        completion = future_to_completion[future]
                        eval_results.append(
                            {
                                "task_id": task_id,
                                "completion": completion,
                                "result": f"execution error: {str(e)}",
                            }
                        )

            # Count correct completions
            correct = sum(1 for r in eval_results if r["result"] == "passed")

            # Update result
            result["completions"] = filtered_completions
            result["design_histories"] = design_histories
            result["results"] = eval_results
            result["correct"] = correct

            # Calculate pass@k for each k in k_list
            for k in self.k_list:
                result[f"pass@{k}"] = self.compute_pass_at_k(
                    n=len(filtered_completions), c=correct, k=min(k, len(filtered_completions))
                )

        except Exception as e:
            print(f"Error evaluating task {task_id}: {str(e)}")
            result["error"] = str(e)

        return result

    def evaluate_all_problems(
        self, solve_fn: Callable, size: Optional[int] = None, eval_timeout: float = 10.0
    ):
        """
        Evaluate all problems using the specified function.

        Args:
            function: Generation function to use
            size: Number of problems to evaluate (None for all)
            eval_timeout: Maximum execution time for evaluation

        Returns:
            List of evaluation results
        """
        problems = self.load_json(self.dataset_path)
        if size is not None:
            problems = problems[:size]

        results = []
        completed_count = 0

        # Create directory for temporary files
        temp_dir = os.path.dirname(self.output_path)
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, "temp_humaneval_results.json")
        temp_cost_file = os.path.join(temp_dir, "temp_humaneval_cost.json")

        # Load any existing results
        if os.path.exists(temp_file):
            try:
                with open(temp_file, encoding="utf-8") as f:
                    results = json.load(f)
                    completed_count = len(results)
                    print(f"Loaded {completed_count} existing results from {temp_file}")

                    # Filter out completed problems
                    completed_tasks = {r["task_id"] for r in results}
                    problems = [p for p in problems if p["task_id"] not in completed_tasks]
                    print(f"Remaining problems to evaluate: {len(problems)}")
            except Exception as e:
                print(f"Error loading existing results: {e}")
                results = []
                completed_count = 0

        def save_intermediate_results():
            """Save results to temporary file"""
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=4)

        def save_intermediate_cost(generate_service):
            """Save cost information to temporary file"""
            if generate_service:
                generate_cost = generate_service.get_usage_stats()
                with open(temp_cost_file, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "generate_cost": generate_cost,
                            "completed_count": len(results),
                            "timestamp": str(datetime.datetime.now()),
                        },
                        f,
                        indent=4,
                    )

        # Use a fixed number of workers (4) as required
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers_problems
        ) as executor:
            # Submit all jobs to the executor
            future_to_problem = {
                executor.submit(self.evaluate_problem, problem, solve_fn, eval_timeout): problem
                for problem in problems
            }

            # Process results as they complete
            for future in tqdm(
                concurrent.futures.as_completed(future_to_problem),
                total=len(problems),
                desc="Evaluating HumanEval problems",
                initial=completed_count,
                unit="problem",
            ):
                try:
                    result = future.result(timeout=300)  # 5 minute timeout
                    results.append(result)
                    # Save intermediate results
                    save_intermediate_results()
                    # Update cost info periodically
                    if len(results) % 5 == 0:
                        save_intermediate_cost(self.generate_service)
                except concurrent.futures.TimeoutError:
                    problem = future_to_problem[future]
                    print(f"Problem {problem['task_id']} timed out after 300 seconds")
                    result = {
                        "task_id": problem["task_id"],
                        "prompt": problem["prompt"],
                        "tests": problem["test"],
                        "completions": [],
                        "results": [],
                        "correct": 0,
                        "error": "Evaluation timed out",
                    }
                    results.append(result)
                    save_intermediate_results()
                except Exception as exc:
                    problem = future_to_problem[future]
                    print(f"Problem {problem['task_id']} generated an exception: {exc}")
                    result = {
                        "task_id": problem["task_id"],
                        "prompt": problem["prompt"],
                        "tests": problem["test"],
                        "completions": [],
                        "results": [],
                        "correct": 0,
                        "error": str(exc),
                    }
                    results.append(result)
                    save_intermediate_results()

        # Final save of cost information
        save_intermediate_cost(self.generate_service)

        print(f"Evaluation complete. Total HumanEval problems evaluated: {len(results)}")
        return results

    def calculate_metrics(self, results=None):
        """
        Calculate and print the benchmark metrics.

        Args:
            results: Results to calculate metrics for (None to load from file)

        Returns:
            Dictionary with average pass@k values for each k
        """
        if results is None:
            with open(self.output_path, encoding="utf-8") as f:
                results = json.load(f)

        total_problems = 0
        for result in results:
            if result["completions"] != []:
                total_problems += 1
        # Track pass@k metrics
        pass_at_k = dict.fromkeys(self.k_list, 0)

        # Calculate total pass@k for each k
        for result in results:
            for k in self.k_list:
                if f"pass@{k}" in result:
                    pass_at_k[k] += result[f"pass@{k}"]

        # Calculate average pass@k
        avg_pass_at_k = {k: pass_at_k[k] / total_problems for k in self.k_list}

        # Print metrics
        print("\nBenchmark: HumanEval")
        print(f"Baseline: {self.baseline}")
        print(f"Execution Model: {self.execution_model}")
        print(f"Total Problems: {total_problems}")
        print(f"Number of samples per task: {self.samples_per_task}")

        for k in sorted(self.k_list):
            print(f"Pass@{k}: {avg_pass_at_k[k]:.4f}")

        return avg_pass_at_k

    def record_cost(self, judge_service: Optional[ModelService] = None):
        """Record usage statistics when services are provided."""
        if not self.cost_path:
            return

        generate_cost = self.generate_service.get_usage_stats() if self.generate_service else {}

        executor_stats = {}
        if hasattr(self, "executor_service") and self.executor_service is not None:
            executor_stats = self.executor_service.get_usage_stats()

        judge_cost = {} if judge_service is None else judge_service.get_usage_stats()

        with open(self.cost_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "generate_cost": generate_cost,
                    "judge_cost": judge_cost,
                    "executor_cost": executor_stats,
                    "timestamp": str(datetime.datetime.now()),
                },
                f,
                indent=4,
            )

    def run(
        self,
        solve_fn: Callable[[dict[str, Any]], Any],
        judge_service: Optional[ModelService] = None,
        *,
        generate_service: Optional[ModelService] = None,
        executor_service: Optional[ModelService] = None,
        size: Optional[int] = None,
        max_workers: int = 4,
        pass_k: Optional[int] = None,
    ):
        """
        Run the HumanEval benchmark.

        Args:
            solve_fn: Callable that runs DyFlow and returns a solution payload
            judge_service: Optional judge model service for scoring solutions
            generate_service: Optional service used inside solve_fn for cost accounting
            executor_service: Optional executor service for cost accounting
            size: Number of problems to evaluate (None for all)
            max_workers: Maximum number of worker threads (defaults to 4)
            pass_k: Maximum k for pass@k calculations (None for just pass@1, int for pass@1 to pass@k)

        Returns:
            List of evaluation results
        """
        if solve_fn is None:
            raise ValueError("solve_fn must be provided for DyFlow evaluation.")

        # Ensure output directory exists
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        self.generate_service = generate_service
        self.executor_service = executor_service

        # Update k_list based on pass_k parameter
        if pass_k is not None and pass_k > 1:
            if self.samples_per_task < pass_k:
                self.samples_per_task = pass_k
                print(f"Increased samples_per_task to {pass_k} to support pass@{pass_k}")

            # Set k_list to include values from 1 to pass_k
            self.k_list = list(range(1, pass_k + 1))

        # Update max_workers if provided
        self.max_workers_problems = max_workers

        # Evaluate all problems
        results = self.evaluate_all_problems(solve_fn, size=size, eval_timeout=10.0)

        # Save final results
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4)

        # Record final cost if any services were supplied
        self.record_cost(judge_service)

        # Clean up temporary files
        temp_dir = os.path.dirname(self.output_path)
        temp_file = os.path.join(temp_dir, "temp_humaneval_results.json")
        temp_cost_file = os.path.join(temp_dir, "temp_humaneval_cost.json")

        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                print(f"Temporary HumanEval results file removed: {temp_file}")

            if os.path.exists(temp_cost_file):
                os.remove(temp_cost_file)
                print(f"Temporary HumanEval cost file removed: {temp_cost_file}")
        except Exception as e:
            print(f"Warning: Failed to remove temporary HumanEval files: {e}")

        self.calculate_metrics(results)

        return results
