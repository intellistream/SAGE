import concurrent.futures
import datetime
import json
import os
import re
import sys

import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from typing import Callable, Optional

from dyflow.model_service import ModelService
from tqdm import tqdm

from .framework import BaseBenchmark, get_relative_path


class LiveBenchBenchmark(BaseBenchmark):
    def __init__(self, execution_model: str, baseline: str, mode: str):
        """
        Initialize the LiveBench benchmark.

        Args:
            execution_model: Name of the model to use for generating solutions
            baseline: Baseline method to use
            mode: Evaluation mode
        """
        super().__init__(execution_model, baseline, mode)

        self.generate_service = None
        self.dataset_path = get_relative_path(f"data/livebench/livebench_{mode}.json")
        self.output_path = get_relative_path(
            f"results/livebench/{mode}/{baseline}_{execution_model}.json"
        )
        self.cost_path = get_relative_path(
            f"results/livebench/{mode}/{baseline}_{execution_model}_cost.json"
        )

        # Define executor service
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

    def judge_prompt(self, question: str, solution: str, ground_truth: str) -> str:
        """
        Generate the prompt for judging a solution against the ground truth.

        Args:
            question: The problem text
            solution: The solution to evaluate
            ground_truth: The correct solution

        Returns:
            Formatted prompt for the judge model
        """
        return (
            "You are an expert evaluator. Here is a problem and two solutions. Please evaluate if the given solution's answer "
            "is equivalent to the ground truth solution's answer. Consider the following rules:\n\n"
            "1. Ignore spacing and formatting differences\n"
            "2. Accept different but logically equivalent expressions\n"
            "3. Exact matching is required for unambiguous answers\n"
            f"Problem:\n{question}\n\n"
            f"Ground Truth Solution:\n{ground_truth}\n\n"
            f"Given Solution:\n{solution}\n\n"
            "Please first explain your reasoning and then respond with [[True]] if correct or [[False]] if incorrect. "
        )

    def evaluate_problem(self, problem: dict, function: Callable, judge_service=None) -> dict:
        """
        Evaluate a single problem using the specified function and judge service.

        Args:
            problem: The problem dictionary
            function: The function to use for generating solutions
            judge_service: The service to use for judging solutions

        Returns:
            The problem dictionary with evaluation results added
        """
        question = problem["turns"][0]
        ground_truth = problem["ground_truth"]

        # Generate multiple answers by calling function multiple times in parallel
        answers = []
        design_histories = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.samples_per_task) as executor:
            futures = [executor.submit(function, question) for _ in range(self.samples_per_task)]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if isinstance(result, tuple):
                    answer, design_history = result
                    answers.append(answer)
                    design_histories.append(design_history)
                else:
                    answers.append(result)
                    design_histories.append(None)

        # Initialize results for pass@k
        judge_results = []

        # Evaluate each completion in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(answers)) as executor:
            # Create a mapping of futures to answers
            future_to_answer = {}

            for answer in answers:
                if answer is None:
                    judge_results.append(False)
                else:
                    judge_prompt = self.judge_prompt(question, answer, ground_truth)
                    future = executor.submit(judge_service.generate, judge_prompt)
                    future_to_answer[future] = answer

            # Process judge results
            for future in concurrent.futures.as_completed(future_to_answer):
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
        problem["generated_solutions"] = answers
        problem["design_histories"] = design_histories
        problem["judge_results"] = judge_results
        problem["correct"] = correct
        problem["total"] = total
        problem.update(pass_at_k)

        # Also store the first solution for backwards compatibility
        problem["generated_solution"] = answers[0] if answers else None
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
            function: The function to use for generating solutions
            judge_service: The service to use for judging solutions
            generate_service: The service used to generate solutions
            max_workers: Maximum number of concurrent workers
            size: Optional limit on the number of problems to evaluate

        Returns:
            List of evaluated problems with results
        """
        problems = self.load_json(self.dataset_path)
        if size is not None:
            problems = problems[:size]
        results = []
        completed_count = 0

        # Create temporary directory and files for saving intermediate results
        temp_dir = os.path.dirname(self.output_path)
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, f"temp_{self.mode}_livebench_results.json")
        temp_cost_file = os.path.join(temp_dir, f"temp_{self.mode}_livebench_cost.json")

        # If temporary file exists, load completed results
        if os.path.exists(temp_file):
            try:
                with open(temp_file, encoding="utf-8") as f:
                    results = json.load(f)
                    completed_count = len(results)
                    print(f"Loaded {completed_count} existing results from {temp_file}")

                    # Create a set of completed problem IDs for quick lookup
                    completed_problems = {r.get("question_id", "") for r in results}
                    # Filter out already completed problems
                    problems = [
                        p for p in problems if p.get("question_id", "") not in completed_problems
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
                desc=f"Evaluating {self.mode} LiveBench problems",
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
                    print(f"Problem {problem.get('question_id', '')} timed out after 300 seconds")
                    problem["generated_solution"] = None
                    problem["original_judge_output"] = None
                    problem["judge_result"] = False
                    problem["error"] = "Evaluation timed out"
                    results.append(problem)
                    save_intermediate_results()
                except Exception as exc:
                    problem = future_to_problem[future]
                    print(f"Problem {problem.get('question_id', '')} generated an exception: {exc}")
                    problem["generated_solution"] = None
                    problem["original_judge_output"] = None
                    problem["judge_result"] = False
                    problem["error"] = str(exc)
                    results.append(problem)
                    save_intermediate_results()

        # Final save of cost information
        save_intermediate_cost(generate_service, judge_service)

        print(f"Evaluation complete. Total LiveBench problems evaluated: {len(results)}")
        return results

    def calculate_metrics(self, results=None):
        """
        Calculate and print the benchmark metrics.

        Args:
            results: Results to calculate metrics for (None to load from file)

        Returns:
            Dictionary with metrics including pass@k values
        """
        if results is None:
            try:
                with open(self.output_path, encoding="utf-8") as f:
                    results = json.load(f)
            except FileNotFoundError:
                print(f"警告: 结果文件 {self.output_path} 不存在")
                return {"accuracy": 0, "error": "结果文件不存在"}

        total = 0
        acc = 0
        category_metrics = {}

        # Track pass@k metrics
        pass_at_k = dict.fromkeys(self.k_list, 0)
        pass_at_k_count = 0

        for result in results:
            if result.get("generated_solution") is not None:
                total += 1
                category = result.get("category", "unknown")
                if category not in category_metrics:
                    category_metrics[category] = {"total": 0, "correct": 0}

                category_metrics[category]["total"] += 1

                if result.get("judge_result"):
                    acc += 1
                    category_metrics[category]["correct"] += 1

                # Track pass@k if available
                if "total" in result and result.get("total", 0) > 0:
                    pass_at_k_count += 1
                    for k in self.k_list:
                        key = f"pass@{k}"
                        if key in result:
                            pass_at_k[k] += result[key]

        print("Benchmark: LiveBench")
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

        # Print per-category metrics
        print("\nPerformance by category:")
        for category, metrics in category_metrics.items():
            cat_acc = metrics["correct"] / metrics["total"] if metrics["total"] > 0 else 0
            print(f"  {category}: {cat_acc:.4f} ({metrics['correct']}/{metrics['total']})")

        # Prepare return metrics
        metrics_result = {
            "accuracy": acc / total if total > 0 else 0,
            "categories": category_metrics,
        }

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
            generate_service: The service used to generate solutions
            judge_service: The service used to judge solutions
            function: Optional specific function to use for evaluation
            size: Optional limit on the number of problems to evaluate
            max_workers: Maximum number of concurrent workers
            pass_k: Maximum k for pass@k calculations (None for default, int for pass@1 to pass@k)

        Returns:
            List of evaluated problems with results
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
            raise ValueError("function parameter is required for LiveBenchBenchmark.run()")
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
        temp_file = os.path.join(temp_dir, f"temp_{self.mode}_livebench_results.json")
        temp_cost_file = os.path.join(temp_dir, f"temp_{self.mode}_livebench_cost.json")

        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                print(f"Temporary LiveBench results file removed: {temp_file}")

            if os.path.exists(temp_cost_file):
                os.remove(temp_cost_file)
                print(f"Temporary LiveBench cost file removed: {temp_cost_file}")
        except Exception as e:
            print(f"Warning: Failed to remove temporary LiveBench files: {e}")

        self.calculate_metrics(results)

        return results

    def extract_judge_result(self, output: str) -> bool:
        """
        Extract the judge result from the output.

        Args:
            output: The judge model's output

        Returns:
            Boolean indicating if the solution is correct
        """
        if "[[True]]" in output:
            return True
        elif "[[False]]" in output:
            return False
        else:
            # Try to find True/False with regex
            pattern = r"\[\[(\w+)\]\]"
            match = re.search(pattern, output)
            if match:
                result = match.group(1).lower()
                return result == "true"
            return False

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
