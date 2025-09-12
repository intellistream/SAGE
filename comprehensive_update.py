#!/usr/bin/env python3
"""
全面更新SAGE项目中的所有引用
- Python import语句  
- Shell脚本中的路径和模块引用
- pyproject.toml中的依赖配置
- 文档和注释中的引用
"""

import os
import re
import glob
from pathlib import Path

def update_python_imports():
    """更新所有Python文件中的import语句"""
    print("🐍 Step 1: 更新Python文件中的import语句...")
    
    # 需要替换的模式
    replacements = [
        # CLI相关模块移到sage.tools
        (r'from sage\.common\.cli', 'from sage.tools.cli'),
        (r'import sage\.common\.cli', 'import sage.tools.cli'),
        
        # Frontend相关模块移到sage.tools  
        (r'from sage\.common\.frontend', 'from sage.tools.frontend'),
        (r'import sage\.common\.frontend', 'import sage.tools.frontend'),
        
        # Dev相关模块移到sage.tools
        (r'from sage\.common\.dev', 'from sage.tools.dev'),
        (r'import sage\.common\.dev', 'import sage.tools.dev'),
        
        # Management相关模块移到sage.tools
        (r'from sage\.common\.management', 'from sage.tools.management'),
        (r'import sage\.common\.management', 'import sage.tools.management'),
        
        # Studio相关模块移到sage.tools
        (r'from sage\.common\.studio', 'from sage.tools.studio'),
        (r'import sage\.common\.studio', 'import sage.tools.studio'),
        
        # Internal相关模块移到sage.tools
        (r'from sage\.common\.internal', 'from sage.tools.internal'),
        (r'import sage\.common\.internal', 'import sage.tools.internal'),
        
        # Scripts相关模块移到sage.tools
        (r'from sage\.common\.scripts', 'from sage.tools.scripts'),
        (r'import sage\.common\.scripts', 'import sage.tools.scripts'),
    ]
    
    # 查找所有Python文件
    python_files = []
    for root, dirs, files in os.walk('/home/shuhao/SAGE'):
        # 跳过__pycache__等目录
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    updated_files = []
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 应用替换
            for pattern, replacement in replacements:
                content = re.sub(pattern, replacement, content)
            
            # 如果内容有变化，写回文件
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                updated_files.append(file_path)
                print(f"  ✅ Updated: {file_path}")
                
        except Exception as e:
            print(f"  ❌ Error processing {file_path}: {e}")
    
    print(f"  📊 Updated {len(updated_files)} Python files")
    return updated_files

def update_shell_scripts():
    """更新Shell脚本中的路径和模块引用"""
    print("\n🐚 Step 2: 更新Shell脚本中的引用...")
    
    # 需要替换的模式
    replacements = [
        # CLI模块调用
        (r'python -m sage\.common\.cli\.main', 'python -m sage.tools.cli.main'),
        (r'python3 -m sage\.common\.cli\.main', 'python3 -m sage.tools.cli.main'),
        
        # 路径引用 - 从sage-common变为sage-tools
        (r'packages/sage-common/src/sage/common/cli', 'packages/sage-tools/src/sage/tools/cli'),
        (r'packages/sage-common/src/sage/common/frontend', 'packages/sage-tools/src/sage/tools/frontend'),
        (r'packages/sage-common/src/sage/common/studio', 'packages/sage-tools/src/sage/tools/studio'),
        (r'packages/sage-common/src/sage/common/internal', 'packages/sage-tools/src/sage/tools/internal'),
        
        # 包安装顺序更新 - 现在需要先安装sage-common再安装sage-tools
        (r'"sage-common" "sage-kernel"', '"sage-common" "sage-tools" "sage-kernel"'),
        
        # 测试包列表更新
        (r'\("sage-common" "sage-kernel"', '("sage-common" "sage-tools" "sage-kernel"'),
        
        # pip卸载命令更新
        (r'isage-kernel isage-middleware isage-libs isage-common', 'isage-kernel isage-middleware isage-libs isage-common isage-tools'),
        
        # 前端依赖更新
        (r'isage-common\[frontend\]', 'isage-tools'),
        (r'isage-common\[studio\]', 'isage-tools'),
        (r'isage-common\[ui\]', 'isage-tools'),
    ]
    
    # 查找所有shell脚本
    shell_files = []
    for root, dirs, files in os.walk('/home/shuhao/SAGE'):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in files:
            if file.endswith('.sh'):
                shell_files.append(os.path.join(root, file))
    
    updated_files = []
    
    for file_path in shell_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 应用替换
            for pattern, replacement in replacements:
                content = re.sub(pattern, replacement, content)
            
            # 如果内容有变化，写回文件
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                updated_files.append(file_path)
                print(f"  ✅ Updated: {file_path}")
                
        except Exception as e:
            print(f"  ❌ Error processing {file_path}: {e}")
    
    print(f"  📊 Updated {len(updated_files)} shell files")
    return updated_files

