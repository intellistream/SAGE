#!/usr/bin/env python3
"""
Issues错误分配修复执行脚本

功能:
- 根据修复计划文件执行issues的移动操作
- 支持dry-run模式进行预览
- 自动从源项目删除并添加到目标项目
- 完整的错误处理和状态报告

使用方法:
    # Dry-run模式 (默认)
    python3 execute_fix_plan.py <fix_plan_file.json>
    
    # 实际执行修复
    python3 execute_fix_plan.py <fix_plan_file.json> --live

输出:
- 执行结果文件: output/fix_execution_result_<timestamp>.json
- 详细的修复状态报告

作者: SAGE Team  
日期: 2025-08-30
"""

import json
import time
import sys
from pathlib import Path
from helpers.project_manage import IssueProjectMover

def execute_fix_plan(fix_plan_file: str, dry_run: bool = True):
    """
    执行修复计划
    
    Args:
        fix_plan_file: 修复计划JSON文件路径
        dry_run: 是否为dry-run模式 (True=预览, False=实际执行)
    """
    
    # 读取修复计划
    with open(fix_plan_file, 'r', encoding='utf-8') as f:
        fix_plan = json.load(f)
    
    print(f"📋 加载修复计划: {fix_plan_file}")
    print(f"📊 计划修复 {fix_plan['total_fixes_needed']} 个错误分配的issues")
    
    if dry_run:
        print("🔍 DRY RUN模式 - 仅显示将要执行的操作，不实际修改")
    else:
        print("⚠️  LIVE模式 - 将实际执行修复操作")
        
        response = input("确认要执行实际修复吗？(yes/no): ")
        if response.lower() != 'yes':
            print("❌ 操作已取消")
            return
    
    pm = IssueProjectMover()
    
    # 预加载所有issues的ID映射
    if not dry_run:
        print("📥 预加载issues的全局ID映射...")
        all_issues = pm.get_all_repository_issues()
        issue_id_map = {issue['number']: issue.get('node_id') for issue in all_issues}
        print(f"✅ 已加载 {len(issue_id_map)} 个issues的ID映射")
    
    success_count = 0
    error_count = 0
    errors = []
    
    for i, fix in enumerate(fix_plan['fixes'], 1):
        issue_number = fix['issue_number']
        author = fix['author']
        current_project = fix['current_project']
        target_project = fix['target_project']
        item_id = fix['item_id']
        
        print(f"\n[{i}/{len(fix_plan['fixes'])}] 处理Issue #{issue_number}")
        print(f"  📝 {fix['issue_title']}")
        print(f"  👤 作者: {author}")
        print(f"  📦 从项目#{current_project} ({fix['current_project_name']}) → 项目#{target_project} ({fix['target_project_name']})")
        
        if dry_run:
            print(f"  ✅ DRY RUN: 将会移动此issue")
            success_count += 1
        else:
            try:
                # 获取目标项目的ID
                target_project_data = pm.get_project_by_number(target_project)
                if not target_project_data:
                    raise Exception(f"无法获取目标项目#{target_project}的数据")
                
                target_project_id = target_project_data['id']
                
                # 获取issue的正确全局ID
                issue_global_id = issue_id_map.get(issue_number)
                if not issue_global_id:
                    raise Exception(f"无法找到Issue #{issue_number}的全局ID")
                
                # 先添加到目标项目
                success_add, add_result = pm.add_issue_to_project(target_project_id, issue_global_id)
                
                if success_add:
                    print(f"  ✅ 成功添加到项目#{target_project}")
                    
                    # 现在从源项目删除
                    current_project_data = pm.get_project_by_number(current_project)
                    if current_project_data:
                        current_project_id = current_project_data['id']
                        
                        # 查找item_id （需要重新获取，因为可能已经变化）
                        old_project_number = pm.ORG_PROJECT_NUMBER
                        pm.ORG_PROJECT_NUMBER = current_project
                        
                        try:
                            current_project_items = pm.get_org_project()
                            if current_project_items and 'items' in current_project_items:
                                items = current_project_items['items']['nodes']
                                
                                item_id_to_delete = None
                                for item in items:
                                    content = item.get('content', {})
                                    if content.get('number') == issue_number:
                                        item_id_to_delete = item.get('id')
                                        break
                                
                                if item_id_to_delete:
                                    success_delete, delete_result = pm.delete_project_item(current_project_id, item_id_to_delete)
                                    if success_delete:
                                        print(f"  🗑️  成功从项目#{current_project}中删除")
                                        print(f"  🎉 Issue #{issue_number} 完整移动成功!")
                                        success_count += 1
                                    else:
                                        print(f"  ⚠️  删除失败: {delete_result}")
                                        print(f"  ✅ 已添加到目标项目，但请手动从源项目删除")
                                        success_count += 1  # 仍然算作部分成功
                                else:
                                    print(f"  ⚠️  在项目#{current_project}中找不到item，可能已不在该项目中")
                                    success_count += 1  # 算作成功，因为已经添加到目标项目
                        finally:
                            pm.ORG_PROJECT_NUMBER = old_project_number
                    else:
                        print(f"  ⚠️  无法获取源项目#{current_project}数据")
                        success_count += 1  # 仍然算作成功，因为已经添加到目标项目
                else:
                    error_msg = f"添加到项目#{target_project}失败: {add_result}"
                    print(f"  ❌ {error_msg}")
                    errors.append({
                        'issue_number': issue_number,
                        'error': error_msg,
                        'fix': fix
                    })
                    error_count += 1
                
                # 添加延迟避免API限制
                time.sleep(0.5)
                
            except Exception as e:
                error_msg = f"处理Issue #{issue_number}时出错: {str(e)}"
                print(f"  ❌ {error_msg}")
                errors.append({
                    'issue_number': issue_number,
                    'error': error_msg,
                    'fix': fix
                })
                error_count += 1
    
    # 显示结果摘要
    print(f"\n📊 修复结果摘要:")
    print(f"  ✅ 成功: {success_count}")
    print(f"  ❌ 失败: {error_count}")
    
    if errors:
        print(f"\n❌ 错误详情:")
        for error in errors:
            print(f"  Issue #{error['issue_number']}: {error['error']}")
    
    # 保存执行结果
    result = {
        'execution_time': time.time(),
        'fix_plan_file': fix_plan_file,
        'dry_run': dry_run,
        'total_processed': len(fix_plan['fixes']),
        'success_count': success_count,
        'error_count': error_count,
        'errors': errors
    }
    
    output_dir = Path(fix_plan_file).parent
    result_file = output_dir / f"fix_execution_result_{int(time.time())}.json"
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 执行结果已保存到: {result_file}")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python3 execute_fix_plan.py <fix_plan_file.json> [--live]")
        print("  --live: 实际执行修复 (默认为dry-run模式)")
        return
    
    fix_plan_file = sys.argv[1]
    dry_run = "--live" not in sys.argv
    
    if not Path(fix_plan_file).exists():
        print(f"❌ 修复计划文件不存在: {fix_plan_file}")
        return
    
    execute_fix_plan(fix_plan_file, dry_run)

if __name__ == "__main__":
    main()
