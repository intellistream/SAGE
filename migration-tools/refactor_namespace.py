#!/usr/bin/env python3
"""
SAGE命名空间重构工具
==================

将现有的monorepo代码重构为namespace packages结构。
自动更新导入语句、创建namespace package结构。
"""

import os
import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import argparse
import shutil

class NamespaceRefactor:
    """命名空间重构器"""
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.changes_made = []
        
        # 导入路径映射规则
        self.import_mappings = {
            # 现有导入 -> 新的namespace导入
            r'from sage\.core\.(.+) import': r'from sage.core.\1 import',
            r'from sage\.runtime\.(.+) import': r'from sage.runtime.\1 import',
            r'from sage\.lib\.(.+) import': r'from sage.lib.\1 import',
            r'from sage\.service\.(.+) import': r'from sage.service.\1 import',
            r'from sage\.utils\.(.+) import': r'from sage.utils.\1 import',
            r'from sage\.jobmanager\.(.+) import': r'from sage.jobmanager.\1 import',
            r'from sage\.cli\.(.+) import': r'from sage.cli.\1 import',
            r'from sage\.plugins\.(.+) import': r'from sage.plugins.\1 import',
            
            # 扩展模块映射
            r'from sage_ext\.(.+) import': r'from sage.extensions.\1 import',
            r'import sage_ext\.(.+)': r'import sage.extensions.\1',
            
            # Dashboard模块映射
            r'from frontend\.(.+) import': r'from sage.dashboard.\1 import',
            r'import frontend\.(.+)': r'import sage.dashboard.\1',
        }
    
    def scan_python_files(self, directory: Path = None) -> List[Path]:
        """扫描Python文件"""
        if directory is None:
            directory = self.project_path
            
        python_files = []
        for file_path in directory.rglob("*.py"):
            # 排除一些目录
            if any(part.startswith('.') for part in file_path.parts):
                continue
            if '__pycache__' in file_path.parts:
                continue
            if 'build' in file_path.parts:
                continue
            python_files.append(file_path)
        return python_files
    
    def create_namespace_structure(self, target_project: str):
        """创建namespace package结构"""
        if target_project == 'sage-core':
            self._create_sage_core_structure()
        elif target_project == 'sage-extensions':
            self._create_sage_extensions_structure()
        elif target_project == 'sage-dashboard':
            self._create_sage_dashboard_structure()
    
    def _create_sage_core_structure(self):
        """创建sage-core的namespace结构"""
        print("🏗️  创建sage-core namespace结构...")
        
        src_dir = self.project_path / 'src'
        sage_ns_dir = src_dir / 'sage'
        
        # 创建src/sage目录结构
        src_dir.mkdir(exist_ok=True)
        sage_ns_dir.mkdir(exist_ok=True)
        
        # 移动现有的sage目录内容
        original_sage_dir = self.project_path / 'sage'
        if original_sage_dir.exists():
            print(f"📦 移动 {original_sage_dir} -> {sage_ns_dir}")
            
            # 复制内容而不是移动整个目录
            for item in original_sage_dir.iterdir():
                if item.name in ['.git', '__pycache__', '.pytest_cache']:
                    continue
                    
                target_item = sage_ns_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, target_item, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, target_item)
            
            # 备份原目录
            backup_dir = self.project_path / 'sage.backup'
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            shutil.move(original_sage_dir, backup_dir)
            print(f"📁 原sage目录已备份到: {backup_dir}")
        
        # 创建新的__init__.py文件
        self._create_sage_init_file(sage_ns_dir)
        
        # 创建智能组件发现机制
        self._create_component_discovery(sage_ns_dir)
        
        print("✅ sage-core namespace结构创建完成")
    
    def _create_sage_extensions_structure(self):
        """创建sage-extensions的namespace结构"""
        print("🏗️  创建sage-extensions namespace结构...")
        
        src_dir = self.project_path / 'src'
        sage_ns_dir = src_dir / 'sage'
        extensions_dir = sage_ns_dir / 'extensions'
        
        # 创建目录结构
        src_dir.mkdir(exist_ok=True)
        sage_ns_dir.mkdir(exist_ok=True)
        extensions_dir.mkdir(exist_ok=True)
        
        # 移动sage_ext内容
        original_ext_dir = self.project_path / 'sage_ext'
        if original_ext_dir.exists():
            print(f"📦 移动 {original_ext_dir} -> {extensions_dir}")
            for item in original_ext_dir.iterdir():
                if item.name in ['.git', '__pycache__']:
                    continue
                target_item = extensions_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, target_item, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, target_item)
            
            # 备份原目录
            backup_dir = self.project_path / 'sage_ext.backup'
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            shutil.move(original_ext_dir, backup_dir)
        
        # 创建扩展模块的__init__.py
        self._create_extensions_init_file(extensions_dir)
        
        print("✅ sage-extensions namespace结构创建完成")
    
    def _create_sage_dashboard_structure(self):
        """创建sage-dashboard的namespace结构"""
        print("🏗️  创建sage-dashboard namespace结构...")
        
        # 后端结构
        backend_src_dir = self.project_path / 'backend' / 'src'
        sage_ns_dir = backend_src_dir / 'sage'
        dashboard_dir = sage_ns_dir / 'dashboard'
        
        # 创建目录结构
        backend_src_dir.mkdir(parents=True, exist_ok=True)
        sage_ns_dir.mkdir(exist_ok=True)
        dashboard_dir.mkdir(exist_ok=True)
        
        # 移动frontend内容
        original_frontend_dir = self.project_path / 'frontend'
        if original_frontend_dir.exists():
            # 前端代码保持在frontend目录
            frontend_target = self.project_path / 'frontend'
            if original_frontend_dir != frontend_target:
                shutil.copytree(original_frontend_dir, frontend_target, dirs_exist_ok=True)
            
            # 后端代码移动到namespace结构
            sage_server_dir = original_frontend_dir / 'sage_server'
            if sage_server_dir.exists():
                server_target = dashboard_dir / 'server'
                shutil.copytree(sage_server_dir, server_target, dirs_exist_ok=True)
        
        # 创建dashboard模块的__init__.py
        self._create_dashboard_init_file(dashboard_dir)
        
        print("✅ sage-dashboard namespace结构创建完成")
    
    def _create_sage_init_file(self, sage_dir: Path):
        """创建sage核心的__init__.py文件"""
        init_content = '''"""
SAGE Framework - 核心Python实现
"""
import sys
import importlib
from typing import Optional, List

__version__ = "1.0.0"
__all__ = ["__version__", "get_available_modules", "check_extensions"]

def get_available_modules() -> List[str]:
    """动态发现所有已安装的SAGE模块"""
    available = ['core']  # 核心总是可用
    
    # 检查扩展
    try:
        import sage.extensions
        available.append('extensions')
    except ImportError:
        pass
    
    # 检查dashboard
    try:
        import sage.dashboard
        available.append('dashboard')
    except ImportError:
        pass
    
    return available

def check_extensions() -> dict:
    """检查扩展模块的可用性和版本信息"""
    extensions_info = {}
    
    try:
        import sage.extensions
        extensions_info['extensions'] = {
            'available': True,
            'version': getattr(sage.extensions, '__version__', 'unknown'),
            'modules': []
        }
        
        # 检查具体的扩展模块
        for ext_name in ['sage_queue', 'sage_db']:
            try:
                importlib.import_module(f'sage.extensions.{ext_name}')
                extensions_info['extensions']['modules'].append(ext_name)
            except ImportError:
                pass
                
    except ImportError:
        extensions_info['extensions'] = {'available': False}
    
    try:
        import sage.dashboard
        extensions_info['dashboard'] = {
            'available': True,
            'version': getattr(sage.dashboard, '__version__', 'unknown')
        }
    except ImportError:
        extensions_info['dashboard'] = {'available': False}
    
    return extensions_info

# 启动时的信息输出 (可通过环境变量控制)
import os
if not os.getenv('SAGE_SILENT_IMPORT'):
    available = get_available_modules()
    if len(available) > 1:
        print(f"🧠 SAGE Framework v{__version__} - Available modules: {', '.join(available)}")
    else:
        print(f"🧠 SAGE Framework v{__version__} - Core only (install sage-extensions, sage-dashboard for more features)")
'''
        
        init_file = sage_dir / '__init__.py'
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write(init_content)
        print(f"📄 创建: {init_file}")
    
    def _create_extensions_init_file(self, extensions_dir: Path):
        """创建扩展模块的__init__.py文件"""
        init_content = '''"""
SAGE Extensions - 高性能C++扩展
"""
import sys
import os
from typing import Dict, Any, Optional

__version__ = "1.0.0"

def get_available_extensions() -> Dict[str, Any]:
    """获取所有可用的C++扩展"""
    extensions = {}
    
    # 检查sage_queue
    try:
        from .sage_queue import SageQueueDescriptor
        extensions['sage_queue'] = {
            'class': SageQueueDescriptor,
            'description': 'High-performance memory-mapped queue',
            'version': getattr(SageQueueDescriptor, '__version__', 'unknown')
        }
    except ImportError:
        pass
    
    # 检查sage_db
    try:
        from .sage_db import SageDB
        extensions['sage_db'] = {
            'class': SageDB,
            'description': 'High-performance vector database',
            'version': getattr(SageDB, '__version__', 'unknown')
        }
    except ImportError:
        pass
    
    return extensions

def check_build_info() -> Dict[str, Any]:
    """检查C++扩展的构建信息"""
    build_info = {
        'compiler': os.getenv('CXX', 'unknown'),
        'build_type': os.getenv('CMAKE_BUILD_TYPE', 'unknown'),
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}",
        'available_extensions': list(get_available_extensions().keys())
    }
    return build_info
'''
        
        init_file = extensions_dir / '__init__.py'
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write(init_content)
        print(f"📄 创建: {init_file}")
    
    def _create_dashboard_init_file(self, dashboard_dir: Path):
        """创建dashboard模块的__init__.py文件"""
        init_content = '''"""
SAGE Dashboard - Web界面和API客户端
"""
__version__ = "1.0.0"

from .client import DashboardClient

try:
    from .server.main import create_app
    __all__ = ["DashboardClient", "create_app"]
except ImportError:
    # 服务器组件可能不可用
    __all__ = ["DashboardClient"]
'''
        
        init_file = dashboard_dir / '__init__.py'
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write(init_content)
        print(f"📄 创建: {init_file}")
        
        # 创建客户端模块
        client_content = '''"""
Dashboard客户端 - 用于从Python代码中连接Dashboard
"""
import httpx
from typing import Optional, Dict, Any

class DashboardClient:
    """SAGE Dashboard API客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8080", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {}
        )
    
    def check_health(self) -> bool:
        """检查Dashboard服务健康状态"""
        try:
            response = self.client.get("/health")
            return response.status_code == 200
        except:
            return False
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """获取作业状态"""
        response = self.client.get(f"/api/jobs/{job_id}")
        response.raise_for_status()
        return response.json()
    
    def submit_pipeline(self, pipeline_config: Dict[str, Any]) -> str:
        """提交流水线"""
        response = self.client.post("/api/pipeline/submit", json=pipeline_config)
        response.raise_for_status()
        return response.json()["job_id"]
'''
        
        client_file = dashboard_dir / 'client.py'
        with open(client_file, 'w', encoding='utf-8') as f:
            f.write(client_content)
        print(f"📄 创建: {client_file}")
    
    def _create_component_discovery(self, sage_dir: Path):
        """创建智能组件发现机制"""
        # 更新runtime/queue模块以支持自动fallback
        queue_dir = sage_dir / 'runtime' / 'queue'
        if queue_dir.exists():
            queue_init = queue_dir / '__init__.py'
            
            # 读取现有内容
            existing_content = ""
            if queue_init.exists():
                with open(queue_init, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
            
            # 添加自动fallback机制
            fallback_content = '''
# 自动fallback机制
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

def create_queue(queue_type: str = "auto", **kwargs):
    """
    创建队列的统一工厂函数
    
    自动检测可用的实现，优雅降级：
    sage_queue (C++扩展) -> python_queue (Python实现)
    """
    if queue_type == "sage_queue" or queue_type == "auto":
        # 尝试使用C++扩展
        try:
            from sage.extensions.sage_queue import SageQueueDescriptor
            logger.info("Using sage_queue (C++ extension)")
            return SageQueueDescriptor(**kwargs)
        except ImportError as e:
            if queue_type == "sage_queue":
                # 用户明确要求sage_queue但不可用
                raise ImportError(
                    f"sage_queue requested but sage-extensions not installed. "
                    f"Install with: pip install sage-extensions"
                ) from e
            else:
                logger.info("sage-extensions not available, falling back to Python implementation")
    
    # Fallback到Python实现
    from .python_queue_descriptor import PythonQueueDescriptor
    logger.info("Using python_queue (pure Python)")
    return PythonQueueDescriptor(**kwargs)

def get_available_queue_types() -> List[str]:
    """获取当前可用的队列类型"""
    available = ["python_queue"]
    
    try:
        import sage.extensions.sage_queue
        available.append("sage_queue")
    except ImportError:
        pass
    
    return available

'''
            
            # 如果文件不存在或内容中没有create_queue函数，则添加
            if not queue_init.exists() or 'def create_queue' not in existing_content:
                with open(queue_init, 'a', encoding='utf-8') as f:
                    f.write(fallback_content)
                print(f"📄 更新: {queue_init} (添加自动fallback机制)")
    
    def update_import_statements(self, file_path: Path) -> bool:
        """更新文件中的导入语句"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            updated_content = original_content
            changes_in_file = 0
            
            for old_pattern, new_pattern in self.import_mappings.items():
                matches = re.findall(old_pattern, updated_content)
                if matches:
                    updated_content = re.sub(old_pattern, new_pattern, updated_content)
                    changes_in_file += len(matches)
            
            if changes_in_file > 0:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                
                self.changes_made.append({
                    'file': str(file_path.relative_to(self.project_path)),
                    'changes': changes_in_file
                })
                return True
            
            return False
            
        except Exception as e:
            print(f"⚠️  处理文件 {file_path} 时出错: {e}")
            return False
    
    def refactor_imports(self, directory: Path = None):
        """重构导入语句"""
        if directory is None:
            directory = self.project_path
            
        print(f"🔄 重构导入语句: {directory}")
        
        python_files = self.scan_python_files( directory)
        updated_files = 0
        
        for file_path in python_files:
            if self.update_import_statements(file_path):
                updated_files += 1
        
        print(f"✅ 更新了 {updated_files} 个文件中的导入语句")
        
        if self.changes_made:
            print("\n📋 详细变更:")
            for change in self.changes_made[-10:]:  # 只显示最后10个
                print(f"  {change['file']}: {change['changes']} 处变更")
            if len(self.changes_made) > 10:
                print(f"  ... 还有 {len(self.changes_made) - 10} 个文件")
    
    def create_migration_report(self, output_file: Path):
        """创建迁移报告"""
        report = {
            'migration_summary': {
                'total_files_changed': len(self.changes_made),
                'total_changes': sum(change['changes'] for change in self.changes_made)
            },
            'changed_files': self.changes_made,
            'namespace_structure_created': True,
            'recommendations': [
                "运行测试确保所有导入正确工作",
                "检查是否有遗漏的导入路径需要更新",
                "验证namespace packages正确安装",
                "更新文档中的导入示例"
            ]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            import json
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📄 迁移报告已保存到: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="SAGE命名空间重构工具")
    parser.add_argument("--project-path", "-p", type=Path, required=True,
                       help="项目路径")
    parser.add_argument("--target-project", "-t", 
                       choices=['sage-core', 'sage-extensions', 'sage-dashboard'],
                       required=True, help="目标项目类型")
    parser.add_argument("--create-structure", action="store_true",
                       help="创建namespace package结构")
    parser.add_argument("--update-imports", action="store_true",
                       help="更新导入语句")
    parser.add_argument("--output-report", "-o", type=Path,
                       help="输出迁移报告文件")
    
    args = parser.parse_args()
    
    if not args.project_path.exists():
        print(f"❌ 项目路径不存在: {args.project_path}")
        return 1
    
    refactor = NamespaceRefactor(args.project_path)
    
    if args.create_structure:
        refactor.create_namespace_structure(args.target_project)
    
    if args.update_imports:
        refactor.refactor_imports()
    
    if args.output_report:
        refactor.create_migration_report(args.output_report)
    
    if not any([args.create_structure, args.update_imports]):
        print("⚠️  请指定至少一个操作: --create-structure 或 --update-imports")
        return 1
    
    print("✅ 命名空间重构完成！")
    return 0

if __name__ == "__main__":
    exit(main())
