#!/usr/bin/env python3
"""
更新所有引用，从 sage.common 到 sage.common 和 sage.tools
"""

import os
import re
import glob
from pathlib import Path

def update_imports():
    """更新所有Python文件中的import语句"""
    
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
                print(f"✅ Updated: {file_path}")
                
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
    
    print(f"\n📊 Updated {len(updated_files)} files")
    return updated_files

def update_pyproject_dependencies():
    """更新pyproject.toml中的依赖配置"""
    
    pyproject_files = glob.glob('/home/shuhao/SAGE/packages/*/pyproject.toml')
    
    for file_path in pyproject_files:
        package_name = Path(file_path).parent.name
        print(f"\n🔧 Processing {package_name}/pyproject.toml")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 根据包的不同需求更新依赖
            if package_name == 'sage-tools':
                # sage-tools已经正确配置了
                continue
                
            elif package_name == 'sage-common':
                # sage-common已经正确配置了
                continue
                
            elif package_name in ['sage-kernel', 'sage-libs', 'sage-middleware']:
                # 这些包只需要核心功能，保持isage-common依赖
                # 但需要同时添加isage-tools依赖（因为部分代码可能使用CLI）
                if 'isage-tools' not in content:
                    # 在isage-common后面添加isage-tools
                    content = re.sub(
                        r'("isage-common>=0\.1\.0",)',
                        r'\1\n    "isage-tools>=0.1.0",',
                        content
                    )
                    
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
                print(f"✅ Updated dependencies in {package_name}")
            else:
                print(f"➖ No changes needed for {package_name}")
                
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")

if __name__ == "__main__":
    print("🚀 开始更新SAGE项目中的所有引用...")
    
    print("\n📁 Step 1: 更新Python文件中的import语句")
    updated_files = update_imports()
    
    print("\n📦 Step 2: 更新pyproject.toml中的依赖配置")
    update_pyproject_dependencies()
    
    print("\n✨ 更新完成！")
    print("\n💡 接下来需要:")
    print("   1. 验证所有包能正确安装")
    print("   2. 运行测试确保功能正常")
    print("   3. 更新文档说明新的包结构")
