#!/usr/bin/env python3
"""
本地测试运行器 - 模拟GitHub Actions workflow的本地调试版本

用于本地调试和快速测试各种测试策略，避免频繁提交到GitHub Actions。
支持模拟各种workflow场景，包括PR测试、智能测试等。

Usage:
    python scripts/local_test_runner.py --smart-test          # 模拟smart-test.yml
    python scripts/local_test_runner.py --intelligent        # 模拟pr-intelligent-testing.yml  
    python scripts/local_test_runner.py --pr-smart           # 模拟pr-smart-testing.yml
    python scripts/local_test_runner.py --all-workflows      # 运行所有workflow测试
    python scripts/local_test_runner.py --compare main       # 与指定分支比较
"""

import os
import sys
import argparse
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional
import json

class LocalWorkflowRunner:
    """本地Workflow运行器"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.scripts_dir = self.project_root / "scripts"
        self.test_runner_path = self.scripts_dir / "test_runner.py"
        self.logs_dir = self.project_root / "local_workflow_logs"
        self.logs_dir.mkdir(exist_ok=True)
        
        # 验证环境
        self._verify_environment()
    
    def _verify_environment(self):
        """验证本地环境"""
        print("🔍 验证本地环境...")
        
        # 检查test_runner.py是否存在
        if not self.test_runner_path.exists():
            print(f"❌ 错误: {self.test_runner_path} 不存在!")
            print("请确保test_runner.py存在于scripts目录中")
            sys.exit(1)
        
        # 检查git是否可用
        try:
            subprocess.run(["git", "--version"], capture_output=True, check=True)
        except subprocess.CalledProcessError:
            print("❌ 错误: git命令不可用!")
            sys.exit(1)
            
        # 检查是否在git仓库中
        try:
            subprocess.run(["git", "rev-parse", "--git-dir"], 
                          capture_output=True, check=True, cwd=self.project_root)
        except subprocess.CalledProcessError:
            print("❌ 错误: 当前目录不是git仓库!")
            sys.exit(1)
            
        print("✅ 环境验证通过")
    
    def _run_command(self, cmd: List[str], description: str, 
                    capture_output: bool = False, timeout: int = 300) -> Dict:
        """运行命令并记录结果"""
        print(f"🚀 {description}")
        print(f"📝 命令: {' '.join(cmd)}")
        
        start_time = time.time()
        result = {
            "command": ' '.join(cmd),
            "description": description,
            "success": False,
            "duration": 0.0,
            "output": "",
            "error": ""
        }
        
        try:
            if capture_output:
                proc_result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=timeout,
                    cwd=self.project_root
                )
                result["output"] = proc_result.stdout
                result["error"] = proc_result.stderr
                result["success"] = proc_result.returncode == 0
                
                if not result["success"]:
                    print(f"❌ 命令失败 (返回代码: {proc_result.returncode})")
                    if proc_result.stderr:
                        print(f"错误输出: {proc_result.stderr[:500]}")
                else:
                    print("✅ 命令执行成功")
            else:
                proc_result = subprocess.run(cmd, timeout=timeout, cwd=self.project_root)
                result["success"] = proc_result.returncode == 0
                
        except subprocess.TimeoutExpired:
            print(f"⏰ 命令超时 ({timeout}秒)")
            result["error"] = f"Command timed out after {timeout} seconds"
        except Exception as e:
            print(f"💥 命令执行异常: {e}")
            result["error"] = str(e)
        
        result["duration"] = time.time() - start_time
        return result
    
    def _get_current_branch(self) -> str:
        """获取当前分支名"""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"], 
                capture_output=True, text=True, check=True,
                cwd=self.project_root
            )
            return result.stdout.strip()
        except:
            return "unknown"
    
    def _get_changed_files(self, base_branch: str = "main") -> List[str]:
        """获取相对于基准分支的变化文件"""
        try:
            # 确保基准分支存在
            subprocess.run(
                ["git", "fetch", "origin", base_branch], 
                capture_output=True, cwd=self.project_root
            )
            
            result = subprocess.run(
                ["git", "diff", "--name-only", f"origin/{base_branch}...HEAD"], 
                capture_output=True, text=True, check=True,
                cwd=self.project_root
            )
            
            files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
            return files
        except Exception as e:
            print(f"⚠️ 获取变化文件失败: {e}")
            return []
    
    def _save_log(self, workflow_name: str, results: List[Dict]):
        """保存workflow运行日志"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_file = self.logs_dir / f"{workflow_name}_{timestamp}.json"
        
        log_data = {
            "workflow": workflow_name,
            "timestamp": timestamp,
            "project_root": str(self.project_root),
            "current_branch": self._get_current_branch(),
            "results": results
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        print(f"📋 运行日志已保存: {log_file}")
        return log_file
    
    def run_smart_test_workflow(self, base_branch: str = "main") -> bool:
        """模拟smart-test.yml workflow"""
        print("\n" + "="*60)
        print("🤖 运行Smart Test Analysis Workflow (本地模拟)")
        print("="*60)
        
        current_branch = self._get_current_branch()
        changed_files = self._get_changed_files(base_branch)
        
        print(f"📊 当前分支: {current_branch}")
        print(f"📊 基准分支: {base_branch}")
        print(f"📊 变化文件数: {len(changed_files)}")
        
        if changed_files:
            print("📄 变化的文件:")
            for f in changed_files[:10]:
                print(f"  - {f}")
            if len(changed_files) > 10:
                print(f"  ... 还有 {len(changed_files) - 10} 个文件")
        
        results = []
        
        # 步骤1: 安装依赖 (模拟)
        print("\n📦 步骤1: 检查依赖")
        results.append({
            "step": "check_dependencies",
            "description": "检查Python依赖",
            "success": True,
            "duration": 0.1
        })
        
        # 步骤2: 构建C扩展 (模拟)
        build_result = self._run_command(
            ["ls", "sage_ext/sage_queue"], 
            "检查C扩展目录", 
            capture_output=True
        )
        results.append({
            "step": "build_extensions",
            "description": "检查C扩展",
            "success": build_result["success"],
            "duration": build_result["duration"]
        })
        
        # 步骤3: 运行智能测试分析
        test_cmd = [
            "python", str(self.test_runner_path), 
            "--diff", 
            f"--base=origin/{base_branch}",
            "--output-format=markdown",
            "--workers=2"
        ]
        
        test_result = self._run_command(
            test_cmd, 
            "运行智能测试分析", 
            capture_output=True,
            timeout=600
        )
        results.append({
            "step": "smart_test_analysis",
            "description": "智能测试分析",
            "success": test_result["success"],
            "duration": test_result["duration"],
            "output": test_result["output"][:1000] if test_result["output"] else "",
            "error": test_result["error"][:1000] if test_result["error"] else ""
        })
        
        # 保存输出
        if test_result["output"]:
            output_file = self.logs_dir / "smart_test_output.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(test_result["output"])
            print(f"📄 测试输出已保存: {output_file}")
        
        # 步骤4: 生成报告
        print("\n📊 生成本地测试报告...")
        self._generate_smart_test_report(results, base_branch, changed_files)
        
        # 保存日志
        self._save_log("smart-test", results)
        
        success = all(r["success"] for r in results)
        print(f"\n{'✅' if success else '❌'} Smart Test Workflow {'成功' if success else '失败'}")
        return success
    
    def run_intelligent_testing_workflow(self, base_branch: str = "main") -> bool:
        """模拟pr-intelligent-testing.yml workflow"""
        print("\n" + "="*60)
        print("🧠 运行Intelligent Testing Workflow (本地模拟)")
        print("="*60)
        
        current_branch = self._get_current_branch()
        changed_files = self._get_changed_files(base_branch)
        
        print(f"📊 当前分支: {current_branch}")
        print(f"📊 基准分支: {base_branch}")
        print(f"📊 变化文件数: {len(changed_files)}")
        
        results = []
        
        # 检查是否跳过
        if len(changed_files) == 0:
            print("ℹ️ 没有检测到变化，跳过测试")
            results.append({
                "step": "check_changes",
                "description": "检查文件变化",
                "success": True,
                "skipped": True,
                "duration": 0.1
            })
            self._save_log("intelligent-testing", results)
            return True
        
        # 显示变化预览
        print(f"🔍 变化文件预览:")
        for f in changed_files[:10]:
            print(f"  - {f}")
        if len(changed_files) > 10:
            print(f"  ... 还有 {len(changed_files) - 10} 个文件")
        
        # 运行智能差异测试
        test_cmd = [
            "python", str(self.test_runner_path),
            "--diff",
            f"--base=origin/{base_branch}",
            "--workers=2"
        ]
        
        test_result = self._run_command(
            test_cmd,
            "运行智能差异测试",
            capture_output=True,
            timeout=2700  # 45分钟超时
        )
        
        results.append({
            "step": "intelligent_diff_testing",
            "description": "智能差异测试",
            "success": test_result["success"],
            "duration": test_result["duration"],
            "changed_files": len(changed_files)
        })
        
        # 生成报告
        self._generate_intelligent_test_report(results, base_branch, changed_files, test_result["success"])
        
        # 保存日志
        self._save_log("intelligent-testing", results)
        
        success = test_result["success"]
        print(f"\n{'✅' if success else '❌'} Intelligent Testing Workflow {'成功' if success else '失败'}")
        return success
    
    def run_pr_smart_testing_workflow(self, base_branch: str = "main") -> bool:
        """模拟pr-smart-testing.yml workflow"""
        print("\n" + "="*60)
        print("🎯 运行PR Smart Testing Workflow (本地模拟)")
        print("="*60)
        
        current_branch = self._get_current_branch()
        changed_files = self._get_changed_files(base_branch)
        
        print(f"📊 当前分支: {current_branch}")
        print(f"📊 基准分支: {base_branch}")
        print(f"📊 变化文件数: {len(changed_files)}")
        
        results = []
        
        # 步骤1: 列出测试目录
        list_cmd = ["python", str(self.test_runner_path), "--list"]
        list_result = self._run_command(
            list_cmd,
            "列出可用测试目录",
            capture_output=True
        )
        results.append({
            "step": "list_test_directories",
            "description": "列出测试目录",
            "success": list_result["success"],
            "duration": list_result["duration"]
        })
        
        # 步骤2: 运行智能差异测试
        test_cmd = [
            "python", str(self.test_runner_path),
            "--diff",
            f"--base=origin/{base_branch}",
            "--workers=2"
        ]
        
        test_result = self._run_command(
            test_cmd,
            "运行智能差异测试",
            capture_output=True,
            timeout=3600  # 60分钟超时
        )
        
        results.append({
            "step": "smart_diff_testing",
            "description": "智能差异测试",
            "success": test_result["success"],
            "duration": test_result["duration"],
            "changed_files": len(changed_files)
        })
        
        # 生成报告
        self._generate_pr_smart_test_report(results, base_branch, changed_files, test_result["success"])
        
        # 保存日志
        self._save_log("pr-smart-testing", results)
        
        success = all(r["success"] for r in results)
        print(f"\n{'✅' if success else '❌'} PR Smart Testing Workflow {'成功' if success else '失败'}")
        return success
    
    def _generate_smart_test_report(self, results: List[Dict], base_branch: str, changed_files: List[str]):
        """生成Smart Test报告"""
        print("\n📊 Smart Test Analysis 报告:")
        print(f"  - 基准分支: {base_branch}")
        print(f"  - 变化文件: {len(changed_files)}")
        print(f"  - 步骤总数: {len(results)}")
        
        for result in results:
            status = "✅" if result["success"] else "❌"
            print(f"  {status} {result['description']}: {result['duration']:.2f}s")
    
    def _generate_intelligent_test_report(self, results: List[Dict], base_branch: str, 
                                        changed_files: List[str], success: bool):
        """生成Intelligent Testing报告"""
        print("\n🧠 Intelligent Testing 报告:")
        print(f"  - 状态: {'✅ PASSED' if success else '❌ FAILED'}")
        print(f"  - 基准分支: {base_branch}")
        print(f"  - 变化文件: {len(changed_files)}")
        print(f"  - 测试策略: 基于差异的智能选择")
        print(f"  - 并行进程: 2")
        
        if success:
            print("  🎉 所有受影响的测试都已通过!")
        else:
            print("  ⚠️ 某些测试失败，需要修复问题")
    
    def _generate_pr_smart_test_report(self, results: List[Dict], base_branch: str,
                                     changed_files: List[str], success: bool):
        """生成PR Smart Testing报告"""
        print("\n🎯 PR Smart Testing 报告:")
        print(f"  - 状态: {'✅ All tests passed!' if success else '❌ Some tests failed'}")
        print(f"  - 策略: 基于差异的智能测试")
        print(f"  - 基准分支: {base_branch}")
        print(f"  - 变化文件: {len(changed_files)}")
        print(f"  - 并行进程: 2")
        
        total_duration = sum(r["duration"] for r in results)
        print(f"  - 总耗时: {total_duration:.2f}s")
        
        if success:
            print("  🎉 准备合并! 所有受影响的测试都已通过。")
        else:
            print("  ⚠️ 需要修复: 请修复失败的测试后再合并。")
    
    def run_all_workflows(self, base_branch: str = "main") -> Dict[str, bool]:
        """运行所有workflow测试"""
        print("\n" + "="*80)
        print("🚀 运行所有Workflow测试 (本地模拟)")
        print("="*80)
        
        workflows = {
            "smart-test": self.run_smart_test_workflow,
            "intelligent-testing": self.run_intelligent_testing_workflow,
            "pr-smart-testing": self.run_pr_smart_testing_workflow
        }
        
        results = {}
        for name, func in workflows.items():
            print(f"\n{'🔄' * 20} 开始 {name} {'🔄' * 20}")
            results[name] = func(base_branch)
            print(f"{'✅' if results[name] else '❌'} {name} 完成")
        
        # 生成总结报告
        print("\n" + "="*80)
        print("📊 所有Workflow测试结果总结:")
        print("="*80)
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        for name, success in results.items():
            status = "✅ 成功" if success else "❌ 失败"
            print(f"  {status} {name}")
        
        print(f"\n📈 总体结果: {success_count}/{total_count} 个workflow成功")
        
        overall_success = success_count == total_count
        print(f"{'🎉 所有测试通过!' if overall_success else '⚠️ 有测试失败，请检查日志'}")
        
        return results

def main():
    parser = argparse.ArgumentParser(
        description="本地Workflow调试运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python scripts/local_test_runner.py --smart-test
  python scripts/local_test_runner.py --intelligent --base develop  
  python scripts/local_test_runner.py --all-workflows
  python scripts/local_test_runner.py --pr-smart --base main
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--smart-test", action="store_true", 
                      help="运行Smart Test Analysis workflow")
    group.add_argument("--intelligent", action="store_true",
                      help="运行Intelligent Testing workflow")
    group.add_argument("--pr-smart", action="store_true",
                      help="运行PR Smart Testing workflow")
    group.add_argument("--all-workflows", action="store_true",
                      help="运行所有workflow测试")
    
    parser.add_argument("--base", default="main",
                       help="基准分支 (默认: main)")
    parser.add_argument("--project-root",
                       help="项目根目录 (默认: 当前目录)")
    
    args = parser.parse_args()
    
    try:
        runner = LocalWorkflowRunner(args.project_root)
        
        success = False
        if args.smart_test:
            success = runner.run_smart_test_workflow(args.base)
        elif args.intelligent:
            success = runner.run_intelligent_testing_workflow(args.base)
        elif args.pr_smart:
            success = runner.run_pr_smart_testing_workflow(args.base)
        elif args.all_workflows:
            results = runner.run_all_workflows(args.base)
            success = all(results.values())
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断了workflow测试")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 运行workflow时出现异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
