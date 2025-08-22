#!/usr/bin/env python3
"""
通用GitHub Issue创建工具
支持交互式创建或通过命令行参数创建
"""

import os
import sys
import requests
import json
import argparse
from typing import List, Optional

class GitHubIssueCreator:
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.repo = "intellistream/SAGE"
        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def validate_token(self) -> bool:
        """验证GitHub token是否有效"""
        if not self.github_token:
            print("❌ 请设置GITHUB_TOKEN环境变量")
            print("💡 提示: export GITHUB_TOKEN='your_token_here'")
            return False
        return True
    
    def get_available_labels(self) -> List[str]:
        """获取仓库可用的标签"""
        try:
            url = f"https://api.github.com/repos/{self.repo}/labels"
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                labels = response.json()
                return [label['name'] for label in labels]
        except Exception as e:
            print(f"⚠️ 获取标签失败: {e}")
        return []
    
    def interactive_input(self) -> dict:
        """交互式输入issue信息"""
        print("\n🎯 创建新的GitHub Issue")
        print("=" * 40)
        
        # 标题
        while True:
            title = input("\n📝 请输入Issue标题: ").strip()
            if title:
                break
            print("❌ 标题不能为空，请重新输入")
        
        # 描述
        print("\n📄 请输入Issue描述 (输入空行结束):")
        body_lines = []
        while True:
            line = input()
            if line.strip() == "":
                break
            body_lines.append(line)
        body = "\n".join(body_lines)
        
        if not body.strip():
            body = "待补充详细描述..."
        
        # 标签
        available_labels = self.get_available_labels()
        if available_labels:
            print(f"\n🏷️ 可用标签: {', '.join(available_labels[:10])}...")
            labels_input = input("请输入标签 (用逗号分隔，留空跳过): ").strip()
            labels = [label.strip() for label in labels_input.split(',') if label.strip()] if labels_input else []
        else:
            labels = []
        
        # 分配给某人 (可选)
        assignee = input("\n👤 分配给 (GitHub用户名，留空跳过): ").strip() or None
        
        # 里程碑 (可选)
        milestone = input("\n🎯 里程碑编号 (留空跳过): ").strip()
        milestone = int(milestone) if milestone.isdigit() else None
        
        return {
            "title": title,
            "body": body,
            "labels": labels,
            "assignee": assignee,
            "milestone": milestone
        }
    
    def create_issue(self, issue_data: dict) -> bool:
        """创建GitHub Issue"""
        # 清理数据，移除空值
        clean_data = {k: v for k, v in issue_data.items() if v is not None and v != []}
        
        url = f"https://api.github.com/repos/{self.repo}/issues"
        
        print(f"\n🚀 正在创建GitHub Issue...")
        print(f"📝 标题: {clean_data['title']}")
        if clean_data.get('labels'):
            print(f"🏷️ 标签: {', '.join(clean_data['labels'])}")
        if clean_data.get('assignee'):
            print(f"👤 分配给: {clean_data['assignee']}")
        
        try:
            response = requests.post(url, headers=self.headers, json=clean_data)
            
            if response.status_code == 201:
                issue_info = response.json()
                print(f"\n✅ Issue创建成功!")
                print(f"🔗 Issue链接: {issue_info['html_url']}")
                print(f"📊 Issue编号: #{issue_info['number']}")
                return True
            else:
                print(f"\n❌ 创建失败! 状态码: {response.status_code}")
                print(f"错误信息: {response.text}")
                return False
                
        except Exception as e:
            print(f"\n❌ 发生错误: {str(e)}")
            return False

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='创建GitHub Issue')
    parser.add_argument('--title', '-t', help='Issue标题')
    parser.add_argument('--body', '-b', help='Issue描述')
    parser.add_argument('--labels', '-l', help='标签 (用逗号分隔)')
    parser.add_argument('--assignee', '-a', help='分配给的用户')
    parser.add_argument('--milestone', '-m', type=int, help='里程碑编号')
    parser.add_argument('--file', '-f', help='从文件读取issue内容 (JSON格式)')
    
    return parser.parse_args()

def load_from_file(file_path: str) -> Optional[dict]:
    """从文件加载issue数据"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return None

def main():
    print("🎯 GitHub Issue 创建工具")
    print("=" * 40)
    
    creator = GitHubIssueCreator()
    
    # 验证GitHub token
    if not creator.validate_token():
        sys.exit(1)
    
    args = parse_arguments()
    
    # 确定issue数据来源
    if args.file:
        # 从文件读取
        issue_data = load_from_file(args.file)
        if not issue_data:
            sys.exit(1)
    elif args.title:
        # 从命令行参数
        issue_data = {
            "title": args.title,
            "body": args.body or "待补充详细描述...",
            "labels": args.labels.split(',') if args.labels else [],
            "assignee": args.assignee,
            "milestone": args.milestone
        }
    else:
        # 交互式输入
        issue_data = creator.interactive_input()
    
    # 创建issue
    success = creator.create_issue(issue_data)
    
    if success:
        print("\n🎉 任务完成! Issue已成功创建到GitHub仓库。")
    else:
        print("\n💡 提示: 请检查网络连接和GitHub token权限。")
        sys.exit(1)

if __name__ == "__main__":
    main()
