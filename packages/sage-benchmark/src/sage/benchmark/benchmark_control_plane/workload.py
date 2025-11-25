"""
Workload Generation Module
==========================

Generates request sequences for benchmarking Control Plane scheduling policies.

This module provides:
- WorkloadGenerator: Main workload generation class
- Request: Dataclass representing a benchmark request
- Support for synthetic and dataset-based workloads
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .config import BenchmarkConfig


@dataclass
class Request:
    """A single benchmark request.

    Attributes:
        request_id: Unique request identifier
        model_name: Target model for this request
        prompt: Request prompt text
        max_tokens: Maximum tokens to generate
        priority: Request priority (HIGH, NORMAL, LOW)
        slo_deadline_ms: SLO deadline in milliseconds
        scheduled_arrival_time: Planned arrival time relative to benchmark start (seconds)
        temperature: Sampling temperature
        top_p: Top-p sampling parameter
    """

    request_id: str
    model_name: str
    prompt: str
    max_tokens: int
    priority: str
    slo_deadline_ms: int
    scheduled_arrival_time: float
    temperature: float = 0.7
    top_p: float = 0.95
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert request to dictionary format."""
        return {
            "request_id": self.request_id,
            "model_name": self.model_name,
            "prompt": self.prompt,
            "max_tokens": self.max_tokens,
            "priority": self.priority,
            "slo_deadline_ms": self.slo_deadline_ms,
            "scheduled_arrival_time": self.scheduled_arrival_time,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "metadata": self.metadata,
        }


# Template prompts for synthetic workload generation
SYNTHETIC_PROMPTS = [
    "Explain the concept of {topic} in simple terms.",
    "Write a short summary about {topic}.",
    "What are the key points to understand about {topic}?",
    "Describe the main features of {topic}.",
    "How does {topic} work in practice?",
    "Compare and contrast {topic} with related concepts.",
    "What are the benefits and drawbacks of {topic}?",
    "Provide an example that illustrates {topic}.",
]

TOPICS = [
    "machine learning",
    "neural networks",
    "distributed systems",
    "cloud computing",
    "database optimization",
    "software architecture",
    "API design",
    "data structures",
    "algorithms",
    "system design",
    "microservices",
    "containerization",
    "DevOps practices",
    "continuous integration",
    "load balancing",
]


