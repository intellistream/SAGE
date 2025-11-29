# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Hybrid Workload Generation Module
==================================

Generates mixed LLM and Embedding request sequences for benchmarking
hybrid scheduling policies.

This module provides:
- HybridRequest: Dataclass representing a hybrid benchmark request
- HybridWorkloadGenerator: Main workload generation class for mixed workloads
- Support for synthetic and dataset-based workloads
"""

from __future__ import annotations

import json
import random
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from .config import RequestType

if TYPE_CHECKING:
    from .config import HybridBenchmarkConfig


@dataclass
class HybridRequest:
    """A single hybrid benchmark request (LLM or Embedding).

    Attributes:
        request_id: Unique request identifier
        request_type: Type of request (llm_chat, llm_generate, embedding)
        priority: Request priority (HIGH, NORMAL, LOW)
        slo_deadline_ms: SLO deadline in milliseconds
        scheduled_arrival_time: Planned arrival time relative to benchmark start (seconds)

        # LLM-specific fields
        model_name: Target model for LLM requests
        prompt: Request prompt text (for LLM)
        max_tokens: Maximum tokens to generate (for LLM)
        temperature: Sampling temperature (for LLM)
        top_p: Top-p sampling parameter (for LLM)
        stream: Whether to stream response (for LLM)

        # Embedding-specific fields
        embedding_model: Model name for embedding requests
        texts: List of texts to embed (for embedding)
        batch_size: Batch size for embedding request

        metadata: Additional metadata
    """

    request_id: str
    request_type: RequestType
    priority: str
    slo_deadline_ms: int
    scheduled_arrival_time: float

    # LLM-specific fields
    model_name: str = ""
    prompt: str = ""
    max_tokens: int = 100
    temperature: float = 0.7
    top_p: float = 0.95
    stream: bool = True

    # Embedding-specific fields
    embedding_model: str = ""
    texts: list[str] = field(default_factory=list)
    batch_size: int = 1

    # Metadata
    metadata: dict = field(default_factory=dict)

    @property
    def is_llm_request(self) -> bool:
        """Check if this is an LLM request."""
        return self.request_type in (RequestType.LLM_CHAT, RequestType.LLM_GENERATE)

    @property
    def is_embedding_request(self) -> bool:
        """Check if this is an embedding request."""
        return self.request_type == RequestType.EMBEDDING

    def to_dict(self) -> dict[str, Any]:
        """Convert request to dictionary format."""
        base = {
            "request_id": self.request_id,
            "request_type": self.request_type.value,
            "priority": self.priority,
            "slo_deadline_ms": self.slo_deadline_ms,
            "scheduled_arrival_time": self.scheduled_arrival_time,
            "metadata": self.metadata,
        }

        if self.is_llm_request:
            base.update(
                {
                    "model_name": self.model_name,
                    "prompt": self.prompt,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "stream": self.stream,
                }
            )
        elif self.is_embedding_request:
            base.update(
                {
                    "embedding_model": self.embedding_model,
                    "texts": self.texts,
                    "batch_size": self.batch_size,
                }
            )

        return base

    def to_api_payload(self) -> dict[str, Any]:
        """Convert request to API payload format.

        Returns:
            Dictionary suitable for sending to Control Plane API
        """
        if self.is_llm_request:
            # OpenAI-compatible chat completion format
            return {
                "model": self.model_name,
                "messages": [{"role": "user", "content": self.prompt}],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "stream": self.stream,
            }
        else:
            # OpenAI-compatible embedding format
            return {
                "model": self.embedding_model,
                "input": self.texts if len(self.texts) > 1 else self.texts[0],
            }


# Template prompts for synthetic LLM workload generation
SYNTHETIC_LLM_PROMPTS = [
    "Explain the concept of {topic} in simple terms.",
    "Write a short summary about {topic}.",
    "What are the key points to understand about {topic}?",
    "Describe the main features of {topic}.",
    "How does {topic} work in practice?",
    "Compare and contrast {topic} with related concepts.",
    "What are the benefits and drawbacks of {topic}?",
    "Provide an example that illustrates {topic}.",
]

LLM_TOPICS = [
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

# Template texts for synthetic embedding workload generation
SYNTHETIC_EMBEDDING_TEXTS = [
    "The quick brown fox jumps over the lazy dog.",
    "Machine learning is transforming how we process data.",
    "Cloud computing provides scalable infrastructure on demand.",
    "Distributed systems enable high availability and fault tolerance.",
    "Natural language processing helps computers understand human language.",
    "Deep learning models can recognize patterns in complex data.",
    "Microservices architecture improves system modularity and scalability.",
    "Data pipelines automate the flow of information through systems.",
    "Real-time analytics provide immediate insights from streaming data.",
    "Graph databases excel at representing connected information.",
    "Vector databases enable efficient similarity search operations.",
    "Transformer models have revolutionized natural language understanding.",
    "Embedding vectors capture semantic meaning in numerical form.",
    "Retrieval augmented generation combines search with language models.",
    "Semantic search finds results based on meaning rather than keywords.",
]


class HybridWorkloadGenerator:
    """Generates hybrid benchmark workloads with mixed LLM and Embedding requests.

    This class creates a sequence of mixed requests with:
    - Configurable LLM/Embedding ratio
    - Configurable arrival patterns (uniform, Poisson, burst)
    - Model distribution for LLM requests
    - Batch size distribution for embedding requests
    - Priority distribution according to configuration
    - Synthetic or dataset-based content
    """

    def __init__(self, config: HybridBenchmarkConfig, seed: int | None = None):
        """Initialize workload generator.

        Args:
            config: Hybrid benchmark configuration
            seed: Random seed for reproducibility
        """
        self.config = config
        self.seed = seed
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)

        # Load datasets if provided
        self._llm_prompts: list[str] = []
        self._embedding_texts: list[str] = []
        self._load_datasets()

    def _load_datasets(self) -> None:
        """Load prompts and texts from dataset files if provided."""
        if self.config.llm_dataset_path and self.config.llm_dataset_path.exists():
            self._llm_prompts = self._load_jsonl(self.config.llm_dataset_path, "prompt")

        if self.config.embedding_dataset_path and self.config.embedding_dataset_path.exists():
            self._embedding_texts = self._load_jsonl(self.config.embedding_dataset_path, "text")

    def _load_jsonl(self, path: Path, text_field: str) -> list[str]:
        """Load texts from a JSONL file.

        Args:
            path: Path to JSONL file
            text_field: Field name containing the text

        Returns:
            List of text strings
        """
        texts = []
        try:
            with open(path) as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        if text_field in data:
                            texts.append(data[text_field])
                        elif "content" in data:
                            texts.append(data["content"])
                        elif "input" in data:
                            texts.append(data["input"])
        except Exception:
            pass
        return texts

    def generate(self) -> list[HybridRequest]:
        """Generate a list of hybrid requests according to configuration.

        Returns:
            List of HybridRequest objects with scheduled arrival times
        """
        requests = []
        arrival_times = self._generate_arrival_times()

        for i, arrival_time in enumerate(arrival_times):
            request = self._generate_single_request(i, arrival_time)
            requests.append(request)

        return requests

    def generate_from_data(
        self,
        workload_config: dict[str, Any],
        llm_prompts: list[str] | None = None,
        embedding_texts: list[str] | None = None,
    ) -> list[HybridRequest]:
        """Generate requests from external data sources.

        Args:
            workload_config: Workload configuration dictionary
            llm_prompts: Optional list of LLM prompts
            embedding_texts: Optional list of embedding texts

        Returns:
            List of HybridRequest objects
        """
        # Temporarily override datasets
        if llm_prompts:
            self._llm_prompts = llm_prompts
        if embedding_texts:
            self._embedding_texts = embedding_texts

        # Override config with workload_config
        if "num_requests" in workload_config:
            self.config.num_requests = workload_config["num_requests"]
        if "request_rate" in workload_config:
            self.config.request_rate = workload_config["request_rate"]
        if "llm_ratio" in workload_config:
            self.config.llm_ratio = workload_config["llm_ratio"]
            self.config.embedding_ratio = 1.0 - workload_config["llm_ratio"]

        return self.generate()

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
            times = self._generate_burst_arrivals(n)

        else:
            # Default to uniform
            inter_arrival = 1.0 / self.config.request_rate
            times = [i * inter_arrival for i in range(n)]

        return times

    def _generate_burst_arrivals(self, n: int) -> list[float]:
        """Generate burst arrival pattern.

        Args:
            n: Number of requests

        Returns:
            List of arrival times
        """
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

        return times

    def _generate_single_request(self, index: int, arrival_time: float) -> HybridRequest:
        """Generate a single hybrid request.

        Args:
            index: Request index
            arrival_time: Scheduled arrival time

        Returns:
            HybridRequest object
        """
        # Determine request type based on ratio
        is_llm = self.rng.random() < self.config.llm_ratio

        # Determine priority
        priority = self._sample_priority()

        if is_llm:
            return self._generate_llm_request(index, arrival_time, priority)
        else:
            return self._generate_embedding_request(index, arrival_time, priority)

    def _generate_llm_request(
        self, index: int, arrival_time: float, priority: str
    ) -> HybridRequest:
        """Generate an LLM request.

        Args:
            index: Request index
            arrival_time: Scheduled arrival time
            priority: Request priority

        Returns:
            HybridRequest for LLM
        """
        # Select model based on distribution
        model_name = self._sample_from_distribution(self.config.llm_model_distribution)

        # Generate or select prompt
        if self._llm_prompts:
            prompt = self.rng.choice(self._llm_prompts)
        else:
            prompt = self._generate_synthetic_llm_prompt()

        # Determine max tokens
        max_tokens = self.rng.randint(
            self.config.output_len_range[0], self.config.output_len_range[1]
        )

        # Get SLO deadline
        slo_deadline_ms = self.config.hybrid_slo_config.get_deadline_for_request(
            priority, RequestType.LLM_CHAT
        )

        # Decide request type (chat vs generate)
        request_type = RequestType.LLM_CHAT if self.rng.random() < 0.8 else RequestType.LLM_GENERATE

        return HybridRequest(
            request_id=f"llm-{index}-{uuid.uuid4().hex[:8]}",
            request_type=request_type,
            priority=priority,
            slo_deadline_ms=slo_deadline_ms,
            scheduled_arrival_time=arrival_time,
            model_name=model_name,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=0.7,
            top_p=0.95,
            stream=self.config.enable_streaming,
            metadata={
                "index": index,
                "generated_at": "synthetic" if not self._llm_prompts else "dataset",
            },
        )

    def _generate_embedding_request(
        self, index: int, arrival_time: float, priority: str
    ) -> HybridRequest:
        """Generate an embedding request.

        Args:
            index: Request index
            arrival_time: Scheduled arrival time
            priority: Request priority

        Returns:
            HybridRequest for Embedding
        """
        # Select batch size
        batch_size = self.rng.choice(self.config.embedding_batch_sizes)

        # Generate or select texts
        texts = []
        for _ in range(batch_size):
            if self._embedding_texts:
                text = self.rng.choice(self._embedding_texts)
            else:
                text = self._generate_synthetic_embedding_text()
            texts.append(text)

        # Get SLO deadline
        slo_deadline_ms = self.config.hybrid_slo_config.get_deadline_for_request(
            priority, RequestType.EMBEDDING
        )

        return HybridRequest(
            request_id=f"emb-{index}-{uuid.uuid4().hex[:8]}",
            request_type=RequestType.EMBEDDING,
            priority=priority,
            slo_deadline_ms=slo_deadline_ms,
            scheduled_arrival_time=arrival_time,
            embedding_model=self.config.embedding_model,
            texts=texts,
            batch_size=batch_size,
            metadata={
                "index": index,
                "generated_at": "synthetic" if not self._embedding_texts else "dataset",
            },
        )

    def _generate_synthetic_llm_prompt(self) -> str:
        """Generate a synthetic LLM prompt.

        Returns:
            Generated prompt string
        """
        template = self.rng.choice(SYNTHETIC_LLM_PROMPTS)
        topic = self.rng.choice(LLM_TOPICS)
        prompt = template.format(topic=topic)

        # Optionally extend prompt to meet length requirements
        min_len = self.config.prompt_len_range[0]
        while len(prompt.split()) < min_len // 4:  # Rough estimate: 4 chars per token
            extra_topic = self.rng.choice(LLM_TOPICS)
            prompt += f" Also, consider how this relates to {extra_topic}."

        return prompt

    def _generate_synthetic_embedding_text(self) -> str:
        """Generate a synthetic embedding text.

        Returns:
            Generated text string
        """
        base_text = self.rng.choice(SYNTHETIC_EMBEDDING_TEXTS)

        # Extend or trim to meet length requirements
        min_len, max_len = self.config.embedding_text_len_range
        while len(base_text) < min_len:
            extra = self.rng.choice(SYNTHETIC_EMBEDDING_TEXTS)
            base_text += " " + extra

        if len(base_text) > max_len:
            base_text = base_text[:max_len]

        return base_text

    def _sample_priority(self) -> str:
        """Sample a priority level based on configuration.

        Returns:
            Priority level string
        """
        return self._sample_from_distribution(self.config.priority_distribution)

    def _sample_from_distribution(self, distribution: dict[str, float]) -> str:
        """Sample from a weighted distribution.

        Args:
            distribution: Dictionary mapping items to probabilities

        Returns:
            Sampled item
        """
        items = list(distribution.keys())
        weights = list(distribution.values())
        return self.rng.choices(items, weights=weights, k=1)[0]

    def get_workload_summary(self, requests: list[HybridRequest]) -> dict[str, Any]:
        """Get summary statistics for a generated workload.

        Args:
            requests: List of generated requests

        Returns:
            Summary statistics dictionary
        """
        llm_requests = [r for r in requests if r.is_llm_request]
        embedding_requests = [r for r in requests if r.is_embedding_request]

        return {
            "total_requests": len(requests),
            "llm_requests": len(llm_requests),
            "embedding_requests": len(embedding_requests),
            "actual_llm_ratio": len(llm_requests) / len(requests) if requests else 0,
            "actual_embedding_ratio": (len(embedding_requests) / len(requests) if requests else 0),
            "priority_distribution": {
                "HIGH": sum(1 for r in requests if r.priority == "HIGH"),
                "NORMAL": sum(1 for r in requests if r.priority == "NORMAL"),
                "LOW": sum(1 for r in requests if r.priority == "LOW"),
            },
            "llm_model_distribution": {
                model: sum(1 for r in llm_requests if r.model_name == model)
                for model in {r.model_name for r in llm_requests}
            },
            "embedding_batch_size_distribution": {
                bs: sum(1 for r in embedding_requests if r.batch_size == bs)
                for bs in {r.batch_size for r in embedding_requests}
            },
            "duration_seconds": max(r.scheduled_arrival_time for r in requests) if requests else 0,
        }


# Re-export
__all__ = [
    "HybridRequest",
    "HybridWorkloadGenerator",
    "RequestType",
]
