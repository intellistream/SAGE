# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Common types and data structures for Control Plane."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# =============================================================================
# Engine State and Registration Types
# =============================================================================


class EngineState(str, Enum):
    """Lifecycle states for registered engines in the Control Plane.

    State transitions:
        STARTING -> READY (after successful health check)
        READY -> DRAINING (when graceful shutdown requested)
        DRAINING -> STOPPED (after all requests complete)
        Any -> ERROR (on consecutive health check failures)
        ERROR -> STARTING (on restart attempt)

    Attributes:
        STARTING: Engine process is starting, not yet ready to accept requests.
        READY: Engine is healthy and accepting requests.
        DRAINING: Engine is stopping gracefully, not accepting new requests
            but finishing existing ones.
        STOPPED: Engine has been stopped (gracefully or after draining).
        ERROR: Engine is unhealthy (e.g., consecutive health check failures).
    """

    STARTING = "STARTING"
    READY = "READY"
    DRAINING = "DRAINING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


@dataclass
class EngineInfo:
    """Information about a registered engine in the Control Plane.

    This dataclass tracks the state and metadata of an engine that has
    registered with the Control Plane, including its health status,
    heartbeat information, and lifecycle state.

    Attributes:
        engine_id: Unique identifier for this engine.
        model_id: The model loaded on this engine.
        host: Hostname or IP address of the engine.
        port: Port number the engine is listening on.
        state: Current lifecycle state of the engine.
        engine_kind: Type of engine ('llm' or 'embedding').
        created_at: When the engine was registered.
        last_heartbeat: Timestamp of last successful heartbeat.
        consecutive_failures: Number of consecutive health check failures.
        active_requests: Number of requests currently being processed.
        metadata: Additional engine metadata (labels, GPU info, etc.).
    """

    engine_id: str
    model_id: str
    host: str
    port: int
    state: EngineState = EngineState.STARTING
    engine_kind: str = "llm"
    created_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime | None = None
    consecutive_failures: int = 0
    active_requests: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        """Check if the engine is in a healthy state."""
        return self.state == EngineState.READY

    @property
    def is_accepting_requests(self) -> bool:
        """Check if the engine can accept new requests."""
        return self.state == EngineState.READY

    @property
    def is_terminal(self) -> bool:
        """Check if the engine is in a terminal state (STOPPED or ERROR)."""
        return self.state in (EngineState.STOPPED, EngineState.ERROR)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "engine_id": self.engine_id,
            "model_id": self.model_id,
            "host": self.host,
            "port": self.port,
            "state": self.state.value,
            "engine_kind": self.engine_kind,
            "created_at": self.created_at.isoformat(),
            "last_heartbeat": (self.last_heartbeat.isoformat() if self.last_heartbeat else None),
            "consecutive_failures": self.consecutive_failures,
            "active_requests": self.active_requests,
            "metadata": self.metadata,
        }


class RequestType(Enum):
    """Request type for hybrid scheduling.

    This enum categorizes inference requests to enable appropriate
    routing to compatible execution instances.

    Attributes:
        LLM_CHAT: Chat/conversation request with message history.
            Typically uses /v1/chat/completions endpoint.
        LLM_GENERATE: Text generation/completion request.
            Typically uses /v1/completions endpoint.
        EMBEDDING: Text embedding/vectorization request.
            Typically uses /v1/embeddings endpoint.
    """

    LLM_CHAT = "llm_chat"
    LLM_GENERATE = "llm_generate"
    EMBEDDING = "embedding"


class RequestPriority(Enum):
    """Request priority levels."""

    CRITICAL = 0  # Highest priority
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4  # Lowest priority


class RequestStatus(Enum):
    """Request lifecycle status."""

    PENDING = "pending"
    QUEUED = "queued"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ParallelismType(Enum):
    """Types of parallelism strategies."""

    TENSOR_PARALLEL = "tp"
    PIPELINE_PARALLEL = "pp"
    DATA_PARALLEL = "dp"
    EXPERT_PARALLEL = "ep"
    HYBRID = "hybrid"


