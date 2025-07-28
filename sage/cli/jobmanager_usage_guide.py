#!/usr/bin/env python3
"""
JobManager多用户环境使用指南
"""

def print_usage_guide():
    print("=" * 60)
    print("SAGE JobManager 多用户环境使用指南")
    print("=" * 60)
    
    print("\n📋 常见场景和解决方案:")
    
    print("\n1️⃣  启动JobManager (自己使用)")
    print("   命令: sage jobmanager start")
    print("   说明: 在默认端口19001启动JobManager")
    
    print("\n2️⃣  强制启动JobManager (替换其他用户的实例)")
    print("   命令: sage jobmanager start --force")
    print("   说明: 会请求sudo密码，强制终止现有进程并启动新实例")
    print("   注意: 新实例会以当前用户身份运行(保持conda环境)")
    
    print("\n3️⃣  停止JobManager (温和方式)")
    print("   命令: sage jobmanager stop")
    print("   说明: 发送SIGTERM信号，等待进程优雅退出")
    
    print("\n4️⃣  强制停止JobManager (包括其他用户的)")
    print("   命令: sage jobmanager stop --force")
    print("   说明: 会请求sudo密码，强制终止所有JobManager进程")
    
    print("\n5️⃣  强制重启JobManager (跨用户)")
    print("   命令: sage jobmanager restart --force")
    print("   说明: 用sudo强制停止 + 用户权限启动(conda环境)")
    
    print("\n6️⃣  查看JobManager状态")
    print("   命令: sage jobmanager status")
    print("   说明: 显示进程信息、端口占用、进程所有者等")
    
    print("\n7️⃣  强制杀死JobManager")
    print("   命令: sage jobmanager kill")
    print("   说明: 直接发送SIGKILL，会请求sudo权限")
    
    print("\n8️⃣  诊断启动问题")
    print("   命令: sage jobmanager diagnose")
    print("   说明: 检查环境、权限、端口等潜在问题")
    
    print("\n⚠️  权限和安全注意事项:")
    print("   • --force选项会请求sudo密码验证")
    print("   • 只有在必要时才使用sudo权限")
    print("   • 新启动的JobManager始终以当前用户身份运行")
    print("   • 确保conda环境正确激活")
    
    print("\n🔧 故障排除:")
    print("   • 如果启动失败: 先运行 sage jobmanager diagnose")
    print("   • 如果端口被占用: 使用 --force 选项")
    print("   • 如果权限不足: 确保有sudo权限")
    print("   • 如果conda环境错误: 重新激活环境后启动")
    print("   • 多用户冲突: 协调使用不同端口")
    print("   • 端口绑定失败: 尝试不同端口或检查系统限制")
    
    print("\n🚨 常见启动失败原因及解决方案:")
    print("   1. 端口占用问题:")
    print("      问题: Port already in use")
    print("      解决: sage jobmanager start --force")
    print("   ")
    print("   2. 权限问题:")
    print("      问题: Permission denied")
    print("      解决: 检查sudo权限，使用不同端口")
    print("   ")
    print("   3. 环境问题:")
    print("      问题: Module not found")
    print("      解决: 重新激活conda环境，检查SAGE安装")
    print("   ")
    print("   4. 端口释放延迟:")
    print("      问题: 进程已杀死但端口仍占用")
    print("      解决: 等待几秒钟或使用不同端口")
    print("   ")
    print("   5. 跨用户权限冲突:")
    print("      问题: 其他用户的进程无法终止")
    print("      解决: 确保有sudo权限，使用 --force 选项")
    
    print("\n💡 最佳实践:")
    print("   • 使用不同端口避免冲突: --port 19002")
    print("   • 定期检查状态: sage jobmanager status")
    print("   • 启动前先诊断: sage jobmanager diagnose")
    print("   • 优先使用温和停止: sage jobmanager stop")
    print("   • 在共享环境中协调使用")
    
    print("\n🔄 快速排障流程:")
    print("   1. sage jobmanager diagnose    # 诊断问题")
    print("   2. sage jobmanager status      # 检查状态") 
    print("   3. sage jobmanager kill        # 强制清理(如果需要)")
    print("   4. sage jobmanager start       # 重新启动")
    print("   5. 如果还失败，尝试不同端口: --port 19002")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    print_usage_guide()
