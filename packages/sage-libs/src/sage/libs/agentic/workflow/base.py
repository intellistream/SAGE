"""
Base Classes for Workflow Optimization Framework

Layer: L3 (Core - Algorithm Library)

This module defines the core abstractions for representing agentic workflows
and optimization strategies.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class NodeType(Enum):
    """Types of nodes in a workflow graph."""

    AGENT = "agent"  # AI agent (LLM-based)
    TOOL = "tool"  # External tool/API
    OPERATOR = "operator"  # Data processing operator
    DECISION = "decision"  # Conditional branching
    AGGREGATE = "aggregate"  # Result aggregation


@dataclass
class WorkflowNode:
    """
    Represents a node in an agentic workflow.

    Attributes:
        id: Unique identifier for the node
        name: Human-readable name
        node_type: Type of the node
        operator: Optional SAGE operator instance
        config: Node configuration parameters
        metrics: Performance metrics (cost, latency, quality, etc.)
        metadata: Additional node metadata
    """

    id: str
    name: str
    node_type: NodeType
    operator: Any | None = None  # MapFunction type, but avoid import
    config: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate node initialization."""
        if not self.id:
            raise ValueError("Node ID cannot be empty")

        # Set default metrics if not provided
        if "cost" not in self.metrics:
            self.metrics["cost"] = 0.0
        if "latency" not in self.metrics:
            self.metrics["latency"] = 0.0
        if "quality" not in self.metrics:
            self.metrics["quality"] = 1.0

    @property
    def cost(self) -> float:
        """Get node cost."""
        return self.metrics.get("cost", 0.0)

    @property
    def latency(self) -> float:
        """Get node latency."""
        return self.metrics.get("latency", 0.0)

    @property
    def quality(self) -> float:
        """Get node quality score."""
        return self.metrics.get("quality", 1.0)


class WorkflowGraph:
    """
    Represents an agentic workflow as a directed acyclic graph (DAG).

    This is the primary data structure for workflow optimization research.
    Students can define workflows and apply different optimization strategies.

    Example:
        >>> workflow = WorkflowGraph()
        >>> workflow.add_node("agent1", NodeType.AGENT, metrics={"cost": 10})
        >>> workflow.add_node("agent2", NodeType.AGENT, metrics={"cost": 20})
        >>> workflow.add_edge("agent1", "agent2")
        >>> print(workflow.total_cost())
        30.0
    """

    def __init__(self, name: str = "workflow"):
        """
        Initialize a workflow graph.

        Args:
            name: Name of the workflow
        """
        self.name = name
        self.nodes: dict[str, WorkflowNode] = {}
        self.edges: dict[str, set[str]] = {}  # adjacency list
        self.metadata: dict[str, Any] = {}

    def add_node(
        self,
        node_id: str,
        node_type: NodeType,
        name: str | None = None,
        operator: Any | None = None,
        config: dict[str, Any] | None = None,
        metrics: dict[str, float] | None = None,
        **kwargs,
    ) -> WorkflowNode:
        """
        Add a node to the workflow.

        Args:
            node_id: Unique identifier
            node_type: Type of the node
            name: Human-readable name (defaults to node_id)
            operator: Optional SAGE operator
            config: Configuration parameters
            metrics: Performance metrics
            **kwargs: Additional metadata

        Returns:
            The created WorkflowNode

        Raises:
            ValueError: If node_id already exists
        """
        if node_id in self.nodes:
            raise ValueError(f"Node {node_id} already exists")

        node = WorkflowNode(
            id=node_id,
            name=name or node_id,
            node_type=node_type,
            operator=operator,
            config=config or {},
            metrics=metrics or {},
            metadata=kwargs,
        )

        self.nodes[node_id] = node
        self.edges[node_id] = set()
        return node

    def add_edge(self, from_node: str, to_node: str):
        """
        Add a directed edge between two nodes.

        Args:
            from_node: Source node ID
            to_node: Target node ID

        Raises:
            ValueError: If nodes don't exist or edge creates a cycle
        """
        if from_node not in self.nodes:
            raise ValueError(f"Node {from_node} does not exist")
        if to_node not in self.nodes:
            raise ValueError(f"Node {to_node} does not exist")

        # Check for cycles (simple DFS)
        if self._creates_cycle(from_node, to_node):
            raise ValueError(f"Adding edge {from_node}->{to_node} would create a cycle")

        self.edges[from_node].add(to_node)

    def _creates_cycle(self, from_node: str, to_node: str) -> bool:
        """Check if adding an edge would create a cycle."""
        visited = set()

        def dfs(node: str) -> bool:
            if node == from_node:
                return True
            if node in visited:
                return False
            visited.add(node)
            for neighbor in self.edges.get(node, []):
                if dfs(neighbor):
                    return True
            return False

        return dfs(to_node)

    def get_node(self, node_id: str) -> WorkflowNode:
        """Get a node by ID."""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} does not exist")
        return self.nodes[node_id]

    def get_predecessors(self, node_id: str) -> list[str]:
        """Get all nodes that have edges pointing to this node."""
        return [n for n, targets in self.edges.items() if node_id in targets]

    def get_successors(self, node_id: str) -> list[str]:
        """Get all nodes that this node points to."""
        return list(self.edges.get(node_id, []))

    def topological_sort(self) -> list[str]:
        """
        Return nodes in topological order.

        Returns:
            List of node IDs in execution order

        Raises:
            ValueError: If graph has cycles
        """
        in_degree = dict.fromkeys(self.nodes, 0)
        for node in self.nodes:
            for successor in self.edges[node]:
                in_degree[successor] += 1

        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for successor in self.edges[node]:
                in_degree[successor] -= 1
                if in_degree[successor] == 0:
                    queue.append(successor)

        if len(result) != len(self.nodes):
            raise ValueError("Graph contains cycles")

        return result

    def total_cost(self) -> float:
        """Calculate total workflow cost."""
        return sum(node.cost for node in self.nodes.values())

    def total_latency(self) -> float:
        """Calculate critical path latency (longest path)."""
        # Simple implementation: sum of all nodes (assumes sequential execution)
        # Students can implement more sophisticated critical path analysis
        return sum(node.latency for node in self.nodes.values())

    def average_quality(self) -> float:
        """Calculate average quality across all nodes."""
        if not self.nodes:
            return 0.0
        return sum(node.quality for node in self.nodes.values()) / len(self.nodes)

    def clone(self) -> "WorkflowGraph":
        """Create a deep copy of the workflow."""
        import copy

        return copy.deepcopy(self)

    def __repr__(self) -> str:
        return (
            f"WorkflowGraph(name={self.name}, "
            f"nodes={len(self.nodes)}, edges={sum(len(e) for e in self.edges.values())})"
        )