class ExecutionInstanceType(Enum):
    """Types/roles of execution instances for PD separation and hybrid scheduling.

    This enum categorizes execution instances based on their capabilities,
    enabling appropriate routing of different request types.

    Attributes:
        GENERAL: General-purpose instance capable of handling LLM requests.
            Supports chat and text generation but not optimized for either phase.
        PREFILLING: Specialized for the prefilling phase of LLM inference.
            Optimized for processing long input sequences efficiently.
        DECODING: Specialized for the decoding phase of LLM inference.
            Optimized for generating output tokens with low latency.
        HYBRID: Handles both prefilling and decoding phases of LLM.
            Balances between prefilling throughput and decoding latency.
        EMBEDDING: Pure embedding instance (e.g., TEI, dedicated embedding server).
            Only handles embedding/vectorization requests, cannot process LLM requests.
        LLM_EMBEDDING: Mixed instance capable of both LLM and embedding requests.
            Supports chat, generation, and embedding operations.
            Useful for maximizing GPU utilization with mixed workloads.
    """

    GENERAL = "general"  # General-purpose instance
    PREFILLING = "prefilling"  # Specialized for prefilling phase
    DECODING = "decoding"  # Specialized for decoding phase
    HYBRID = "hybrid"  # Handles both prefilling and decoding
    EMBEDDING = "embedding"  # Pure embedding instance (e.g., TEI)
    LLM_EMBEDDING = "llm_embedding"  # Mixed instance for both LLM and embedding


@dataclass
class RequestMetadata:
    """Metadata for an inference request.

    This dataclass stores all metadata associated with an inference request,
    including request identification, parameters, timing information,
    resource preferences, and cost/billing information.

    The class supports both LLM requests (chat/generate) and Embedding requests
    through the request_type field and embedding-specific fields.

    Attributes:
        request_id: Unique identifier for this request.
        prompt: Prompt text for LLM inference (None for embedding requests).
        user_id: Optional user identifier for tracking/billing.
        priority: Request priority level for scheduling.
        slo_deadline_ms: SLO deadline in milliseconds.
        max_tokens: Maximum tokens to generate (LLM only).
        temperature: Sampling temperature (LLM only).
        top_p: Top-p sampling parameter (LLM only).
        model_name: Model name/identifier.

        request_type: Type of request (LLM_CHAT, LLM_GENERATE, or EMBEDDING).
            Defaults to LLM_CHAT for backward compatibility.
        embedding_texts: List of texts to embed (Embedding requests only).
        embedding_model: Model to use for embedding (overrides model_name if set).
        embedding_batch_size: Batch size for embedding requests.

        arrival_time: When the request arrived.
        queue_time: When the request was queued.
        schedule_time: When the request was scheduled.
        start_time: When execution started.
        end_time: When execution completed.

        preferred_instance_id: Preferred execution instance.
        parallelism_hint: Hint for parallelism strategy.

        cost_budget: Maximum cost budget.
        billing_tier: Billing tier identifier.

        tokens_generated: Number of tokens generated so far.
        last_token_time: Timestamp of last token generation.
        tbt_slo_ms: Time Between Tokens SLO in milliseconds.
        prefill_completed: Whether prefill phase is complete.
        can_be_preempted: Whether request can be preempted.

        tags: Additional metadata tags.
    """

    request_id: str
    prompt: str | None = None  # Prompt text for inference
    user_id: str | None = None
    priority: RequestPriority = RequestPriority.NORMAL
    slo_deadline_ms: float | None = None  # SLO deadline in milliseconds
    max_tokens: int | None = None
    temperature: float = 1.0
    top_p: float = 1.0
    model_name: str | None = None

    # ============ Request Type for Hybrid Scheduling ============
    # Type of request: LLM_CHAT, LLM_GENERATE, or EMBEDDING
    # Defaults to LLM_CHAT for backward compatibility with existing code
    request_type: RequestType = RequestType.LLM_CHAT

    # ============ Embedding-specific Fields ============
    # List of texts to embed (for EMBEDDING requests)
    embedding_texts: list[str] | None = None
    # Embedding model name (overrides model_name for embedding if set)
    embedding_model: str | None = None
    # Batch size for embedding requests (affects throughput vs latency tradeoff)
    embedding_batch_size: int = 32

    # Timing information
    arrival_time: datetime = field(default_factory=datetime.now)
    queue_time: datetime | None = None
    schedule_time: datetime | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None

    # Resource preferences
    preferred_instance_id: str | None = None
    parallelism_hint: ParallelismType | None = None

    # Cost and billing
    cost_budget: float | None = None
    billing_tier: str = "standard"

    # Token-level tracking for Aegaeon
    tokens_generated: int = 0  # Number of tokens already generated
    last_token_time: datetime | None = None  # Timestamp of last token generation
    tbt_slo_ms: float | None = None  # Time Between Tokens SLO in milliseconds
    prefill_completed: bool = False  # Whether prefill phase is complete
    can_be_preempted: bool = True  # Whether request can be preempted

    # Additional metadata
    tags: dict[str, Any] = field(default_factory=dict)

    @property
    def latency_ms(self) -> float | None:
        """Calculate end-to-end latency in milliseconds."""
        if self.end_time and self.arrival_time:
            return (self.end_time - self.arrival_time).total_seconds() * 1000
        return None

    @property
    def queue_wait_ms(self) -> float | None:
        """Calculate queue waiting time in milliseconds."""
        if self.schedule_time and self.queue_time:
            return (self.schedule_time - self.queue_time).total_seconds() * 1000
        return None

    @property
    def is_embedding_request(self) -> bool:
        """Check if this is an embedding request.

        Returns:
            True if request_type is EMBEDDING, False otherwise.
        """
        return self.request_type == RequestType.EMBEDDING

    @property
    def is_llm_request(self) -> bool:
        """Check if this is an LLM request (chat or generate).

        Returns:
            True if request_type is LLM_CHAT or LLM_GENERATE, False otherwise.
        """
        return self.request_type in (RequestType.LLM_CHAT, RequestType.LLM_GENERATE)

    @property
    def effective_model_name(self) -> str | None:
        """Get the effective model name for this request.

        For embedding requests, returns embedding_model if set, otherwise model_name.
        For LLM requests, returns model_name.

        Returns:
            The model name to use for this request.
        """
        if self.is_embedding_request and self.embedding_model:
            return self.embedding_model
        return self.model_name


