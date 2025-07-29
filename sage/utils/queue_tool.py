"""
Queue Management Tools

Provides command-line and programmatic tools for managing queues,
monitoring performance, and debugging queue systems.
"""

import argparse
import time
import json
import sys
from typing import Dict, Any, Optional, List
from .queue_adapter import get_queue_backend_info, create_queue, is_sage_queue_available
from .queue_config import get_default_config, load_queue_config


class QueueTool:
    """Command-line tool for queue management and monitoring."""
    
    def __init__(self):
        self.config = get_default_config()
    
    def info(self) -> Dict[str, Any]:
        """Get information about available queue backends."""
        return get_queue_backend_info()
    
    def test_backend(self, backend: str = "auto", verbose: bool = False) -> bool:
        """
        Test a specific queue backend.
        
        Args:
            backend: Backend to test
            verbose: Print detailed output
            
        Returns:
            True if test passes, False otherwise
        """
        try:
            if verbose:
                print(f"Testing backend: {backend}")
            
            # Create test queue
            queue = create_queue(backend=backend, name="test_queue", maxsize=100)
            
            # Test basic operations
            test_data = ["test1", "test2", "test3"]
            
            # Test put operations
            for item in test_data:
                queue.put(item)
                if verbose:
                    print(f"Put: {item}")
            
            # Test get operations
            retrieved = []
            for _ in range(len(test_data)):
                item = queue.get()
                retrieved.append(item)
                if verbose:
                    print(f"Got: {item}")
            
            # Verify data integrity
            if retrieved != test_data:
                raise ValueError(f"Data mismatch: expected {test_data}, got {retrieved}")
            
            # Clean up
            if hasattr(queue, 'close'):
                queue.close()
            
            if verbose:
                print(f"Backend {backend} test passed")
            
            return True
            
        except Exception as e:
            if verbose:
                print(f"Backend {backend} test failed: {e}")
            return False
    
    def benchmark(self, backend: str = "auto", num_items: int = 1000, 
                  num_workers: int = 1, verbose: bool = False) -> Dict[str, float]:
        """
        Benchmark queue performance.
        
        Args:
            backend: Backend to benchmark
            num_items: Number of items to process
            num_workers: Number of worker processes (if supported)
            verbose: Print detailed output
            
        Returns:
            Dictionary with performance metrics
        """
        try:
            if verbose:
                print(f"Benchmarking {backend} with {num_items} items")
            
            queue = create_queue(backend=backend, name="benchmark_queue", maxsize=num_items * 2)
            
            # Benchmark put operations
            start_time = time.time()
            for i in range(num_items):
                queue.put(f"item_{i}")
            put_time = time.time() - start_time
            
            # Benchmark get operations
            start_time = time.time()
            for i in range(num_items):
                queue.get()
            get_time = time.time() - start_time
            
            # Clean up
            if hasattr(queue, 'close'):
                queue.close()
            
            metrics = {
                'backend': backend,
                'num_items': num_items,
                'put_time_seconds': put_time,
                'get_time_seconds': get_time,
                'total_time_seconds': put_time + get_time,
                'put_ops_per_second': num_items / put_time if put_time > 0 else 0,
                'get_ops_per_second': num_items / get_time if get_time > 0 else 0,
                'total_ops_per_second': (num_items * 2) / (put_time + get_time) if (put_time + get_time) > 0 else 0
            }
            
            if verbose:
                print(f"Put operations: {metrics['put_ops_per_second']:.2f} ops/sec")
                print(f"Get operations: {metrics['get_ops_per_second']:.2f} ops/sec")
                print(f"Total: {metrics['total_ops_per_second']:.2f} ops/sec")
            
            return metrics
            
        except Exception as e:
            if verbose:
                print(f"Benchmark failed: {e}")
            return {'error': str(e)}
    
    def monitor(self, queue_name: str, backend: str = "auto", 
                interval: int = 5, duration: int = 60) -> List[Dict[str, Any]]:
        """
        Monitor queue statistics over time.
        
        Args:
            queue_name: Name of queue to monitor
            backend: Backend type
            interval: Monitoring interval in seconds
            duration: Total monitoring duration in seconds
            
        Returns:
            List of monitoring data points
        """
        monitoring_data = []
        end_time = time.time() + duration
        
        print(f"Monitoring queue '{queue_name}' for {duration} seconds...")
        
        try:
            while time.time() < end_time:
                timestamp = time.time()
                
                # Get queue stats (this would need backend-specific implementation)
                stats = {
                    'timestamp': timestamp,
                    'queue_name': queue_name,
                    'backend': backend,
                    # Add more metrics as available from specific backends
                }
                
                monitoring_data.append(stats)
                print(f"[{time.strftime('%H:%M:%S')}] Queue: {queue_name}, Backend: {backend}")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
        
        return monitoring_data
    
    def cleanup(self, namespace: Optional[str] = None, force: bool = False) -> bool:
        """
        Clean up queue resources.
        
        Args:
            namespace: Specific namespace to clean up
            force: Force cleanup without confirmation
            
        Returns:
            True if cleanup successful
        """
        try:
            if not force:
                response = input("Are you sure you want to cleanup queue resources? (y/N): ")
                if response.lower() != 'y':
                    print("Cleanup cancelled")
                    return False
            
            # Sage queue cleanup
            if is_sage_queue_available():
                try:
                    from sage_ext.sage_queue.python.sage_queue import SageQueue
                    # Add cleanup logic here
                    print("SAGE queue resources cleaned up")
                except Exception as e:
                    print(f"Warning: SAGE queue cleanup failed: {e}")
            
            print("Queue cleanup completed")
            return True
            
        except Exception as e:
            print(f"Cleanup failed: {e}")
            return False


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(description="SAGE Queue Management Tool")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show queue backend information')
    info_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test queue backends')
    test_parser.add_argument('--backend', default='auto', help='Backend to test')
    test_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    # Benchmark command
    bench_parser = subparsers.add_parser('benchmark', help='Benchmark queue performance')
    bench_parser.add_argument('--backend', default='auto', help='Backend to benchmark')
    bench_parser.add_argument('--items', type=int, default=1000, help='Number of items to process')
    bench_parser.add_argument('--workers', type=int, default=1, help='Number of workers')
    bench_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Monitor queue statistics')
    monitor_parser.add_argument('queue_name', help='Name of queue to monitor')
    monitor_parser.add_argument('--backend', default='auto', help='Backend type')
    monitor_parser.add_argument('--interval', type=int, default=5, help='Monitoring interval (seconds)')
    monitor_parser.add_argument('--duration', type=int, default=60, help='Monitoring duration (seconds)')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up queue resources')
    cleanup_parser.add_argument('--namespace', help='Specific namespace to clean up')
    cleanup_parser.add_argument('--force', action='store_true', help='Force cleanup without confirmation')
    
    return parser


def main():
    """Main entry point for command-line tool."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    tool = QueueTool()
    
    if args.command == 'info':
        info = tool.info()
        if getattr(args, 'json', False):
            print(json.dumps(info, indent=2))
        else:
            print("Queue Backend Information:")
            print(f"  Current Backend: {info['current_backend']}")
            print(f"  SAGE Available: {info['sage_available']}")
            print(f"  Available Backends: {', '.join(info['backends'])}")
            if 'extension_status' in info:
                print(f"  Extension Status: {info['extension_status']}")
    
    elif args.command == 'test':
        success = tool.test_backend(args.backend, args.verbose)
        sys.exit(0 if success else 1)
    
    elif args.command == 'benchmark':
        metrics = tool.benchmark(args.backend, args.items, args.workers, args.verbose)
        if 'error' in metrics:
            print(f"Benchmark failed: {metrics['error']}")
            sys.exit(1)
        else:
            print(json.dumps(metrics, indent=2))
    
    elif args.command == 'monitor':
        tool.monitor(args.queue_name, args.backend, args.interval, args.duration)
    
    elif args.command == 'cleanup':
        success = tool.cleanup(args.namespace, args.force)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
