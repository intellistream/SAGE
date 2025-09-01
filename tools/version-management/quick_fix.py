#!/usr/bin/env python3
"""
简单的SAGE项目硬编码修复工具
专注于将硬编码版本号替换为动态加载
"""

import re
from pathlib import Path


def find_sage_root():
    """查找SAGE项目根目录"""
    current_path = Path(__file__).resolve()
    for parent in [current_path.parent.parent.parent] + list(current_path.parents):
        if (parent / "_version.py").exists():
            return parent
    raise FileNotFoundError("找不到SAGE项目根目录")


def get_core_python_files():
    """获取核心Python文件列表"""
    root_dir = find_sage_root()
    files = []
    
    # 查找packages目录下的__init__.py文件
    for init_file in root_dir.glob("packages/*/src/**/__init__.py"):
        if '/build/' not in str(init_file):
            files.append(init_file)
    
    return files


def fix_version_hardcode(file_path):
    """修复单个文件的版本硬编码"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 如果包含硬编码版本号
        if '__version__ = "0.1.4"' in content:
            # 计算到根目录的层级
            root_dir = find_sage_root()
            relative_path = file_path.relative_to(root_dir)
            levels_up = len(relative_path.parts) - 1  # 减去文件名
            
            # 动态版本加载代码
            version_loader_code = f'''
# 动态版本加载 - 避免硬编码
def _get_version():
    """从根目录的_version.py动态获取版本"""
    from pathlib import Path
    
    current_file = Path(__file__).resolve()
    root_dir = current_file{".parent" * levels_up}
    version_file = root_dir / "_version.py"
    
    if version_file.exists():
        version_globals = {{}}
        with open(version_file, 'r', encoding='utf-8') as f:
            exec(f.read(), version_globals)
        return version_globals.get('__version__', '0.1.4')
    return '0.1.4'

__version__ = _get_version()
'''
            
            # 替换硬编码版本
            content = content.replace('__version__ = "0.1.4"', '__version__ = _get_version()')
            
            # 在文件开头添加动态加载函数
            if '_get_version()' in content and 'def _get_version():' not in content:
                # 找到合适的插入位置（在模块文档字符串之后）
                lines = content.split('\n')
                insert_pos = 0
                
                # 跳过开头的注释和文档字符串
                in_docstring = False
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped.startswith('"""') or stripped.startswith("'''"):
                        if in_docstring:
                            in_docstring = False
                            insert_pos = i + 1
                            break
                        else:
                            in_docstring = True
                    elif not in_docstring and stripped and not stripped.startswith('#'):
                        insert_pos = i
                        break
                
                lines.insert(insert_pos, version_loader_code)
                content = '\n'.join(lines)
        
        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
    
    except Exception as e:
        print(f"⚠️ 处理文件 {file_path} 时出错: {e}")
        return False
    
    return False


def check_hardcode():
    """检查硬编码问题"""
    print("🔍 检查核心文件中的硬编码...")
    
    files = get_core_python_files()
    issues = []
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if '__version__ = "0.1.4"' in content:
                issues.append(file_path)
        except Exception:
            continue
    
    if issues:
        print(f"⚠️ 发现 {len(issues)} 个文件存在硬编码版本号:")
        for file_path in issues:
            root_dir = find_sage_root()
            print(f"  📁 {file_path.relative_to(root_dir)}")
    else:
        print("✅ 未发现硬编码版本号问题")
    
    return issues


def fix_hardcode():
    """修复硬编码问题"""
    print("🔧 修复硬编码版本号...")
    
    files = get_core_python_files()
    fixed_count = 0
    root_dir = find_sage_root()
    
    for file_path in files:
        if fix_version_hardcode(file_path):
            print(f"  ✅ 修复 {file_path.relative_to(root_dir)}")
            fixed_count += 1
    
    print(f"🎉 修复完成，共修复 {fixed_count} 个文件")


def main():
    import sys
    
    if len(sys.argv) != 2:
        print("用法: python quick_fix.py [check|fix]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "check":
        check_hardcode()
    elif command == "fix":
        fix_hardcode()
    else:
        print("错误: 命令必须是 'check' 或 'fix'")
        sys.exit(1)


if __name__ == "__main__":
    main()
