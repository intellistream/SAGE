#!/usr/bin/env python3
"""
Commercial Code Migration Script
将packages/commercial中的代码迁移到对应的开源包中作为enterprise扩展
"""

import os
import shutil
import json
from pathlib import Path


def migrate_commercial_code():
    """迁移commercial代码到对应的开源包中"""
    project_root = Path(__file__).parent.parent
    commercial_dir = project_root / "packages" / "commercial"
    packages_dir = project_root / "packages"
    
    print("🚀 开始迁移commercial代码...")
    
    # 迁移映射
    migrations = {
        "sage-kernel": {
            "source": commercial_dir / "sage-kernel" / "src" / "sage" / "kernel",
            "target": packages_dir / "sage-kernel" / "src" / "sage" / "kernel" / "enterprise",
            "description": "高性能kernel组件"
        },
        "sage-middleware": {
            "source": commercial_dir / "sage-middleware" / "src" / "sage" / "middleware",
            "target": packages_dir / "sage-middleware" / "src" / "sage" / "middleware" / "enterprise", 
            "description": "企业级中间件"
        },
        "sage-userspace": {
            "source": commercial_dir / "sage-userspace" / "src" / "sage" / "userspace",
            "target": packages_dir / "sage-userspace" / "src" / "sage" / "userspace" / "enterprise",
            "description": "企业级用户空间组件"
        }
    }
    
    for package_name, config in migrations.items():
        source_dir = config["source"]
        target_dir = config["target"]
        
        print(f"\n📦 迁移 {package_name}...")
        print(f"   从: {source_dir}")
        print(f"   到: {target_dir}")
        
        if not source_dir.exists():
            print(f"   ⚠️  源目录不存在，跳过: {source_dir}")
            continue
        
        # 创建目标目录
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # 迁移代码
        try:
            # 复制所有文件
            for item in source_dir.iterdir():
                if item.name in ['.git', '__pycache__', '.pytest_cache']:
                    continue
                    
                dest_path = target_dir / item.name
                
                if item.is_dir():
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(item, dest_path)
                    print(f"   📁 复制目录: {item.name}")
                else:
                    shutil.copy2(item, dest_path)
                    print(f"   📄 复制文件: {item.name}")
            
            # 创建license检查的__init__.py
            create_enterprise_init(target_dir, package_name)
            
            print(f"   ✅ {package_name} 迁移完成")
            
        except Exception as e:
            print(f"   ❌ 迁移失败: {e}")
    
    print("\n🎉 Commercial代码迁移完成！")


def create_enterprise_init(enterprise_dir, package_name):
    """为enterprise目录创建带license检查的__init__.py"""
    init_content = f'''"""
SAGE {package_name} Enterprise Edition
企业版功能需要有效的商业许可证
"""

import os
import sys
from pathlib import Path

# 添加license工具到路径
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
_LICENSE_TOOLS = _PROJECT_ROOT / "tools" / "license"

if _LICENSE_TOOLS.exists():
    sys.path.insert(0, str(_LICENSE_TOOLS))
    sys.path.insert(0, str(_LICENSE_TOOLS / "shared"))


def _check_enterprise_license():
    """检查企业版license"""
    try:
        from shared.validation import LicenseValidator
        
        validator = LicenseValidator()
        if not validator.has_valid_license():
            return False
            
        features = validator.get_license_features()
        # 检查是否有企业版功能
        required_features = ["enterprise", "high-performance", "enterprise-db", "advanced-analytics"]
        return any(feature in features for feature in required_features)
        
    except ImportError:
        # License工具不可用，检查环境变量
        return os.getenv("SAGE_ENTERPRISE_ENABLED", "").lower() in ["true", "1", "yes"]
    except Exception:
        return False


# 企业版功能可用性检查
_ENTERPRISE_AVAILABLE = _check_enterprise_license()

if not _ENTERPRISE_AVAILABLE:
    import warnings
    warnings.warn(
        f"SAGE {package_name} Enterprise features require a valid commercial license. "
        "Enterprise functionality will be disabled. "
        "Please contact your SAGE vendor for licensing information.",
        UserWarning,
        stacklevel=2
    )


def require_enterprise_license(func):
    """装饰器：要求企业版license"""
    def wrapper(*args, **kwargs):
        if not _ENTERPRISE_AVAILABLE:
            raise RuntimeError(
                f"SAGE {package_name} Enterprise feature requires a valid commercial license. "
                f"This functionality is not available with your current license."
            )
        return func(*args, **kwargs)
    return wrapper


# 根据license状态导入功能
if _ENTERPRISE_AVAILABLE:
    # 导入所有企业版功能
    try:
        # 这里会根据实际的企业版模块来调整
        pass
    except ImportError as e:
        print(f"Warning: Failed to import some enterprise features: {{e}}")
else:
    # 企业版功能不可用时的占位符
    pass


__all__ = [
    "_ENTERPRISE_AVAILABLE",
    "require_enterprise_license"
]
'''
    
    init_file = enterprise_dir / "__init__.py"
    with open(init_file, 'w', encoding='utf-8') as f:
        f.write(init_content)
    
    print(f"   📄 创建enterprise __init__.py")


if __name__ == "__main__":
    migrate_commercial_code()
