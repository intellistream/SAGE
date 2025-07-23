#!/usr/bin/env python3
"""
SAGE Memory-Mapped Queue Benchmark Workers
独立的工作进程函数，用于支持多进程基准测试
"""

import time
from typing import Dict, Any
from sage_queue import SageQueue


def benchmark_multiprocess_worker(queue_name: str, worker_id: int, num_operations: int) -> Dict[str, Any]:
    """多进程基准测试工作函数 - 必须在模块顶层定义以支持 pickle"""
    try:
        queue = SageQueue(queue_name)
        
        start_time = time.time()
        completed = 0
        
        for i in range(num_operations):
            message = {
                'worker_id': worker_id,
                'operation_id': i,
                'timestamp': time.time(),
                'data': f'process_{worker_id}_op_{i}'
            }
            
            # Put message
            queue.put(message, timeout=15.0)
            
            # Get message (might not be our own)
            retrieved = queue.get(timeout=15.0)
            
            completed += 2  # put + get
        
        end_time = time.time()
        queue.close()
        
        return {
            'worker_id': worker_id,
            'completed': completed,
            'duration': end_time - start_time,
            'ops_per_sec': completed / (end_time - start_time) if end_time > start_time else 0
        }
        
    except Exception as e:
        return {
            'worker_id': worker_id,
            'error': str(e),
            'completed': completed if 'completed' in locals() else 0
        }
