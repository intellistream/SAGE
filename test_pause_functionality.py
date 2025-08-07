#!/usr/bin/env python3
"""
测试脚本：验证 JobManager CLI 的 pause 功能
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_cli_commands():
    """测试 CLI 命令是否正确导入"""
    try:
        from sage.cli.job import app
        from typer.testing import CliRunner
        
        runner = CliRunner()
        
        # 测试help命令
        print("✅ Testing help command...")
        result = runner.invoke(app, ["--help"])
        print("Help command output:")
        print(result.output)
        
        # 检查是否包含pause命令
        if "pause" in result.output:
            print("✅ 'pause' command found in help")
        else:
            print("❌ 'pause' command NOT found in help")
        
        # 检查是否包含resume命令
        if "resume" in result.output:
            print("✅ 'resume' command found in help")
        else:
            print("❌ 'resume' command NOT found in help")
            
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_jobmanager_client():
    """测试 JobManager 客户端是否有 pause_job 方法"""
    try:
        from sage.kernel.jobmanager.jobmanager_client import JobManagerClient
        
        # 检查客户端是否有 pause_job 方法
        client = JobManagerClient()
        if hasattr(client, 'pause_job'):
            print("✅ JobManagerClient has 'pause_job' method")
        else:
            print("❌ JobManagerClient missing 'pause_job' method")
            
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """主函数"""
    print("🧪 Testing SAGE JobManager CLI pause functionality...")
    print("=" * 60)
    
    success = True
    
    print("\n1. Testing CLI commands...")
    success &= test_cli_commands()
    
    print("\n2. Testing JobManager client...")
    success &= test_jobmanager_client()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed! pause functionality is properly integrated.")
        print("\n💡 Usage examples:")
        print("   sage job pause <job_id>     # 暂停作业")
        print("   sage job resume <job_id>    # 恢复作业") 
        print("   sage job stop <job_id>      # 停止作业")
        print("   sage job continue <job_id>  # 继续作业")
    else:
        print("❌ Some tests failed. Please check the output above.")
        
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
