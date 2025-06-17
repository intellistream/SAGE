import ray
import logging
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from sage.core.dag.dag import DAG
if TYPE_CHECKING:
    from ray.actor import ActorHandle  # 只在类型检查期间生效
else:
    ActorHandle = Any

class RayDAG:
    """
    Ray-specific DAG implementation using Ray actors for distributed execution.
    """
    
    def __init__(self, name: str, strategy: str = "streaming"):
        self.name = name
        self.strategy = strategy
        self.platform = "ray"
        
        # Ray actor storage
        self.ray_actors: Dict[str, ray.ActorHandle] = {}
        self.actor_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Connection mappings for proper channel routing
        self.connections: List[Tuple[str, int, str, int]] = []  # (upstream_node, out_channel, downstream_node, in_channel)
        
        # Execution state
        self._running = False
        self.logger = logging.getLogger(f"RayDAG.{self.name}")
        
        # Store actor dependencies for proper execution order
        self.actor_dependencies: Dict[str, List[str]] = {}  # node_name -> [upstream_node_names]
        self.spout_actors: List[str] = []
    
    def add_ray_actor(self, name: str, actor:Any, is_spout: bool = False, 
                     upstream_nodes: List[str] = None):
        """
        Add a Ray actor to the DAG.
        
        Args:
            name: Actor name/identifier
            actor: Ray actor handle
            is_spout: Whether this actor is a spout (source) node
            upstream_nodes: List of upstream node names this actor depends on
        """
        self.ray_actors[name] = actor
        self.actor_metadata[name] = {
            'is_spout': is_spout,
            'upstream_nodes': upstream_nodes or []
        }
        
        if is_spout:
            self.spout_actors.append(name)
        
        if upstream_nodes:
            self.actor_dependencies[name] = upstream_nodes
        
        self.logger.debug(f"Added Ray actor '{name}' to DAG (spout: {is_spout})")
    
    def connect_actors(self, upstream_name: str, upstream_output_channel: int,
                      downstream_name: str, downstream_input_channel: int):
        """
        Connect two Ray actors with proper channel mapping.
        
        Args:
            upstream_name: Name of upstream actor
            upstream_output_channel: Output channel of upstream actor
            downstream_name: Name of downstream actor  
            downstream_input_channel: Input channel of downstream actor
        """
        if upstream_name not in self.ray_actors or downstream_name not in self.ray_actors:
            raise ValueError(f"Actor not found: {upstream_name} or {downstream_name}")
        
        upstream_actor = self.ray_actors[upstream_name]
        downstream_actor = self.ray_actors[downstream_name]
        
        # Add downstream connection to upstream actor
        upstream_actor.add_downstream_connection.remote(
            upstream_output_channel, 
            downstream_actor, 
            downstream_input_channel
        )
        
        # Store connection for debugging and validation
        connection = (upstream_name, upstream_output_channel, downstream_name, downstream_input_channel)
        self.connections.append(connection)
        
        self.logger.debug(
            f"Connected actors: {upstream_name}[out:{upstream_output_channel}] -> "
            f"{downstream_name}[in:{downstream_input_channel}]"
        )
    
    def get_connections(self) -> List[Tuple[str, int, str, int]]:
        """Get all connections in the DAG."""
        return self.connections.copy()
    
    def validate_connections(self) -> bool:
        """Validate that all connections are properly configured."""
        for upstream_name, out_ch, downstream_name, in_ch in self.connections:
            if upstream_name not in self.ray_actors:
                self.logger.error(f"Upstream actor not found: {upstream_name}")
                return False
            if downstream_name not in self.ray_actors:
                self.logger.error(f"Downstream actor not found: {downstream_name}")
                return False
        
        return True
    
    def get_actor(self, name: str) -> Optional[ActorHandle]:
        """Get Ray actor by name."""
        return self.ray_actors.get(name)
    
    def get_all_actors(self) -> Dict[str, ActorHandle]:
        """Get all Ray actors in the DAG."""
        return self.ray_actors.copy()
    
    def get_spout_actors(self) -> List[ActorHandle]:
        """Get all spout actors."""
        return [self.ray_actors[name] for name in self.spout_actors]
    
    def get_actor_count(self) -> int:
        """Get total number of actors in the DAG."""
        return len(self.ray_actors)
    
    def is_valid(self) -> bool:
        """Check if the DAG is valid."""
        if not self.spout_actors:
            self.logger.error("DAG has no spout actors")
            return False
        
        if not self.validate_connections():
            return False
        
        # Check if all referenced actors exist
        for name, dependencies in self.actor_dependencies.items():
            for dep in dependencies:
                if dep not in self.ray_actors:
                    self.logger.error(f"Missing dependency: {dep} for actor {name}")
                    return False
        
        return True
    
    
    def __str__(self):
        """String representation of the DAG."""
        return (f"RayDAG(name={self.name}, actors={len(self.ray_actors)}, "
                f"connections={len(self.connections)}, spouts={len(self.spout_actors)})")