#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAGE Issues 管理 - 测试套件
基于原始test_issues_manager.sh的Python实现
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

import typer
from rich.console import Console
from rich.progress import Progress, track
from rich.table import Table
from rich.panel import Panel

from .config import IssuesConfig
from .manager import IssuesManager

console = Console()

class IssuesTestSuite:
    """Issues管理测试套件"""
    
    def __init__(self):
        self.config = IssuesConfig()
        self.manager = IssuesManager()
        self.test_results: List[Tuple[str, bool, str]] = []
        self.backup_dir = None
        
    def setup(self) -> bool:
        """初始化测试环境"""
        console.print("🔧 [bold blue]初始化测试环境...[/bold blue]")
        
        # 创建备份目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = Path(f"/tmp/issues_test_backup_{timestamp}")
        self.backup_dir.mkdir(exist_ok=True)
        
        # 确保工作目录存在
        self.config.workspace_path.mkdir(parents=True, exist_ok=True)
        self.config.output_path.mkdir(parents=True, exist_ok=True)
        self.config.metadata_path.mkdir(parents=True, exist_ok=True)
        
        return True
    
    def teardown(self):
        """清理测试环境"""
        console.print("🧹 [bold yellow]清理测试环境...[/bold yellow]")
        
        # 清理临时文件
        if self.backup_dir and self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
    
    def test_config_validation(self) -> bool:
        """测试配置验证"""
        try:
            # 测试基本配置存在性
            config_attrs = ['GITHUB_OWNER', 'GITHUB_REPO', 'project_root', 'workspace_path', 'output_path']
            for attr in config_attrs:
                if not hasattr(self.config, attr):
                    console.print(f"❌ 配置缺少属性: {attr}")
                    return False
            
            # 检查基本值
            if not self.config.GITHUB_OWNER or not self.config.GITHUB_REPO:
                console.print("❌ GitHub仓库配置不完整")
                return False
                
            return True
        except Exception as e:
            console.print(f"❌ 配置验证失败: {e}")
            return False
    
    def test_github_connection(self) -> bool:
        """测试GitHub连接"""
        try:
            # 使用manager的内置连接测试
            return self.manager.test_github_connection()
        except Exception as e:
            console.print(f"❌ GitHub连接测试失败: {e}")
            return False
    
    def test_download_functionality(self) -> bool:
        """测试下载功能"""
        try:
            # 检查下载脚本是否存在
            download_script = Path(__file__).parent / "helpers" / "download_issues.py"
            download_v2_script = Path(__file__).parent / "helpers" / "download_issues_v2.py"
            
            # 至少有一个下载脚本存在
            return download_script.exists() or download_v2_script.exists()
            
        except Exception as e:
            console.print(f"❌ 下载功能测试失败: {e}")
            return False
    
    def test_stats_generation(self) -> bool:
        """测试统计生成"""
        try:
            # 使用manager的统计功能
            success = self.manager.show_statistics()
            return success
        except Exception as e:
            console.print(f"❌ 统计生成测试失败: {e}")
            return False
    
    def test_team_analysis(self) -> bool:
        """测试团队分析"""
        try:
            # 检查团队信息加载
            team_info = self.manager.team_info
            
            # 检查基本团队信息结构
            return isinstance(team_info, dict) and len(team_info) > 0
        except Exception as e:
            console.print(f"❌ 团队分析测试失败: {e}")
            return False
    
    def test_file_operations(self) -> bool:
        """测试文件操作"""
        try:
            # 测试临时文件创建和删除
            test_file = self.config.workspace_path / "test_file.json"
            test_file.write_text('{"test": true}')
            
            exists = test_file.exists()
            test_file.unlink()
            
            return exists and not test_file.exists()
        except Exception as e:
            console.print(f"❌ 文件操作测试失败: {e}")
            return False
    
    def run_test(self, test_name: str, test_func) -> bool:
        """运行单个测试"""
        console.print(f"▶️  运行测试: {test_name}")
        
        try:
            result = test_func()
            status = "✅ PASS" if result else "❌ FAIL"
            console.print(f"   {status}")
            
            self.test_results.append((test_name, result, ""))
            return result
        except Exception as e:
            console.print(f"   ❌ ERROR: {e}")
            self.test_results.append((test_name, False, str(e)))
            return False
    
    def run_all_tests(self) -> bool:
        """运行所有测试"""
        console.print(Panel.fit("🧪 [bold blue]SAGE Issues 管理测试套件[/bold blue]", 
                               border_style="blue"))
        
        if not self.setup():
            console.print("❌ 测试环境初始化失败")
            return False
        
        tests = [
            ("配置验证", self.test_config_validation),
            ("GitHub连接", self.test_github_connection),
            ("文件操作", self.test_file_operations),
            ("下载功能", self.test_download_functionality),
            ("统计生成", self.test_stats_generation),
            ("团队分析", self.test_team_analysis),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in track(tests, description="运行测试..."):
            if self.run_test(test_name, test_func):
                passed += 1
        
        # 生成测试报告
        self.generate_report(passed, total)
        
        # 清理
        self.teardown()
        
        return passed == total
    
    def generate_report(self, passed: int, total: int):
        """生成测试报告"""
        console.print("\n" + "="*60)
        console.print(f"📊 [bold blue]测试结果汇总[/bold blue]")
        console.print("="*60)
        
        table = Table(title="测试详情")
        table.add_column("测试项", style="cyan")
        table.add_column("状态", style="green")
        table.add_column("备注", style="yellow")
        
        for test_name, result, error in self.test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            table.add_row(test_name, status, error or "")
        
        console.print(table)
        
        # 汇总统计
        console.print(f"\n📈 总计: {total} 个测试")
        console.print(f"✅ 通过: {passed} 个")
        console.print(f"❌ 失败: {total - passed} 个")
        console.print(f"📊 成功率: {passed/total*100:.1f}%")
        
        if passed == total:
            console.print("\n🎉 [bold green]所有测试通过！[/bold green]")
        else:
            console.print(f"\n⚠️  [bold yellow]{total - passed} 个测试失败[/bold yellow]")


def main():
    """测试主函数"""
    test_suite = IssuesTestSuite()
    success = test_suite.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()