@dataclass
class OptimizationResult:
    """
    Result of workflow optimization.

    Attributes:
        original_workflow: The input workflow
        optimized_workflow: The optimized workflow
        metrics: Optimization metrics
        steps: List of optimization steps taken
        metadata: Additional result metadata
    """

    original_workflow: WorkflowGraph
    optimized_workflow: WorkflowGraph
    metrics: "OptimizationMetrics"
    steps: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationMetrics:
    """
    Metrics for evaluating optimization quality.

    Attributes:
        cost_reduction: Percentage reduction in cost
        latency_reduction: Percentage reduction in latency
        quality_change: Change in quality score
        execution_time: Optimization execution time (seconds)
        iterations: Number of optimization iterations
    """

    cost_reduction: float = 0.0  # Percentage (0-100)
    latency_reduction: float = 0.0  # Percentage (0-100)
    quality_change: float = 0.0  # Positive or negative
    execution_time: float = 0.0  # Seconds
    iterations: int = 0

    def __repr__(self) -> str:
        return (
            f"OptimizationMetrics("
            f"cost↓={self.cost_reduction:.1f}%, "
            f"latency↓={self.latency_reduction:.1f}%, "
            f"quality Δ={self.quality_change:+.2f})"
        )


class BaseOptimizer(ABC):
    """
    Abstract base class for workflow optimizers.

    Students should inherit from this class to implement their own
    optimization strategies. The framework handles evaluation and
    comparison of different approaches.

    Example:
        >>> class MyOptimizer(BaseOptimizer):
        ...     def optimize(self, workflow, constraints=None):
        ...         # Your optimization logic here
        ...         optimized = workflow.clone()
        ...         # ... modify optimized workflow ...
        ...         return OptimizationResult(
        ...             original_workflow=workflow,
        ...             optimized_workflow=optimized,
        ...             metrics=self.calculate_metrics(workflow, optimized)
        ...         )
    """

    def __init__(self, name: str = "BaseOptimizer"):
        """
        Initialize optimizer.

        Args:
            name: Name of the optimizer
        """
        self.name = name
        self.config: dict[str, Any] = {}

    @abstractmethod
    def optimize(
        self,
        workflow: WorkflowGraph,
        constraints: dict[str, Any] | None = None,
    ) -> OptimizationResult:
        """
        Optimize a workflow graph.

        Args:
            workflow: The workflow to optimize
            constraints: Optional constraints (max_cost, max_latency, min_quality, etc.)

        Returns:
            OptimizationResult containing the optimized workflow and metrics
        """
        pass

    def calculate_metrics(
        self,
        original: WorkflowGraph,
        optimized: WorkflowGraph,
        execution_time: float = 0.0,
        iterations: int = 0,
    ) -> OptimizationMetrics:
        """
        Calculate optimization metrics.

        Args:
            original: Original workflow
            optimized: Optimized workflow
            execution_time: Time taken to optimize
            iterations: Number of iterations

        Returns:
            OptimizationMetrics
        """
        orig_cost = original.total_cost()
        opt_cost = optimized.total_cost()
        cost_reduction = ((orig_cost - opt_cost) / orig_cost * 100) if orig_cost > 0 else 0.0

        orig_latency = original.total_latency()
        opt_latency = optimized.total_latency()
        latency_reduction = (
            ((orig_latency - opt_latency) / orig_latency * 100) if orig_latency > 0 else 0.0
        )

        quality_change = optimized.average_quality() - original.average_quality()

        return OptimizationMetrics(
            cost_reduction=cost_reduction,
            latency_reduction=latency_reduction,
            quality_change=quality_change,
            execution_time=execution_time,
            iterations=iterations,
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"
