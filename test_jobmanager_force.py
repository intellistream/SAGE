#!/usr/bin/env python3
"""
测试JobManager的force功能
"""

import sys
import os
sys.path.insert(0, '/home/tjy/SAGE')

from sage.cli.jobmanager import JobManagerController

def test_force_logic():
    """测试force逻辑"""
    controller = JobManagerController()
    
    print("=== JobManager Force Test ===")
    
    # 查找当前进程
    processes = controller.find_jobmanager_processes()
    print(f"Found {len(processes)} JobManager processes")
    
    current_user = os.getenv('USER', 'unknown')
    print(f"Current user: {current_user}")
    
    for proc in processes:
        proc_info = controller._get_process_info(proc.pid)
        print(f"Process {proc_info['pid']}:")
        print(f"  User: {proc_info['user']}")
        print(f"  Name: {proc_info['name']}")
        print(f"  Status: {proc_info['status']}")
        
        needs_sudo = proc_info['user'] != current_user and proc_info['user'] != 'N/A'
        print(f"  Needs sudo: {needs_sudo}")
    
    print("\n=== Force Restart Simulation ===")
    print("In force restart mode:")
    print("1. Use sudo to kill existing processes (if needed)")
    print("2. Start new process with user privileges (in conda env)")
    print("3. This ensures the new JobManager has access to conda environment")

if __name__ == "__main__":
    test_force_logic()
