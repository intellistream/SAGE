#!/usr/bin/env python3
"""
示例：演示RemoteEnvironment的环境检查和对齐功能

这个脚本展示如何使用新的环境检查功能来解决多租户环境不一致的问题。
"""

import logging
from pathlib import Path
from sage_core.api.remote_environment import RemoteEnvironment
from sage_utils.logging_utils import configure_logging

def main():
    """主函数，演示环境检查功能"""
    
    # 配置日志
    configure_logging(level=logging.INFO)
    
    print("=" * 60)
    print("SAGE RemoteEnvironment 环境检查示例")
    print("=" * 60)
    
    # 创建RemoteEnvironment实例
    print("\n1. 创建RemoteEnvironment实例...")
    try:
        env = RemoteEnvironment(
            name="env_check_demo",
            config={},
            host="127.0.0.1",
            port=19001
        )
        print("   ✓ RemoteEnvironment创建成功")
    except Exception as e:
        print(f"   ✗ RemoteEnvironment创建失败: {e}")
        return
    
    # 检查远程JobManager连接
    print("\n2. 检查远程JobManager连接...")
    try:
        health = env.health_check()
        if health.get("status") == "success":
            print("   ✓ 远程JobManager连接正常")
        else:
            print(f"   ⚠ 远程JobManager连接有问题: {health.get('message')}")
    except Exception as e:
        print(f"   ✗ 无法连接到远程JobManager: {e}")
        return
    
    # 执行环境兼容性检查
    print("\n3. 执行环境兼容性检查...")
    try:
        compatibility = env.check_environment_compatibility(detailed=True)
        
        if compatibility["compatible"]:
            print("   ✓ 环境兼容性检查通过")
        else:
            print("   ⚠ 环境兼容性检查发现问题")
        
        # 显示警告
        if compatibility["warnings"]:
            print("   警告:")
            for warning in compatibility["warnings"]:
                print(f"     - {warning}")
        
        # 显示错误
        if compatibility["errors"]:
            print("   错误:")
            for error in compatibility["errors"]:
                print(f"     - {error}")
        
        # 显示详细环境信息
        if "local_env" in compatibility:
            local_env = compatibility["local_env"]
            remote_env = compatibility["remote_env"]
            
            print(f"\n   本地环境:")
            print(f"     Python版本: {local_env.get('python_version', 'N/A').split()[0]}")
            print(f"     虚拟环境: {local_env.get('virtual_env') or local_env.get('conda_env', 'N/A')}")
            print(f"     Ray版本: {local_env.get('ray_version', 'N/A')}")
            
            print(f"   远程环境:")
            print(f"     Python版本: {remote_env.get('python_version', 'N/A').split()[0] if remote_env.get('python_version') else 'N/A'}")
            print(f"     虚拟环境: {remote_env.get('virtual_env') or remote_env.get('conda_env', 'N/A')}")
            print(f"     Ray版本: {remote_env.get('ray_version', 'N/A')}")
            
    except Exception as e:
        print(f"   ✗ 环境兼容性检查失败: {e}")
        return
    
    # 如果有兼容性问题，演示环境对齐
    if not compatibility["compatible"] or compatibility["warnings"]:
        print("\n4. 尝试环境对齐...")
        try:
            alignment_result = env.align_environment()
            
            if alignment_result["status"] == "success":
                if alignment_result["alignment_performed"]:
                    print("   ✓ 环境对齐已启动 (进程将重启)")
                else:
                    print("   ✓ 环境已兼容，无需对齐")
            else:
                print(f"   ⚠ 环境对齐失败: {alignment_result['message']}")
                
                if "compatibility_issues" in alignment_result:
                    issues = alignment_result["compatibility_issues"]
                    if issues["warnings"]:
                        print("     未解决的警告:")
                        for warning in issues["warnings"]:
                            print(f"       - {warning}")
                    if issues["errors"]:
                        print("     未解决的错误:")
                        for error in issues["errors"]:
                            print(f"       - {error}")
        except Exception as e:
            print(f"   ✗ 环境对齐过程失败: {e}")
    else:
        print("\n4. 环境兼容性良好，跳过对齐步骤")
    
    # 模拟创建一个简单的pipeline
    print("\n5. 测试环境提交...")
    try:
        # 创建一个简单的pipeline用于测试
        from sage_common_funs.io.source import FileSource
        from sage_common_funs.io.sink import TerminalSink
        
        # 模拟数据源（测试用）
        test_stream = env.from_source(FileSource, {"file_path": "/tmp/test.txt"})
        test_stream.sink(TerminalSink, {"prefix": "[TEST]"})
        
        print("   Pipeline创建成功，尝试提交...")
        
        # 执行提交 (这会触发环境检查和可能的对齐)
        env.submit()
        print("   ✓ Environment提交成功!")
        
    except Exception as e:
        print(f"   ✗ Environment提交失败: {e}")
        
        # 分析失败原因
        if "serialization" in str(e).lower():
            print("     -> 这可能是由于序列化兼容性问题造成的")
            print("     -> 建议检查本地和远程环境的依赖版本一致性")
        elif "ray" in str(e).lower():
            print("     -> 这可能是Ray版本或配置问题")
            print("     -> 建议确保本地和远程使用相同版本的Ray")
    
    finally:
        # 清理资源
        try:
            if hasattr(env, 'env_uuid') and env.env_uuid:
                env.close()
        except:
            pass
    
    print("\n" + "=" * 60)
    print("环境检查示例完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
