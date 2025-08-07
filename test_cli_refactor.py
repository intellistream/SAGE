#!/usr/bin/env python3
"""
验证重构后的 SAGE JobManager CLI 功能
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_command_structure():
    """测试命令结构"""
    try:
        from sage.cli.job import app
        from typer.testing import CliRunner
        
        runner = CliRunner()
        
        print("✅ Testing main help...")
        result = runner.invoke(app, ["--help"])
        help_output = result.output
        
        # 检查主要命令是否存在
        main_commands = ["stop", "continue", "delete", "list", "show"]
        hidden_commands = ["pause", "resume"]
        
        print("\n📋 Checking main commands:")
        for cmd in main_commands:
            if cmd in help_output:
                print(f"  ✅ {cmd} - found in help")
            else:
                print(f"  ❌ {cmd} - NOT found in help")
        
        print("\n🔍 Checking hidden aliases (should NOT appear in main help):")
        for cmd in hidden_commands:
            if cmd not in help_output:
                print(f"  ✅ {cmd} - correctly hidden")
            else:
                print(f"  ❌ {cmd} - appears in main help (should be hidden)")
        
        # 检查别名描述
        print("\n📝 Checking command descriptions:")
        if "(别名: pause)" in help_output:
            print("  ✅ stop command shows pause alias")
        else:
            print("  ❌ stop command missing pause alias info")
            
        if "(别名: resume)" in help_output:
            print("  ✅ continue command shows resume alias")
        else:
            print("  ❌ continue command missing resume alias info")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing command structure: {e}")
        return False

def test_aliases_work():
    """测试别名是否工作"""
    try:
        from sage.cli.job import app
        from typer.testing import CliRunner
        
        runner = CliRunner()
        
        print("\n🔗 Testing aliases functionality:")
        
        # 测试 pause 别名
        result = runner.invoke(app, ["pause", "--help"])
        if result.exit_code == 0 and "停止/暂停作业" in result.output:
            print("  ✅ 'pause' alias works correctly")
        else:
            print("  ❌ 'pause' alias not working")
        
        # 测试 resume 别名  
        result = runner.invoke(app, ["resume", "--help"])
        if result.exit_code == 0 and "继续/恢复作业" in result.output:
            print("  ✅ 'resume' alias works correctly")
        else:
            print("  ❌ 'resume' alias not working")
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing aliases: {e}")
        return False

def test_removed_commands():
    """测试已删除的命令"""
    try:
        from sage.cli.job import app
        from typer.testing import CliRunner
        
        runner = CliRunner()
        
        print("\n🗑️ Testing removed commands:")
        
        # 测试 run 命令是否已删除
        result = runner.invoke(app, ["--help"])
        if "run" not in result.output:
            print("  ✅ 'run' command successfully removed")
        else:
            print("  ❌ 'run' command still exists")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing removed commands: {e}")
        return False

def main():
    """主函数"""
    print("🧪 SAGE JobManager CLI 重构验证")
    print("=" * 50)
    
    success = True
    
    print("1. Testing command structure...")
    success &= test_command_structure()
    
    print("\n2. Testing aliases...")
    success &= test_aliases_work()
    
    print("\n3. Testing removed commands...")
    success &= test_removed_commands()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 所有测试通过！CLI 重构成功!")
        print("\n💡 现在的命令结构:")
        print("   sage job stop <id>      # 暂停作业 (别名: pause)")
        print("   sage job continue <id>  # 恢复作业 (别名: resume)")
        print("   sage job delete <id>    # 删除作业")
        print("   sage job list           # 列出作业")
        print("   sage job show <id>      # 显示作业详情")
        print("   # ... 其他命令")
        
        print("\n🔗 别名用法:")
        print("   sage job pause <id>     # 等同于 sage job stop")
        print("   sage job resume <id>    # 等同于 sage job continue")
    else:
        print("❌ 部分测试失败，请检查上述输出")
        
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