class WorkloadGenerator:
    """Generates benchmark workloads based on configuration.

    This class creates a sequence of requests with:
    - Configurable arrival patterns (uniform, Poisson, burst)
    - Model distribution according to configuration
    - Priority distribution according to configuration
    - Synthetic or dataset-based prompts
    """

    def __init__(self, config: BenchmarkConfig, seed: int | None = None):
        """Initialize workload generator.

        Args:
            config: Benchmark configuration
            seed: Random seed for reproducibility
        """
        self.config = config
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)

    def generate(self) -> list[Request]:
        """Generate a list of requests according to configuration.

        Returns:
            List of Request objects with scheduled arrival times
        """
        requests = []
        arrival_times = self._generate_arrival_times()

        for i, arrival_time in enumerate(arrival_times):
            request = self._generate_single_request(i, arrival_time)
            requests.append(request)

        return requests

    def _generate_arrival_times(self) -> list[float]:
        """Generate arrival times based on configured pattern.

        Returns:
            List of arrival times in seconds from start
        """
        n = self.config.num_requests

        if self.config.arrival_pattern.value == "uniform":
            # Uniform inter-arrival times
            inter_arrival = 1.0 / self.config.request_rate
            times = [i * inter_arrival for i in range(n)]

        elif self.config.arrival_pattern.value == "poisson":
            # Poisson arrivals (exponential inter-arrival times)
            mean_inter_arrival = 1.0 / self.config.request_rate
            inter_arrivals = self.np_rng.exponential(mean_inter_arrival, n)
            times = list(np.cumsum(inter_arrivals))

        elif self.config.arrival_pattern.value == "burst":
            # Burst pattern: alternating bursts and quiet periods
            times = []
            current_time = 0.0
            burst_size = max(1, n // 10)
            burst_rate = self.config.request_rate * 5  # 5x rate during burst
            quiet_rate = self.config.request_rate / 2  # 0.5x rate during quiet

            i = 0
            in_burst = True
            while i < n:
                if in_burst:
                    # Generate burst of requests
                    burst_count = min(burst_size, n - i)
                    for _ in range(burst_count):
                        times.append(current_time)
                        current_time += 1.0 / burst_rate
                        i += 1
                    in_burst = False
                else:
                    # Quiet period
                    quiet_count = min(burst_size // 2, n - i)
                    for _ in range(quiet_count):
                        times.append(current_time)
                        current_time += 1.0 / quiet_rate
                        i += 1
                    in_burst = True

        else:
            # Default to uniform
            inter_arrival = 1.0 / self.config.request_rate
            times = [i * inter_arrival for i in range(n)]

        return times

    def _generate_single_request(self, index: int, arrival_time: float) -> Request:
        """Generate a single request.

        Args:
            index: Request index
            arrival_time: Scheduled arrival time

        Returns:
            Generated Request object
        """
        # Sample model
        model_name = self._sample_from_distribution(self.config.model_distribution)

        # Sample priority
        priority = self._sample_from_distribution(self.config.priority_distribution)

        # Get SLO deadline for priority
        slo_deadline_ms = self.config.slo_config.get_deadline_for_priority(priority)

        # Generate prompt
        prompt = self._generate_prompt()

        # Sample output length
        max_tokens = self.rng.randint(
            self.config.output_len_range[0],
            self.config.output_len_range[1],
        )

        return Request(
            request_id=str(uuid.uuid4()),
            model_name=model_name,
            prompt=prompt,
            max_tokens=max_tokens,
            priority=priority,
            slo_deadline_ms=slo_deadline_ms,
            scheduled_arrival_time=arrival_time,
            metadata={"index": index},
        )

    def _sample_from_distribution(self, distribution: dict[str, float]) -> str:
        """Sample a key from a probability distribution.

        Args:
            distribution: Dictionary mapping keys to probabilities

        Returns:
            Sampled key
        """
        keys = list(distribution.keys())
        probs = list(distribution.values())
        return self.rng.choices(keys, weights=probs, k=1)[0]

    def _generate_prompt(self) -> str:
        """Generate a synthetic prompt.

        Returns:
            Generated prompt string
        """
        # If dataset path is configured, load from dataset
        if self.config.dataset_path and self.config.dataset_path.exists():
            return self._load_prompt_from_dataset()

        # Generate synthetic prompt
        template = self.rng.choice(SYNTHETIC_PROMPTS)
        topic = self.rng.choice(TOPICS)
        base_prompt = template.format(topic=topic)

        # Extend to target length
        target_len = self.rng.randint(
            self.config.prompt_len_range[0],
            self.config.prompt_len_range[1],
        )

        # Estimate tokens (rough: ~4 chars per token)
        current_tokens = len(base_prompt) // 4

        if current_tokens < target_len:
            # Add padding context
            padding_phrases = [
                f" Please provide a detailed explanation.",
                f" Consider various perspectives and examples.",
                f" Include practical applications where relevant.",
                f" Discuss both advantages and limitations.",
                f" Structure your response clearly with key points.",
            ]

            while current_tokens < target_len and padding_phrases:
                phrase = self.rng.choice(padding_phrases)
                base_prompt += phrase
                current_tokens = len(base_prompt) // 4
                padding_phrases.remove(phrase)

        return base_prompt

    def _load_prompt_from_dataset(self) -> str:
        """Load a prompt from the configured dataset.

        Returns:
            Prompt string from dataset
        """
        # Placeholder for dataset loading
        # In a full implementation, this would load from ShareGPT or similar datasets
        return self._generate_prompt()


class ShareGPTLoader:
    """Loader for ShareGPT dataset format.

    This is a placeholder for future implementation of dataset loading.
    ShareGPT format typically contains conversations in JSON format.
    """

    def __init__(self, dataset_path: str):
        """Initialize dataset loader.

        Args:
            dataset_path: Path to the dataset file
        """
        self.dataset_path = dataset_path
        self.prompts: list[str] = []
        self._loaded = False

    def load(self) -> None:
        """Load prompts from dataset file."""
        # Placeholder implementation
        # In production, this would parse the ShareGPT JSON format
        self._loaded = True

    def get_random_prompt(self, rng: random.Random) -> str:
        """Get a random prompt from the dataset.

        Args:
            rng: Random number generator

        Returns:
            Random prompt from dataset
        """
        if not self._loaded:
            self.load()

        if not self.prompts:
            return "No prompts available in dataset."

        return rng.choice(self.prompts)
