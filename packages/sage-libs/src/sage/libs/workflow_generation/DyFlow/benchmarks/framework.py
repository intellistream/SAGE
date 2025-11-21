import json
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Callable


def get_relative_path(file_path: str) -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, file_path)


class BaseBenchmark(ABC):
    def __init__(self, execution_model: str, baseline: str, mode: str):
        self.execution_model = execution_model
        self.baseline = baseline
        self.mode = mode

    @abstractmethod
    def evaluate_problem(self, problem: dict, function: Callable, judge_service=None) -> dict:
        pass

    @abstractmethod
    def evaluate_all_problems(
        self, function: Callable, size: int = None, judge_service=None, max_workers: int = 10
    ):
        pass

    @abstractmethod
    def calculate_metrics(self) -> tuple[Any, ...]:
        pass

    @staticmethod
    def write_results(results: list[dict], output_path: str):
        with open(output_path, "w") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

    @staticmethod
    def extract_judge_result(output: str) -> bool:
        """
        Extract the boolean value between [[True]] and [[False]] from the judge's output.

        Args:
            output: The judge model's output

        Returns:
            Boolean indicating if the solution is correct

        Raises:
            ValueError: If no boolean value is found in the output
        """
        match = re.search(r"\[\[True\]\]|\[\[False\]\]", output)
        if match:
            return match.group(0) == "[[True]]"
        else:
            raise ValueError("No boolean value found in the output.")

    @staticmethod
    def load_json(dataset_path: str) -> list[dict]:
        with open(dataset_path, encoding="utf-8") as f:
            return json.load(f)
