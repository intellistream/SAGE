import concurrent.futures
import datetime
import json
import os
import sys

import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from typing import Callable, Optional

from dyflow.model_service import ModelService
from tqdm import tqdm

from .framework import BaseBenchmark, get_relative_path


class SocialMazeBenchmark(BaseBenchmark):
    def __init__(self, execution_model: str, baseline: str, mode: str):
        """
        Initialize the Social Reasoning benchmark.

        Args:
            execution_model: Name of the model to use for generating solutions
            baseline: Baseline method to use
            mode: Evaluation mode
        """
        super().__init__(execution_model, baseline, mode)

        self.generate_service = None
        self.dataset_path = get_relative_path(f"data/socialmaze/socialmaze_{mode}.json")
        self.output_path = get_relative_path(
            f"results/socialmaze/{mode}/{baseline}_{execution_model}.json"
        )
        self.cost_path = get_relative_path(
            f"results/socialmaze/{mode}/{baseline}_{execution_model}_cost.json"
        )

        self.executor_service = None

        # Define default samples per task (can be overridden by pass_k parameter)
        # Default to 5 for Self_Consistency_CoT, 1 for other baselines
        self.samples_per_task = 5 if baseline == "Self_Consistency_CoT" else 1

        # Define k values for pass@k calculations
        self.k_list = [1]
        if self.samples_per_task > 1:
            # Add reasonable k values based on samples_per_task
            possible_k = [min(k, self.samples_per_task) for k in [1, 3, 5]]
            self.k_list = sorted(set(possible_k))

    def judge_prompt(self, problem: str, solution: str, ground_truth: str) -> str:
        """
        Generate the prompt for judging a solution against the ground truth.

        Args:
            solution: The solution to evaluate
            ground_truth: The correct solution

        Returns:
            Formatted prompt for the judge model
        """
        return (
            "You are a social reasoning expert. Here is a social reasoning problem and two solutions. Please evaluate if the given solution is correct.\n\n"
            f"Ground truth: {ground_truth}\n\n"
            f"Solution: {solution}\n\n"
            "If this solution can infer both the Final Criminal and My role, then it is correct. If any of them is wrong, it is not correct.\n"
            "That means, the Final Criminal number must be the same as the ground truth, and My role must be the same as the ground truth. Investigator, Rumormonger, Lunatic, Criminal are different roles.\n Only if the solution can exactly match the Final Criminal number and My role (one of Investigator, Rumormonger, Lunatic, Criminal), it is correct. Otherwise, it is incorrect.\n"
            "If the solution provide unknown in the Final Criminal number or My role, it is [[False]].\n"
            "Please first explain your reasoning and then respond with [[True]] if correct or [[False]] if incorrect."
        )

    def evaluate_problem(self, problem: dict, function: Callable, judge_service=None) -> dict:
        """
        Evaluate a single problem using the given function and judge service.

        Args:
            problem: The problem dictionary

        Returns:
            Dictionary containing the problem, solution, and judge result
        """
        question = (
            problem["system_prompt"]
            + problem["prompt"]
            + "You must output the Final Criminal number and your role in the format of 'Final Criminal: <number>, My role: <role>' in the end of your response. Don't give unknown!"
        )
        ground_truth = problem["Answer"]

        # Generate multiple solutions by calling function multiple times in parallel
        solutions = []
        design_histories = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.samples_per_task) as executor:
            futures = [executor.submit(function, question) for _ in range(self.samples_per_task)]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if isinstance(result, tuple):
                    solution, design_history = result
                    solutions.append(solution)
                    design_histories.append(design_history)
                else:
                    solutions.append(result)
                    design_histories.append(None)

        # Initialize results for pass@k
        judge_results = []

        # Evaluate each completion in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(solutions)) as executor:
            # Create a mapping of futures to solutions
            future_to_solution = {}

            for solution in solutions:
                if solution is None:
                    judge_results.append(False)
                else:
                    judge_prompt = self.judge_prompt(problem, solution, ground_truth)
                    future = executor.submit(judge_service.generate, judge_prompt, temperature=0.1)
                    future_to_solution[future] = solution

            # Process judge results
            for future in concurrent.futures.as_completed(future_to_solution):
                try:
                    judge_output = future.result()["response"]
                    judge_result = self.extract_judge_result(output=judge_output)
                    judge_results.append(judge_result)
                except Exception as e:
                    print(f"Error judging solution: {str(e)}")
                    judge_results.append(False)

        # Calculate pass@k metrics
        correct = sum(1 for r in judge_results if r)
        total = len(judge_results)

        # Add pass@k calculations
        pass_at_k = {}
        for k in self.k_list:
            if total >= k:
                pass_at_k[f"pass@{k}"] = self.compute_pass_at_k(n=total, c=correct, k=k)

        # Store results
        problem["generated_solutions"] = solutions
        problem["design_histories"] = design_histories
        problem["judge_results"] = judge_results
        problem["correct"] = correct
        problem["total"] = total
        problem.update(pass_at_k)

        # Also store the first solution for backwards compatibility
        problem["generated_solution"] = solutions[0] if solutions else None
        problem["judge_result"] = judge_results[0] if judge_results else False

        return problem

    def evaluate_all_problems(
        self,
        function: Callable,
        judge_service=None,
        generate_service=None,
        max_workers: int = 10,
        size: int = None,
    ):
        """
        Evaluate all problems in the dataset.

        Args:
            function: The function to generate solutions
            judge_service: The service to judge solutions
            generate_service: The service to generate solutions
            max_workers: Maximum number of concurrent workers
            size: Number of problems to evaluate

        Returns:
            List of problem dicts with evaluation results
        """
        problems = self.load_json(self.dataset_path)
        if size is not None:
            problems = problems[:size]
        results = []
        completed_count = 0

        # Create temporary directory and files for saving intermediate results
        temp_dir = os.path.dirname(self.output_path)
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, f"temp_{self.mode}_socialreasoning_results.json")
        temp_cost_file = os.path.join(temp_dir, f"temp_{self.mode}_socialreasoning_cost.json")

        # If temporary file exists, load completed results
        if os.path.exists(temp_file):
            try:
                with open(temp_file, encoding="utf-8") as f:
                    results = json.load(f)
                    completed_count = len(results)
                    print(f"Loaded {completed_count} existing results from {temp_file}")

                    # Create a set of completed problem IDs for quick lookup
                    # Using problem text as ID
                    completed_problems = {r.get("prompt", "")[:50] for r in results}
                    # Filter out already completed problems
                    problems = [
                        p for p in problems if p.get("prompt", "")[:50] not in completed_problems
                    ]
                    print(f"Remaining problems to evaluate: {len(problems)}")
            except Exception as e:
                print(f"Error loading existing results: {e}")
                # Reset in case of loading error
                results = []
                completed_count = 0

        def save_intermediate_results():
            """Save results to a temporary file after each problem"""
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=4)

        def save_intermediate_cost(generate_service, judge_service):
            """Save current cost information to a temporary file"""
            if generate_service and judge_service:
                generate_cost = generate_service.get_usage_stats()
                judge_cost = judge_service.get_usage_stats()
                # Get executor stats if available
                executor_stats = (
                    self.executor_service.get_usage_stats()
                    if self.executor_service is not None
                    else {}
                )
                with open(temp_cost_file, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "generate_cost": generate_cost,
                            "judge_cost": judge_cost,
                            "executor_cost": executor_stats,
                            "mode": self.mode,
                            "completed_count": len(results),
                            "timestamp": str(datetime.datetime.now()),
                        },
                        f,
                        indent=4,
                    )

        # Process all problems with multithreading
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all jobs to the executor
            future_to_problem = {
                executor.submit(self.evaluate_problem, problem, function, judge_service): problem
                for problem in problems
            }

            # Process results as they complete
            for future in tqdm(
                concurrent.futures.as_completed(future_to_problem),
                total=len(problems),
                desc=f"Evaluating {self.mode} social reasoning problems",
                initial=completed_count,
                unit="problem",
            ):
                try:
                    result = future.result(timeout=300)  # 5 minute timeout
                    results.append(result)
                    # Save after each result
                    save_intermediate_results()
                    # Update cost info periodically (every 5 problems)
                    if len(results) % 5 == 0:
                        save_intermediate_cost(generate_service, judge_service)
                except concurrent.futures.TimeoutError:
                    problem = future_to_problem[future]
                    print(f"Problem {problem['prompt'][:50]}... timed out after 300 seconds")
                    problem["generated_solution"] = None
                    problem["original_judge_output"] = None
                    problem["judge_result"] = False
                    problem["error"] = "Evaluation timed out"
                    results.append(problem)
                    save_intermediate_results()
                except Exception as exc:
                    problem = future_to_problem[future]
                    print(f"Problem {problem['prompt'][:50]}... generated an exception: {exc}")
                    problem["generated_solution"] = None
                    problem["original_judge_output"] = None
                    problem["judge_result"] = False
                    problem["error"] = str(exc)
                    results.append(problem)
                    save_intermediate_results()

        # Final save of cost information
        save_intermediate_cost(generate_service, judge_service)

        print(f"Evaluation complete. Total social reasoning problems evaluated: {len(results)}")
        return results

    def calculate_metrics(self, results=None):
        """
        Calculate evaluation metrics from the results.

        Args:
            results: Results to calculate metrics for (None to load from file)

        Returns:
            Dictionary with average pass@k values for each k
        """
        if results is None:
            with open(self.output_path, encoding="utf-8") as f:
                results = json.load(f)

        total = 0
        acc = 0

        # Track pass@k metrics
        pass_at_k = dict.fromkeys(self.k_list, 0)
        pass_at_k_count = 0

        for result in results:
            if result.get("generated_solution") is not None:
                total += 1
                if result.get("judge_result"):
                    acc += 1

                # Track pass@k if available
                if "total" in result and result.get("total", 0) > 0:
                    pass_at_k_count += 1
                    for k in self.k_list:
                        key = f"pass@{k}"
                        if key in result:
                            pass_at_k[k] += result[key]

        print("Benchmark: SocialMaze")
        print(f"Mode: {self.mode}")
        print(f"Baseline: {self.baseline}")
        print(f"Execution Model: {self.execution_model}")
        print(f"Total: {total}")
        print(f"Accuracy: {acc / total if total > 0 else 0}")

        # Calculate average pass@k metrics
        avg_pass_at_k = {}
        if pass_at_k_count > 0:
            avg_pass_at_k = {k: pass_at_k[k] / pass_at_k_count for k in self.k_list}
            print(f"\nPass@k Metrics (samples per task: {self.samples_per_task}):")
            for k in sorted(self.k_list):
                print(f"Pass@{k}: {avg_pass_at_k[k]:.4f}")

        # Prepare return metrics
        metrics_result = {"accuracy": acc / total if total > 0 else 0}

        # Add pass@k to return values
        if pass_at_k_count > 0:
            metrics_result.update(avg_pass_at_k)

        return metrics_result

    def record_cost(self, generate_service: ModelService, judge_service: ModelService):
        """
        Record the cost of using the model services.

        Args:
            generate_service: The service used to generate solutions
            judge_service: The service used to judge solutions
        """
        generate_cost = generate_service.get_usage_stats()
        judge_cost = judge_service.get_usage_stats()

        # Get executor stats if available
        executor_stats = (
            self.executor_service.get_usage_stats() if self.executor_service is not None else {}
        )

        with open(self.cost_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "generate_cost": generate_cost,
                    "judge_cost": judge_cost,
                    "executor_cost": executor_stats,
                    "mode": self.mode,
                    "timestamp": str(datetime.datetime.now()),
                },
                f,
                indent=4,
            )

    def run(
        self,
        generate_service: ModelService,
        judge_service: ModelService,
        function: Callable = None,
        size: int = None,
        max_workers: int = 10,
        pass_k: Optional[int] = None,
    ):
        """
        Run the benchmark evaluation.

        Args:
            generate_service: The service to generate solutions
            judge_service: The service to judge solutions
            function: The function to use for generating solutions
            size: Number of problems to evaluate
            max_workers: Maximum number of concurrent workers
            pass_k: Maximum k for pass@k calculations (None for default, int for pass@1 to pass@k)

        Returns:
            List of problem dicts with evaluation results
        """
        # Ensure output directory exists
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        self.generate_service = generate_service

        # Update k_list and samples_per_task based on pass_k parameter
        if pass_k is not None and pass_k > 1:
            # Make sure samples_per_task is sufficient
            if self.samples_per_task < pass_k:
                self.samples_per_task = pass_k
                print(f"Increased samples_per_task to {pass_k} to support pass@{pass_k}")

            # Set k_list to include values from 1 to pass_k
            self.k_list = list(range(1, pass_k + 1))

        if function is None:
            raise ValueError("function parameter is required for SocialMazeBenchmark.run()")

        # Evaluate all problems
        results = self.evaluate_all_problems(
            function, judge_service, generate_service, size=size, max_workers=max_workers
        )

        # Save final results
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4)

        # Record final cost
        self.record_cost(generate_service, judge_service)

        # If everything was successful, clean up temporary files
        temp_dir = os.path.dirname(self.output_path)
        temp_file = os.path.join(temp_dir, f"temp_{self.mode}_socialreasoning_results.json")
        temp_cost_file = os.path.join(temp_dir, f"temp_{self.mode}_socialreasoning_cost.json")

        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                print(f"Temporary social reasoning results file removed: {temp_file}")

            if os.path.exists(temp_cost_file):
                os.remove(temp_cost_file)
                print(f"Temporary social reasoning cost file removed: {temp_cost_file}")
        except Exception as e:
            print(f"Warning: Failed to remove temporary social reasoning files: {e}")

        self.calculate_metrics(results)

        return results

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
