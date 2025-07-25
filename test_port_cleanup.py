#!/usr/bin/env python3
"""
测试JobManager的端口释放和启动问题
"""

import sys
import os
import time
sys.path.insert(0, '/home/tjy/SAGE')

from sage.cli.jobmanager import JobManagerController

def test_port_cleanup_logic():
    """测试端口清理逻辑"""
    controller = JobManagerController()
    
    print("=== JobManager Port Cleanup Test ===")
    
    # 检查当前端口状态
    port_occupied = controller.is_port_occupied()
    print(f"Port {controller.port} occupied: {port_occupied}")
    
    if port_occupied:
        print("\n=== Testing Port Process Detection ===")
        
        # 测试各种端口进程检测方法
        print("1. Using lsof:")
        lsof_pids = controller._find_port_processes_lsof()
        print(f"   Found PIDs: {lsof_pids}")
        
        print("2. Using netstat:")
        netstat_pids = controller._find_port_processes_netstat()
        print(f"   Found PIDs: {netstat_pids}")
        
        print("3. Using fuser:")
        fuser_pids = controller._find_port_processes_fuser()
        print(f"   Found PIDs: {fuser_pids}")
        
        all_pids = set(lsof_pids + netstat_pids + fuser_pids)
        print(f"\nAll unique PIDs: {all_pids}")
        
        # 显示每个进程的详细信息
        for pid in all_pids:
            proc_info = controller._get_process_info(pid)
            print(f"\nProcess {pid}:")
            print(f"  User: {proc_info['user']}")
            print(f"  Name: {proc_info['name']}")
            print(f"  Status: {proc_info['status']}")
            print(f"  Command: {proc_info['cmdline']}")
    
    print("\n=== Testing Port Binding Permission ===")
    can_bind = controller._check_port_binding_permission()
    print(f"Can bind to port {controller.port}: {can_bind}")
    
    print("\n=== Startup Process Analysis ===")
    print("For successful cross-user startup:")
    print("1. ✅ Kill existing processes (with sudo if needed)")
    print("2. ✅ Wait for port to be released")  
    print("3. ✅ Perform aggressive port cleanup if needed")
    print("4. ✅ Verify port binding permission")
    print("5. ✅ Start new JobManager process")
    print("6. ✅ Wait for service to be ready")
    
    print("\nPotential failure points:")
    print("- Port not released after process kill")
    print("- Permission denied for port binding")
    print("- Service startup failure")
    print("- Health check timeout")

if __name__ == "__main__":
    test_port_cleanup_logic()
