import ray
import time
import asyncio
import logging
from typing import List, Optional, Dict, Any
from sage.core.dag.ray_dag import RayDAG

class RayDAGExecutor:
    """
    Specialized executor for Ray DAG execution with distributed actors.
    """
    
    def __init__(self, monitoring_interval: float = 1.0):
        """
        Initialize Ray DAG executor.
        
        Args:
            monitoring_interval: Interval in seconds for monitoring actor status
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.monitoring_interval = monitoring_interval
        self._execution_stats = {}
        
    def execute(self, ray_dag: RayDAG, duration: Optional[int] = None, 
                wait_for_completion: bool = True) -> Dict[str, Any]:
        """
        Execute a Ray DAG.
        
        Args:
            ray_dag: The RayDAG to execute
            duration: Optional execution duration in seconds (for streaming)
            wait_for_completion: Whether to wait for completion (for one-shot)
            
        Returns:
            Execution statistics and results
        """
        if not isinstance(ray_dag, RayDAG):
            raise TypeError("Expected RayDAG instance")
        
        if not ray_dag.is_valid():
            raise ValueError("Invalid RayDAG: missing spouts or broken dependencies")
        
        self.logger.info(f"Starting Ray DAG execution: {ray_dag}")
        
        execution_result = {
            'dag_id': ray_dag.id,
            'strategy': ray_dag.strategy,
            'actor_count': ray_dag.get_actor_count(),
            'start_time': time.time(),
            'end_time': None,
            'success': False,
            'error': None
        }
        
        try:
            if ray_dag.strategy == "streaming":
                result = self._execute_streaming(ray_dag, duration)
            elif ray_dag.strategy == "oneshot":
                result = self._execute_oneshot(ray_dag, wait_for_completion)
            else:
                raise ValueError(f"Unsupported strategy: {ray_dag.strategy}")
            
            execution_result.update(result)
            execution_result['success'] = True
            
        except Exception as e:
            self.logger.error(f"Ray DAG execution failed: {e}", exc_info=True)
            execution_result['error'] = str(e)
            raise
        
        finally:
            execution_result['end_time'] = time.time()
            execution_result['duration'] = execution_result['end_time'] - execution_result['start_time']
            
            # Always attempt cleanup
            self._cleanup_dag(ray_dag)
        
        return execution_result
    
    def _execute_streaming(self, ray_dag: RayDAG, duration: Optional[int]) -> Dict[str, Any]:
        """Execute streaming DAG."""
        self.logger.info(f"Starting streaming execution for {duration or 'indefinite'} seconds")
        
        # Start spout actors
        spout_futures = self._start_spout_actors(ray_dag)
        
        if duration:
            # Run for specified duration with monitoring
            self._monitor_execution(ray_dag, duration)
            self._stop_all_actors(ray_dag)
        else:
            # Run indefinitely until external stop
            self.logger.info("Running indefinitely (call stop_execution to halt)")
        
        return {
            'mode': 'streaming',
            'spout_count': len(spout_futures),
            'requested_duration': duration
        }
    
    def _execute_oneshot(self, ray_dag: RayDAG, wait_for_completion: bool) -> Dict[str, Any]:
        """Execute one-shot DAG."""
        self.logger.info("Starting one-shot execution")
        
        # Start spout actors
        spout_futures = self._start_spout_actors(ray_dag)
        
        if wait_for_completion:
            # Wait for all spouts to complete
            self.logger.info("Waiting for spout actors to complete...")
            ray.get(spout_futures)
            self.logger.info("All spout actors completed")
        
        return {
            'mode': 'oneshot',
            'spout_count': len(spout_futures),
            'waited_for_completion': wait_for_completion
        }
    
    def _start_spout_actors(self, ray_dag: RayDAG) -> List[ray.ObjectRef]:
        """Start all spout actors and return their futures."""
        spout_actors = ray_dag.get_spout_actors()
        
        if not spout_actors:
            raise RuntimeError("No spout actors found in DAG")
        
        spout_futures = []
        for spout_actor in spout_actors:
            try:
                future = spout_actor.start_spout.remote()
                spout_futures.append(future)
                self.logger.debug(f"Started spout actor")
            except Exception as e:
                self.logger.error(f"Failed to start spout actor: {e}")
                raise
        
        self.logger.info(f"Started {len(spout_futures)} spout actors")
        return spout_futures
    
    def _monitor_execution(self, ray_dag: RayDAG, duration: int):
        """Monitor DAG execution for specified duration."""
        start_time = time.time()
        
        while time.time() - start_time < duration:
            # Check actor health
            self._check_actor_health(ray_dag)
            time.sleep(self.monitoring_interval)
        
        self.logger.info(f"Monitoring completed after {duration} seconds")
    
    def _check_actor_health(self, ray_dag: RayDAG):
        """Check health of all actors in the DAG."""
        dead_actors = []
        
        for name, actor in ray_dag.get_all_actors().items():
            try:
                # Non-blocking health check
                ready, not_ready = ray.wait([actor.is_running.remote()], timeout=0.1)
                if not ready:
                    continue  # Actor is busy, assume healthy
                
                is_running = ray.get(ready[0])
                if not is_running:
                    dead_actors.append(name)
                    
            except Exception as e:
                self.logger.warning(f"Health check failed for actor {name}: {e}")
                dead_actors.append(name)
        
        if dead_actors:
            self.logger.error(f"Dead actors detected: {dead_actors}")
            raise RuntimeError(f"Actors died during execution: {dead_actors}")
    
    def _stop_all_actors(self, ray_dag: RayDAG):
        """Stop all actors in the DAG."""
        self.logger.info("Stopping all actors...")
        
        stop_futures = []
        for name, actor in ray_dag.get_all_actors().items():
            try:
                future = actor.stop.remote()
                stop_futures.append(future)
            except Exception as e:
                self.logger.warning(f"Failed to stop actor {name}: {e}")
        
        # Wait for all actors to stop
        if stop_futures:
            try:
                ray.get(stop_futures, timeout=30)  # 30 second timeout
                self.logger.info("All actors stopped successfully")
            except Exception as e:
                self.logger.error(f"Some actors failed to stop gracefully: {e}")
    
    def _cleanup_dag(self, ray_dag: RayDAG):
        """Clean up all Ray actors in the DAG."""
        self.logger.info("Cleaning up Ray actors...")
        
        for name, actor in ray_dag.get_all_actors().items():
            try:
                ray.kill(actor)
                self.logger.debug(f"Killed actor: {name}")
            except Exception as e:
                self.logger.warning(f"Failed to kill actor {name}: {e}")
        
        self.logger.info("Actor cleanup completed")
    
    def stop_execution(self, ray_dag: RayDAG):
        """Manually stop DAG execution."""
        self.logger.info("Manual stop requested")
        self._stop_all_actors(ray_dag)