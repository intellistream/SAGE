#!/usr/bin/env python3
"""
终极简单修复工具：清理所有包的__init__.py文件
确保动态版本加载正确工作
"""

from pathlib import Path


def find_sage_root():
    """查找SAGE项目根目录"""
    current_path = Path(__file__).resolve()
    for parent in [current_path.parent.parent.parent] + list(current_path.parents):
        if (parent / "_version.py").exists():
            return parent
    raise FileNotFoundError("找不到SAGE项目根目录")


def clean_init_file(init_file_path):
    """清理__init__.py文件，提供简洁的动态版本加载"""
    try:
        # 计算到根目录的相对层级
        root_dir = find_sage_root()
        relative_path = init_file_path.relative_to(root_dir)
        
        # 计算需要向上几层才能到达根目录
        levels_up = len(relative_path.parts) - 1  # 减去文件名
        parent_path = ".parent" * levels_up
        
        # 创建新的内容
        new_content = f'''"""
SAGE - Streaming-Augmented Generative Execution
"""

# 动态版本加载
def _load_version():
    """从项目根目录动态加载版本信息"""
    from pathlib import Path
    
    # 获取项目根目录
    current_file = Path(__file__).resolve()
    root_dir = current_file{parent_path}
    version_file = root_dir / "_version.py"
    
    # 加载版本信息
    if version_file.exists():
        version_globals = {{}}
        with open(version_file, 'r', encoding='utf-8') as f:
            exec(f.read(), version_globals)
        return {{
            'version': version_globals.get('__version__', '0.1.4'),
            'author': version_globals.get('__author__', 'SAGE Team'),
            'email': version_globals.get('__email__', 'shuhao_zhang@hust.edu.cn')
        }}
    
    # 默认值
    return {{
        'version': '0.1.4',
        'author': 'SAGE Team', 
        'email': 'shuhao_zhang@hust.edu.cn'
    }}

# 加载信息
_info = _load_version()
__version__ = _info['version']
__author__ = _info['author']
__email__ = _info['email']
'''
        
        # 写入新内容
        with open(init_file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
    
    except Exception as e:
        print(f"⚠️ 处理文件 {init_file_path} 时出错: {e}")
        return False


def main():
    """主函数"""
    root_dir = find_sage_root()
    
    # 查找所有包的__init__.py文件
    init_files = list(root_dir.glob("packages/*/src/**/__init__.py"))
    
    print(f"🔧 开始清理 {len(init_files)} 个__init__.py文件...")
    
    success_count = 0
    for init_file in init_files:
        if clean_init_file(init_file):
            print(f"  ✅ 清理 {init_file.relative_to(root_dir)}")
            success_count += 1
    
    print(f"🎉 完成！成功清理 {success_count} 个文件")
    
    # 测试加载
    print("\n🧪 测试动态版本加载...")
    try:
        import sys
        sys.path.insert(0, str(root_dir / "packages" / "sage" / "src"))
        import sage
        print(f"✅ SAGE版本: {sage.__version__}")
        print(f"✅ 作者: {sage.__author__}")
        print(f"✅ 邮箱: {sage.__email__}")
    except Exception as e:
        print(f"⚠️ 测试失败: {e}")


if __name__ == "__main__":
    main()