@dataclass
class PrefillingConfig:
    """Configuration for prefilling-specialized instances."""

    # Optimization target
    target_batch_size: int = 64
    target_throughput_tokens_per_sec: float = 1000.0

    # Parallelism settings
    tensor_parallel_size: int = 4
    pipeline_parallel_size: int = 1

    # Performance tuning
    enable_kv_cache: bool = True
    enable_chunked_prefill: bool = True
    max_chunk_size_tokens: int = 4096

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DecodingConfig:
    """Configuration for decoding-specialized instances."""

    # Optimization target
    target_latency_ms: float = 50.0
    target_tokens_per_sec_per_gpu: float = 100.0

    # Parallelism settings (typically minimal)
    tensor_parallel_size: int = 1
    pipeline_parallel_size: int = 1

    # Performance tuning
    enable_prefix_caching: bool = True
    max_parallel_requests: int = 200
    kv_cache_memory_fraction: float = 0.85

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionInstance:
    """Represents a vLLM execution instance.

    This dataclass stores all information about an execution instance,
    including its identification, configuration, resource usage, health status,
    performance metrics, and topology information.

    The class supports both LLM-only and mixed LLM/Embedding instances through
    the instance_type field and embedding-specific fields.

    Attributes:
        instance_id: Unique identifier for this instance.
        host: Hostname or IP address of the instance.
        port: Port number for the instance API.
        model_name: Primary model loaded on this instance.

        tensor_parallel_size: Number of GPUs used for tensor parallelism.
        pipeline_parallel_size: Number of pipeline stages.
        data_parallel_size: Number of data parallel replicas.

        instance_type: Type/role of this instance (GENERAL, EMBEDDING, etc.).
        prefilling_config: Configuration for prefilling-specialized instances.
        decoding_config: Configuration for decoding-specialized instances.

        gpu_count: Number of GPUs allocated to this instance.
        gpu_memory_gb: Total GPU memory in gigabytes.
        gpu_utilization: Current GPU utilization (0.0 to 1.0).

        is_available: Whether the instance is available for new requests.
        is_healthy: Whether the instance is healthy.
        current_load: Current load level (0.0 to 1.0).

        avg_latency_ms: Average request latency in milliseconds.
        throughput_tokens_per_sec: Throughput in tokens per second.

        active_requests: Total number of active requests.
        max_concurrent_requests: Maximum concurrent requests allowed.

        prefilling_active_requests: Active prefilling requests (PD separation).
        decoding_active_requests: Active decoding requests (PD separation).

        supported_request_types: List of request types this instance can handle.
            Defaults based on instance_type if not explicitly set.
        embedding_model_loaded: Name of the embedding model loaded (if any).
            None if no embedding model is loaded.
        embedding_max_batch_size: Maximum batch size for embedding requests.
            Affects throughput vs latency tradeoff.
        embedding_active_requests: Current number of active embedding requests.

        machine_id: Physical machine identifier for topology-aware scheduling.
        rack_id: Rack identifier for multi-rack deployments.
        gpu_bus_id: PCIe bus ID of the GPU.
        gpu_device_id: CUDA device ID.
        nvlink_peers: Instance IDs connected via NVLINK.
        numa_node: NUMA node number.
        network_bandwidth_gbps: Network bandwidth in Gbps.
        network_latency_ms: Network latency to Control Plane.
        shared_memory_pool: Whether sharing system memory pool.
        shared_storage_path: Shared storage path.

        metadata: Additional metadata tags.
    """

    instance_id: str
    host: str
    port: int
    model_name: str

    # Parallelism configuration
    tensor_parallel_size: int = 1
    pipeline_parallel_size: int = 1
    data_parallel_size: int = 1

    # PD Separation: Instance type and specialized configs
    instance_type: ExecutionInstanceType = ExecutionInstanceType.GENERAL
    prefilling_config: PrefillingConfig | None = None
    decoding_config: DecodingConfig | None = None

    # Resource information
    gpu_count: int = 1
    gpu_memory_gb: float = 0.0
    gpu_utilization: float = 0.0

    # Status
    is_available: bool = True
    is_healthy: bool = True
    current_load: float = 0.0  # 0.0 to 1.0

    # Performance metrics
    avg_latency_ms: float = 0.0
    throughput_tokens_per_sec: float = 0.0

    # Active requests
    active_requests: int = 0
    max_concurrent_requests: int = 100

    # PD Separation: Request type tracking
    prefilling_active_requests: int = 0
    decoding_active_requests: int = 0

    # ============ Embedding Support for Hybrid Scheduling ============
    # List of request types this instance can handle.
    # If None, defaults are computed based on instance_type.
    supported_request_types: list[RequestType] | None = None

    # Name of the embedding model loaded on this instance.
    # None if no embedding model is loaded or instance doesn't support embedding.
    embedding_model_loaded: str | None = None

    # Maximum batch size for embedding requests.
    # Larger batches improve throughput but increase latency.
    embedding_max_batch_size: int = 32

    # Current number of active embedding requests being processed.
    embedding_active_requests: int = 0

    # ============ Topology Information (for scheduling optimization) ============
    machine_id: str | None = None  # Physical machine identifier (hostname/UUID)
    rack_id: str | None = None  # Rack identifier (for multi-rack deployments)

    # GPU hardware topology
    gpu_bus_id: str | None = None  # PCIe bus ID (e.g., "0000:01:00.0")
    gpu_device_id: int | None = None  # CUDA device ID (0, 1, 2, ...)
    nvlink_peers: list[str] = field(default_factory=list)  # Instance IDs connected via NVLINK
    numa_node: int | None = None  # NUMA node number

    # Network topology
    network_bandwidth_gbps: float = 10.0  # Network bandwidth in Gbps
    network_latency_ms: float = 0.1  # Network latency to Control Plane

    # Shared resources (for single-machine optimization)
    shared_memory_pool: bool = False  # Whether sharing system memory pool
    shared_storage_path: str | None = None  # Shared storage path (NVMe/SSD)

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def available_capacity(self) -> float:
        """Calculate available capacity (0.0 to 1.0)."""
        return max(0.0, 1.0 - self.current_load)

    @property
    def can_accept_request(self) -> bool:
        """Check if instance can accept new requests."""
        return (
            self.is_available
            and self.is_healthy
            and self.active_requests < self.max_concurrent_requests
            and self.current_load < 0.95
        )

    def can_accept_prefilling_request(self) -> bool:
        """Check if instance can accept prefilling requests."""
        if self.instance_type == ExecutionInstanceType.DECODING:
            return False
        return self.can_accept_request

    def can_accept_decoding_request(self) -> bool:
        """Check if instance can accept decoding requests."""
        if self.instance_type == ExecutionInstanceType.PREFILLING:
            return False
        return self.can_accept_request

    def get_effective_supported_request_types(self) -> list[RequestType]:
        """Get the effective list of supported request types.

        If supported_request_types is explicitly set, returns that list.
        Otherwise, computes default supported types based on instance_type.

        Default mappings:
        - EMBEDDING: [EMBEDDING]
        - LLM_EMBEDDING: [LLM_CHAT, LLM_GENERATE, EMBEDDING]
        - GENERAL/PREFILLING/DECODING/HYBRID: [LLM_CHAT, LLM_GENERATE]

        Returns:
            List of RequestType values this instance can handle.
        """
        if self.supported_request_types is not None:
            return self.supported_request_types

        # Compute defaults based on instance_type
        if self.instance_type == ExecutionInstanceType.EMBEDDING:
            return [RequestType.EMBEDDING]
        elif self.instance_type == ExecutionInstanceType.LLM_EMBEDDING:
            return [RequestType.LLM_CHAT, RequestType.LLM_GENERATE, RequestType.EMBEDDING]
        else:
            # GENERAL, PREFILLING, DECODING, HYBRID - all handle LLM requests
            return [RequestType.LLM_CHAT, RequestType.LLM_GENERATE]

    def can_handle_request_type(self, request_type: RequestType) -> bool:
        """Check if this instance can handle a specific request type.

        Determines whether the instance is capable of processing requests
        of the given type, based on its configuration and instance_type.

        Args:
            request_type: The type of request to check.

        Returns:
            True if the instance can handle the request type, False otherwise.

        Examples:
            >>> instance = ExecutionInstance(
            ...     instance_id="llm-1",
            ...     host="localhost",
            ...     port=8000,
            ...     model_name="Qwen/Qwen2.5-7B-Instruct",
            ...     instance_type=ExecutionInstanceType.GENERAL,
            ... )
            >>> instance.can_handle_request_type(RequestType.LLM_CHAT)
            True
            >>> instance.can_handle_request_type(RequestType.EMBEDDING)
            False

            >>> embed_instance = ExecutionInstance(
            ...     instance_id="embed-1",
            ...     host="localhost",
            ...     port=8090,
            ...     model_name="BAAI/bge-m3",
            ...     instance_type=ExecutionInstanceType.EMBEDDING,
            ... )
            >>> embed_instance.can_handle_request_type(RequestType.EMBEDDING)
            True
            >>> embed_instance.can_handle_request_type(RequestType.LLM_CHAT)
            False
        """
        return request_type in self.get_effective_supported_request_types()

    def can_accept_embedding_request(self) -> bool:
        """Check if instance can accept new embedding requests.

        This method checks both capability (can the instance handle embedding?)
        and availability (is there capacity for new requests?).

        The check considers:
        1. Whether the instance supports EMBEDDING request type
        2. General availability (is_available, is_healthy)
        3. Current load and active request counts
        4. Embedding-specific batch constraints

        Returns:
            True if the instance can accept a new embedding request,
            False otherwise.

        Examples:
            >>> instance = ExecutionInstance(
            ...     instance_id="embed-1",
            ...     host="localhost",
            ...     port=8090,
            ...     model_name="BAAI/bge-m3",
            ...     instance_type=ExecutionInstanceType.EMBEDDING,
            ...     embedding_max_batch_size=32,
            ...     embedding_active_requests=10,
            ... )
            >>> instance.can_accept_embedding_request()
            True

            >>> instance.embedding_active_requests = 32
            >>> instance.can_accept_embedding_request()
            False
        """
        # Check if instance supports embedding
        if not self.can_handle_request_type(RequestType.EMBEDDING):
            return False

        # Check general availability
        if not self.is_available or not self.is_healthy:
            return False

        # Check load constraints
        if self.current_load >= 0.95:
            return False

        # Check embedding-specific batch constraint
        if self.embedding_active_requests >= self.embedding_max_batch_size:
            return False

        return True

    def can_accept_llm_request(self) -> bool:
        """Check if instance can accept new LLM requests (chat or generate).

        This method checks both capability (can the instance handle LLM?)
        and availability (is there capacity for new requests?).

        Returns:
            True if the instance can accept a new LLM request,
            False otherwise.
        """
        # Check if instance supports LLM (either chat or generate)
        supports_llm = self.can_handle_request_type(
            RequestType.LLM_CHAT
        ) or self.can_handle_request_type(RequestType.LLM_GENERATE)
        if not supports_llm:
            return False

        # Use existing general availability check
        return self.can_accept_request

    def get_affinity_score(self, other: "ExecutionInstance") -> float:
        """
        Calculate affinity score with another instance (0.0-1.0).

        Higher score means better affinity (lower communication cost).

        Scoring:
        - 1.0: Same machine with NVLINK connection
        - 0.5: Same machine without NVLINK
        - 0.1: Same rack, different machine
        - 0.01: Different rack

        Args:
            other: Another execution instance

        Returns:
            Affinity score between 0.0 and 1.0
        """
        if self.machine_id and self.machine_id == other.machine_id:
            # Same machine
            if other.instance_id in self.nvlink_peers:
                return 1.0  # NVLINK connected
            return 0.5  # Same machine but no NVLINK
        elif self.rack_id and self.rack_id == other.rack_id:
            return 0.1  # Same rack
        else:
            return 0.01  # Different rack or no topology info

    def is_local_to(self, other: "ExecutionInstance") -> bool:
        """Check if this instance is on the same physical machine as another."""
        return self.machine_id is not None and self.machine_id == other.machine_id


