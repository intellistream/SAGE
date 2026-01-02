# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Control Plane for sageLLM - Intelligent request routing and scheduling layer.

The Control Plane sits between users and vLLM execution instances, providing:
- Intelligent request routing and load balancing
- Advanced scheduling policies (priority, SLO-aware, cost-optimized)
- Dynamic parallelism strategy selection and optimization
- Multi-instance management and coordination
- Performance monitoring and adaptive optimization
- SLA-based autoscaling for Prefill/Decode instances
- GPU resource management and allocation
- Engine lifecycle management (spawn, stop, health check)
"""

# Import autoscaling components
from .autoscaler import Autoscaler, AutoscalerConfig

# Import engine lifecycle management
from .engine_lifecycle import (
    EngineLifecycleManager,
    EngineProcessInfo,
    EngineRuntime,
    EngineStatus,
)

# Import types
from .executors import ExecutionCoordinatorBase

# Import GPU resource management
from .gpu_manager import GPUResourceManager, GPUStatus
from .load_predictor import (
    ConstantPredictor,
    ExponentialSmoothingPredictor,
    LoadPredictor,
    MovingAveragePredictor,
)

# Import manager
from .manager import ControlPlaneManager
from .metrics_collector import MetricsCollector, SystemMetrics

# Import parallelism strategies
from .parallelism import (
    DataParallelStrategy,
    ExpertParallelStrategy,
    HybridParallelStrategy,
    ParallelismConfig,
    ParallelismOptimizer,
    ParallelismStrategy,
    PipelineParallelStrategy,
    TensorParallelStrategy,
)

# Import PD separation routing
from .pd_routing import PDRoutingStrategy
from .performance_interpolator import DecodeInterpolator, PrefillInterpolator

# Import request classifier for hybrid scheduling
from .request_classifier import (
    RequestClassifier,
    ValidationErrorCode,
    ValidationResult,
    create_classifier,
)

# Import router and coordinator
from .router import LoadBalancer, RequestRouter

# Import scheduling strategies
from .strategies import (
    AdaptivePolicy,
    CostOptimizedPolicy,
    FIFOPolicy,
    PriorityPolicy,
    SchedulingPolicy,
    SLOAwarePolicy,
)

# Import topology detection
from .topology import TopologyDetector
from .types import (
    DecodingConfig,
    EngineInfo,
    EngineState,
    ExecutionInstance,
    ExecutionInstanceType,
    InstanceMetrics,
    ParallelismType,
    PDMetrics,
    PDSeparationConfig,
    PerformanceMetrics,
    PrefillingConfig,
    RequestMetadata,
    RequestPriority,
    RequestStatus,
    RequestType,
    ScalingDecision,
    SchedulingDecision,
    SchedulingMetrics,
)

__all__ = [
    # Types - Core
    "RequestPriority",
    "RequestStatus",
    "RequestType",
    "ParallelismType",
    "RequestMetadata",
    "ExecutionInstance",
    "SchedulingDecision",
    "PerformanceMetrics",
    "SchedulingMetrics",
    "InstanceMetrics",
    "ScalingDecision",
    # Types - Engine Registration
    "EngineState",
    "EngineInfo",
    # Types - PD Separation
    "ExecutionInstanceType",
    "PrefillingConfig",
    "DecodingConfig",
    "PDSeparationConfig",
    "PDMetrics",
    # Request Classifier (Hybrid Scheduling)
    "RequestClassifier",
    "ValidationErrorCode",
    "ValidationResult",
    "create_classifier",
    # Autoscaling
    "Autoscaler",
    "AutoscalerConfig",
    "LoadPredictor",
    "ConstantPredictor",
    "MovingAveragePredictor",
    "ExponentialSmoothingPredictor",
    "MetricsCollector",
    "SystemMetrics",
    "PrefillInterpolator",
    "DecodeInterpolator",
    # Policies
    "SchedulingPolicy",
    "FIFOPolicy",
    "PriorityPolicy",
    "SLOAwarePolicy",
    "CostOptimizedPolicy",
    "AdaptivePolicy",
    # Parallelism
    "ParallelismConfig",
    "ParallelismStrategy",
    "TensorParallelStrategy",
    "PipelineParallelStrategy",
    "DataParallelStrategy",
    "ExpertParallelStrategy",
    "HybridParallelStrategy",
    "ParallelismOptimizer",
    # Router and Executor
    "RequestRouter",
    "LoadBalancer",
    "ExecutionCoordinatorBase",
    # Topology
    "TopologyDetector",
    # Monitoring
    "MetricsCollector",
    # PD Routing
    "PDRoutingStrategy",
    # Manager
    "ControlPlaneManager",
    # GPU Resource Management
    "GPUResourceManager",
    "GPUStatus",
    # Engine Lifecycle Management
    "EngineLifecycleManager",
    "EngineProcessInfo",
    "EngineRuntime",
    "EngineStatus",
]