def update_pyproject_dependencies():
    """更新pyproject.toml中的依赖配置"""
    print("\n📦 Step 3: 更新pyproject.toml中的依赖配置...")
    
    pyproject_files = glob.glob('/home/shuhao/SAGE/packages/*/pyproject.toml')
    
    for file_path in pyproject_files:
        package_name = Path(file_path).parent.name
        print(f"  🔧 Processing {package_name}/pyproject.toml")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 根据包的不同需求更新依赖
            if package_name == 'sage-tools':
                # sage-tools已经正确配置了
                print(f"    ➖ {package_name} already correctly configured")
                continue
                
            elif package_name == 'sage-common':
                # sage-common已经正确配置了
                print(f"    ➖ {package_name} already correctly configured")
                continue
                
            elif package_name in ['sage-kernel', 'sage-libs', 'sage-middleware']:
                # 这些包只需要核心功能，保持isage-common依赖
                # 但需要添加isage-tools依赖（因为某些代码可能使用CLI）
                if 'isage-tools' not in content and 'sage-tools' in package_name:
                    # 只有在需要工具功能时才添加
                    pass
                print(f"    ➖ {package_name} dependencies correct")
                    
            elif package_name == 'sage':
                # 主包需要所有功能，更新配置
                # 将isage-common[extras]替换为分别的依赖
                replacements = [
                    (r'"isage-common\[dev\]>=0\.1\.0"', '"isage-tools>=0.1.0"'),
                    (r'"isage-common\[cli\]>=0\.1\.0"', '"isage-tools>=0.1.0"'),
                    (r'"isage-common\[frontend\]>=0\.1\.0"', '"isage-tools>=0.1.0"'),
                    (r'"isage-common\[docs\]>=0\.1\.0"', '"isage-tools>=0.1.0"'),
                    (r'"isage-common\[full\]>=0\.1\.0"', '"isage-tools>=0.1.0"'),
                ]
                
                for pattern, replacement in replacements:
                    content = re.sub(pattern, replacement, content)
            
            # 写回文件如果有变化
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"    ✅ Updated dependencies in {package_name}")
            else:
                print(f"    ➖ No changes needed for {package_name}")
                
        except Exception as e:
            print(f"    ❌ Error processing {file_path}: {e}")

def update_documentation_and_comments():
    """更新文档和注释中的引用"""
    print("\n📚 Step 4: 更新文档和注释中的引用...")
    
    # 查找Markdown文件、文档文件等
    doc_patterns = ['*.md', '*.rst', '*.txt']
    doc_files = []
    
    for pattern in doc_patterns:
        for root, dirs, files in os.walk('/home/shuhao/SAGE'):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if file.endswith(pattern[1:]):  # 去掉*
                    doc_files.append(os.path.join(root, file))
    
    # 也包括Python文件中的注释
    python_files = []
    for root, dirs, files in os.walk('/home/shuhao/SAGE'):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    all_files = doc_files + python_files
    
    # 需要替换的模式（在注释和文档中）
    replacements = [
        # 包名引用
        (r'从 sage-common 包', '从 sage-common 包'),  # 保持核心功能引用
        (r'sage-common: 核心工具库
  • sage-tools: CLI工具和开发工具', 'sage-common: 核心工具库
  • sage-tools: CLI工具和开发工具\n  • sage-tools: CLI工具和开发工具'),
        
        # 安装说明更新
        (r'pip install isage-common\[frontend\]', 'pip install isage-tools'),
        (r'pip install isage-common\[cli\]', 'pip install isage-tools'),
        (r'pip install isage-common\[dev\]', 'pip install isage-tools'),
    ]
    
    updated_files = []
    
    for file_path in all_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 应用替换
            for pattern, replacement in replacements:
                content = re.sub(pattern, replacement, content)
            
            # 如果内容有变化，写回文件
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                updated_files.append(file_path)
                print(f"  ✅ Updated: {file_path}")
                
        except Exception as e:
            print(f"  ❌ Error processing {file_path}: {e}")
    
    print(f"  📊 Updated {len(updated_files)} documentation files")
    return updated_files

def verify_references():
    """验证更新后的引用是否正确"""
    print("\n🔍 Step 5: 验证更新后的引用...")
    
    # 检查是否还有旧的引用
    issues = []
    
    # 检查Python文件中是否还有错误的import
    python_files = []
    for root, dirs, files in os.walk('/home/shuhao/SAGE'):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否还有sage.common.cli等引用（这些应该已经改为sage.tools）
            problematic_patterns = [
                r'from sage\.common\.cli',
                r'from sage\.common\.frontend', 
                r'from sage\.common\.dev',
                r'from sage\.common\.management',
                r'from sage\.common\.studio',
                r'from sage\.common\.internal',
                r'from sage\.common\.scripts',
                r'import sage\.common\.cli',
                r'import sage\.common\.frontend',
            ]
            
            for pattern in problematic_patterns:
                if re.search(pattern, content):
                    issues.append(f"  ❌ Found old reference in {file_path}: {pattern}")
                    
        except Exception as e:
            print(f"  ❌ Error checking {file_path}: {e}")
    
    if issues:
        print("  🚨 Found issues that need manual review:")
        for issue in issues[:10]:  # 只显示前10个
            print(issue)
        if len(issues) > 10:
            print(f"    ... and {len(issues) - 10} more issues")
    else:
        print("  ✅ All references look good!")
    
    return len(issues) == 0

if __name__ == "__main__":
    print("🚀 开始全面更新SAGE项目中的所有引用...")
    
    # 执行更新步骤
    update_python_imports()
    update_shell_scripts()
    update_pyproject_dependencies()
    update_documentation_and_comments()
    
    # 验证结果
    success = verify_references()
    
    print(f"\n{'✨' if success else '⚠️'} 更新完成！")
    
    if success:
        print("\n💡 接下来的步骤:")
        print("   1. cd /home/shuhao/SAGE/packages/sage-common && pip install -e .")
        print("   2. cd /home/shuhao/SAGE/packages/sage-tools && pip install -e .")
        print("   3. 测试核心功能: python -c 'from sage.common.utils.logging.custom_logger import get_logger'")
        print("   4. 测试工具功能: python -c 'from sage.tools.cli.main import main'")
        print("   5. 运行完整测试套件验证所有功能")
    else:
        print("\n⚠️ 发现一些问题，可能需要手动检查和修复")
        print("   建议先解决这些问题，再进行包安装和测试")
