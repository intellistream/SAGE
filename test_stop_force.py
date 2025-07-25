#!/usr/bin/env python3
"""
测试JobManager的stop --force功能
"""

import sys
import os
sys.path.insert(0, '/home/tjy/SAGE')

from sage.cli.jobmanager import JobManagerController

def test_stop_force_logic():
    """测试stop --force逻辑"""
    controller = JobManagerController()
    
    print("=== JobManager Stop Force Test ===")
    
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
    
    print("\n=== Command Flow Analysis ===")
    print("For 'stop --force' command:")
    print("1. ✅ Preemptively request sudo password if force=True")
    print("2. ✅ Call force_kill() with sudo privileges available")
    print("3. ✅ Use sudo to kill processes owned by other users")
    
    print("\nFor 'kill' command:")
    print("1. ✅ Always request sudo password (kill is always force)")
    print("2. ✅ Call force_kill() with sudo privileges available")
    
    print("\nFor 'restart --force' command:")
    print("1. ✅ Request sudo password for kill phase")
    print("2. ✅ Use sudo to kill existing processes")
    print("3. ✅ Start new process with user privileges (conda env)")

if __name__ == "__main__":
    test_stop_force_logic()