@dataclass
class SchedulingDecision:
    """Decision made by the scheduler."""

    request_id: str
    target_instance_id: str
    parallelism_strategy: ParallelismType
    estimated_latency_ms: float
    estimated_cost: float

    # Configuration for execution
    tensor_parallel_size: int = 1
    pipeline_parallel_size: int = 1

    # Scheduling metadata
    decision_time: datetime = field(default_factory=datetime.now)
    reason: str = ""
    confidence: float = 1.0  # 0.0 to 1.0

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring."""

    timestamp: datetime = field(default_factory=datetime.now)

    # Request metrics
    total_requests: int = 0
    completed_requests: int = 0
    failed_requests: int = 0
    active_requests: int = 0
    queued_requests: int = 0

    # Latency metrics
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0

    # Throughput metrics
    tokens_per_second: float = 0.0
    requests_per_second: float = 0.0

    # Resource metrics
    avg_gpu_utilization: float = 0.0
    total_gpu_memory_gb: float = 0.0
    used_gpu_memory_gb: float = 0.0

    # Cost metrics
    total_cost: float = 0.0
    cost_per_token: float = 0.0

    # SLO metrics
    slo_violations: int = 0
    slo_compliance_rate: float = 1.0

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SchedulingMetrics:
    """Scheduling policy performance metrics."""

    timestamp: datetime = field(default_factory=datetime.now)
    policy_name: str = ""

    # Scheduling decision quality
    scheduling_latency_us: float = 0.0  # Scheduling decision latency (microseconds)
    scheduling_throughput: float = 0.0  # Scheduling throughput (decisions/sec)

    # Prediction accuracy
    latency_prediction_error_avg: float = 0.0  # Average prediction error (ms)
    latency_prediction_error_p95: float = 0.0  # P95 prediction error
    prediction_accuracy_rate: float = 1.0  # Accuracy rate (error < 10%)

    # Load balancing quality
    load_balance_variance: float = 0.0  # Variance of instance loads
    load_balance_coefficient: float = 1.0  # Load balance coefficient (1.0 = perfect)

    # SLO compliance by priority
    slo_compliance_by_priority: dict[str, float] = field(default_factory=dict)
    # Example: {"CRITICAL": 0.99, "HIGH": 0.95, "NORMAL": 0.90}

    # Queue dynamics
    queue_wait_time_p50: float = 0.0
    queue_wait_time_p95: float = 0.0
    queue_wait_time_p99: float = 0.0
    queue_length_avg: float = 0.0
    queue_length_max: int = 0

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class InstanceMetrics:
    """Detailed metrics for a single execution instance."""

    instance_id: str
    timestamp: datetime = field(default_factory=datetime.now)

    # Request processing
    total_requests_processed: int = 0
    active_requests: int = 0
    failed_requests: int = 0

    # Performance
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    throughput_tokens_per_sec: float = 0.0

    # Resource usage
    gpu_utilization: float = 0.0
    gpu_memory_used_gb: float = 0.0
    gpu_memory_total_gb: float = 0.0
    current_load: float = 0.0

    # Health status
    is_healthy: bool = True
    last_health_check: datetime | None = None
    consecutive_failures: int = 0

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PDSeparationConfig:
    """Configuration for Prefilling/Decoding separation."""

    # Enable/disable PD separation
    enabled: bool = True

    # Dynamic scaling configuration
    enable_dynamic_scaling: bool = True
    prefilling_min_instances: int = 1
    prefilling_max_instances: int = 5
    decoding_min_instances: int = 2
    decoding_max_instances: int = 8

    # Routing decision thresholds
    routing_policy: str = "adaptive"  # adaptive | threshold | ml
    prefilling_threshold_input_tokens: int = 800
    prefilling_threshold_ratio: float = 4.0  # input_tokens / output_tokens

    # KV-Cache management
    kv_cache_storage: str = "gpu"  # gpu | cpu | shared
    kv_cache_eviction_policy: str = "lru"  # lru | lfu | fifo
    kv_cache_memory_fraction: float = 0.85

    # Inter-cluster communication
    enable_kv_cache_transfer: bool = True
    kv_cache_transfer_buffer_mb: int = 2048
    max_transfer_latency_ms: float = 100.0

    # Monitoring and metrics
    collect_pd_metrics: bool = True
    pd_metrics_interval_sec: int = 10
    enable_pd_tracing: bool = False

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PDMetrics:
    """Metrics specific to PD separation."""

    timestamp: datetime = field(default_factory=datetime.now)

    # Prefilling metrics
    prefilling_throughput_tokens_per_sec: float = 0.0
    prefilling_latency_avg_ms: float = 0.0
    prefilling_latency_p99_ms: float = 0.0
    prefilling_gpu_util: float = 0.0
    prefilling_active_requests: int = 0

    # Decoding metrics
    decoding_latency_avg_ms: float = 0.0
    decoding_latency_p99_ms: float = 0.0
    decoding_gpu_util: float = 0.0
    decoding_active_requests: int = 0

    # Inter-cluster metrics
    kv_cache_hit_rate: float = 0.0  # Cache hit rate 0.0-1.0
    inter_cluster_transfer_latency_avg_ms: float = 0.0
    kv_cache_evictions_per_sec: float = 0.0

    # Cost metrics
    prefilling_cost_per_token: float = 0.0
    decoding_cost_per_token: float = 0.0
    total_cost_optimization_percent: float = 0.0  # vs mixed baseline

    # Routing statistics
    requests_routed_to_prefilling: int = 0
    requests_routed_to_decoding: int = 0
    requests_routed_to_hybrid: int = 0
    avg_routing_decision_time_us: float = 0.0

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScalingDecision:
    """Scaling decision for autoscaler."""

    num_prefill_instances: int
    num_decode_instances: int
    predicted_load: dict[str, float]
    decision_time: datetime = field(default_factory=datetime.now)
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
