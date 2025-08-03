#!/usr/bin/env python3
"""
SAGE项目分割工具
===============

根据分析结果，自动将monorepo分割成多个独立的子项目。
使用git filter-branch保留提交历史。
"""

import os
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Set
import argparse
import tempfile

class ProjectSplitter:
    """项目分割器"""
    
    def __init__(self, source_repo: Path, target_dir: Path):
        self.source_repo = Path(source_repo).resolve()
        self.target_dir = Path(target_dir).resolve()
        self.target_dir.mkdir(parents=True, exist_ok=True)
        
    def run_command(self, cmd: List[str], cwd: Path = None, check: bool = True) -> subprocess.CompletedProcess:
        """运行命令"""
        if cwd is None:
            cwd = self.source_repo
        
        print(f"🔧 运行命令: {' '.join(cmd)}")
        print(f"📁 工作目录: {cwd}")
        
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0 and check:
            print(f"❌ 命令失败: {' '.join(cmd)}")
            print(f"📤 标准输出: {result.stdout}")
            print(f"📤 错误输出: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, cmd)
        
        return result
    
    def clone_repo(self, target_path: Path) -> Path:
        """克隆原始仓库"""
        print(f"📥 克隆仓库到: {target_path}")
        
        if target_path.exists():
            shutil.rmtree(target_path)
        
        self.run_command([
            'git', 'clone', str(self.source_repo), str(target_path)
        ], cwd=self.target_dir)
        
        return target_path
    
    def filter_subdirectory(self, repo_path: Path, subdirs: List[str], preserve_structure: bool = False):
        """使用git filter-branch提取子目录"""
        print(f"🔍 提取子目录: {subdirs}")
        
        # 创建临时脚本进行复杂的目录过滤
        if len(subdirs) > 1 or preserve_structure:
            # 复杂过滤：保留多个目录或保持结构
            filter_script = self._create_index_filter_script(subdirs, preserve_structure)
            
            self.run_command([
                'git', 'filter-branch', '--force', '--prune-empty',
                '--index-filter', filter_script,
                '--', '--all'
            ], cwd=repo_path)
        else:
            # 简单过滤：单个子目录
            self.run_command([
                'git', 'filter-branch', '--force', '--prune-empty',
                '--subdirectory-filter', subdirs[0],
                '--', '--all'
            ], cwd=repo_path)
    
    def _create_index_filter_script(self, subdirs: List[str], preserve_structure: bool) -> str:
        """创建索引过滤脚本"""
        if preserve_structure:
            # 保持目录结构的过滤脚本
            dirs_pattern = ' '.join(f'"{d}"' for d in subdirs)
            return f'''
git ls-files -s | \\
awk '$4 ~ /^({"|".join(subdirs.replace("/", "\\/"))})\\// {{ print $0 }}' | \\
GIT_INDEX_FILE=$GIT_INDEX_FILE.new git update-index --index-info && \\
if [ -f "$GIT_INDEX_FILE.new" ]; then \\
    mv "$GIT_INDEX_FILE.new" "$GIT_INDEX_FILE"; \\
else \\
    rm -f "$GIT_INDEX_FILE"; \\
fi
            '''.strip()
        else:
            # 移动到根目录的过滤脚本
            return f'''
git ls-files -s | \\
sed -n 's#\\t{subdirs[0]}/\\(.*\\)#\\t\\1#p' | \\
GIT_INDEX_FILE=$GIT_INDEX_FILE.new git update-index --index-info && \\
if [ -f "$GIT_INDEX_FILE.new" ]; then \\
    mv "$GIT_INDEX_FILE.new" "$GIT_INDEX_FILE"; \\
else \\
    rm -f "$GIT_INDEX_FILE"; \\
fi
            '''.strip()
    
    def setup_project_structure(self, repo_path: Path, project_config: Dict):
        """设置项目结构"""
        print(f"🏗️  设置项目结构: {project_config['name']}")
        
        # 创建目标目录结构
        if 'target_structure' in project_config:
            target_structure = project_config['target_structure']
            if target_structure.endswith('/'):
                target_dir = repo_path / target_structure
                target_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建配置文件
        self._create_pyproject_toml(repo_path, project_config)
        self._create_readme(repo_path, project_config)
        self._create_gitignore(repo_path, project_config)
        self._create_github_workflows(repo_path, project_config)
    
    def _create_pyproject_toml(self, repo_path: Path, config: Dict):
        """创建pyproject.toml文件"""
        project_name = config['name']
        description = config.get('description', f'SAGE Framework - {project_name}')
        
        if project_name == 'sage-core':
            content = self._get_sage_core_pyproject_toml(description)
        elif project_name == 'sage-extensions':
            content = self._get_sage_extensions_pyproject_toml(description)
        elif project_name == 'sage-dashboard':
            content = self._get_sage_dashboard_pyproject_toml(description)
        else:
            content = self._get_generic_pyproject_toml(project_name, description)
        
        pyproject_path = repo_path / 'pyproject.toml'
        with open(pyproject_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"📄 创建: {pyproject_path}")
    
    def _get_sage_core_pyproject_toml(self, description: str) -> str:
        return '''[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "sage-core"
version = "1.0.0"
description = "{description}"
readme = "README.md"
requires-python = ">=3.11"
license = {{text = "MIT"}}
authors = [
    {{name = "IntelliStream Team", email = "sage@intellistream.cc"}},
]
keywords = ["rag", "llm", "dataflow", "reasoning"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]

dependencies = [
    "numpy>=1.21.0",
    "pandas>=1.3.0",
    "pydantic>=2.0.0",
    "typer>=0.9.0",
    "rich>=13.0.0",
    "PyYAML>=6.0",
    "httpx>=0.24.0",
    "ray>=2.8.0",
    "openai>=1.0.0",
    "tiktoken>=0.5.0",
    "transformers>=4.30.0",
    "torch>=2.0.0",
    "sentence-transformers>=2.2.0",
    "faiss-cpu>=1.7.0",
    "chromadb>=0.4.0",
    "redis>=4.5.0",
]

[project.optional-dependencies]
performance = ["sage-extensions>=1.0.0"]
dashboard = ["sage-dashboard>=1.0.0"]
full = ["sage-extensions>=1.0.0", "sage-dashboard>=1.0.0"]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "isort>=5.12.0",
    "flake8>=6.0.0",
    "mypy>=1.0.0",
    "pre-commit>=3.0.0",
]

[project.urls]
Homepage = "https://github.com/intellistream/sage-core"
Repository = "https://github.com/intellistream/sage-core.git"
Documentation = "https://sage-docs.intellistream.cc"

[project.scripts]
sage = "sage.cli.main:app"

[tool.setuptools]
package-dir = {{"" = "src"}}

[tool.setuptools.packages.find]
where = ["src"]
include = ["sage*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = ["--cov=sage", "--cov-report=term-missing"]

[tool.black]
line-length = 88
target-version = ["py311"]

[tool.isort]
profile = "black"
'''.format(description=description)
    
    def _get_sage_extensions_pyproject_toml(self, description: str) -> str:
        return '''[build-system]
requires = [
    "setuptools>=64",
    "wheel",
    "pybind11>=2.10.0",
    "cmake>=3.18",
    "ninja; platform_system!='Windows'",
]
build-backend = "setuptools.build_meta"

[project]
name = "sage-extensions"
version = "1.0.0"
description = "{description}"
readme = "README.md"
requires-python = ">=3.11"
license = {{text = "MIT"}}
authors = [
    {{name = "IntelliStream Team", email = "sage@intellistream.cc"}},
]
keywords = ["rag", "llm", "dataflow", "high-performance", "cpp"]

dependencies = [
    "sage-core>=1.0.0",
    "numpy>=1.21.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "cmake>=3.18",
    "ninja",
]

[project.urls]
Homepage = "https://github.com/intellistream/sage-extensions"
Repository = "https://github.com/intellistream/sage-extensions.git"

[tool.setuptools]
package-dir = {{"" = "src"}}
include-package-data = true

[tool.setuptools.packages.find]
where = ["src"]
include = ["sage*"]

[tool.setuptools.package-data]
"sage.extensions" = ["*.so", "*.pyd", "*.dll"]
'''.format(description=description)
    
    def _get_sage_dashboard_pyproject_toml(self, description: str) -> str:
        return '''[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "sage-dashboard"
version = "1.0.0"
description = "{description}"
readme = "README.md"
requires-python = ">=3.11"
license = {{text = "MIT"}}
authors = [
    {{name = "IntelliStream Team", email = "sage@intellistream.cc"}},
]
keywords = ["rag", "llm", "dashboard", "web", "api"]

dependencies = [
    "sage-core>=1.0.0",
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
    "pydantic>=2.0.0",
    "httpx>=0.24.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
]

[project.urls]
Homepage = "https://github.com/intellistream/sage-dashboard"
Repository = "https://github.com/intellistream/sage-dashboard.git"

[tool.setuptools]
package-dir = {{"" = "backend/src"}}

[tool.setuptools.packages.find]
where = ["backend/src"]
include = ["sage*"]
'''.format(description=description)
    
    def _get_generic_pyproject_toml(self, name: str, description: str) -> str:
        return f'''[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{name}"
version = "1.0.0"
description = "{description}"
readme = "README.md"
requires-python = ">=3.11"
license = {{text = "MIT"}}
authors = [
    {{name = "IntelliStream Team", email = "sage@intellistream.cc"}},
]

dependencies = []

[project.urls]
Homepage = "https://github.com/intellistream/{name}"
Repository = "https://github.com/intellistream/{name}.git"

[tool.setuptools.packages.find]
include = ["*"]
'''
    
    def _create_readme(self, repo_path: Path, config: Dict):
        """创建README.md文件"""
        project_name = config['name']
        description = config.get('description', f'SAGE Framework - {project_name}')
        
        content = f'''# {project_name}

{description}

## 概述

这是SAGE框架的 `{project_name}` 组件，从原始monorepo重构而来。

## 安装

```bash
pip install {project_name}
```

## 使用

```python
import sage
# 您的代码...
```

## 开发

```bash
# 克隆仓库
git clone https://github.com/intellistream/{project_name}.git
cd {project_name}

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest
```

## 贡献

欢迎提交PR和Issue！

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件。

## 相关项目

- [sage-core](https://github.com/intellistream/sage-core) - SAGE核心框架
- [sage-extensions](https://github.com/intellistream/sage-extensions) - 高性能C++扩展
- [sage-dashboard](https://github.com/intellistream/sage-dashboard) - Web界面和API
- [SAGE](https://github.com/intellistream/SAGE) - 完整生态系统
'''
        
        readme_path = repo_path / 'README.md'
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"📄 创建: {readme_path}")
    
    def _create_gitignore(self, repo_path: Path, config: Dict):
        """创建.gitignore文件"""
        project_name = config['name']
        
        base_content = '''# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/
cover/

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Project specific
logs/
.dev-env-info
'''
        
        if project_name == 'sage-extensions':
            base_content += '''
# C++ build artifacts
CMakeCache.txt
CMakeFiles/
cmake_install.cmake
Makefile
*.cmake
*.a
*.o
'''
        
        if project_name == 'sage-dashboard':
            base_content += '''
# Node.js
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.npm
.node_repl_history

# Angular
frontend/dist/
frontend/.angular/
'''
        
        gitignore_path = repo_path / '.gitignore'
        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write(base_content)
        
        print(f"📄 创建: {gitignore_path}")
    
    def _create_github_workflows(self, repo_path: Path, config: Dict):
        """创建GitHub Actions工作流"""
        workflows_dir = repo_path / '.github' / 'workflows'
        workflows_dir.mkdir(parents=True, exist_ok=True)
        
        project_name = config['name']
        
        # 基础测试工作流
        test_workflow = f'''name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11, 3.12]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{{{ matrix.python-version }}}}
      uses: actions/setup-python@v4
      with:
        python-version: ${{{{ matrix.python-version }}}}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"
    
    - name: Run tests
      run: |
        pytest
    
    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      if: matrix.python-version == '3.11'
'''
        
        if project_name == 'sage-extensions':
            # C++扩展需要额外的构建环境
            test_workflow = test_workflow.replace(
                '    - name: Install dependencies',
                '''    - name: Install C++ dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y cmake g++ ninja-build
    
    - name: Install dependencies'''
            )
        
        test_workflow_path = workflows_dir / 'test.yml'
        with open(test_workflow_path, 'w', encoding='utf-8') as f:
            f.write(test_workflow)
        
        print(f"📄 创建: {test_workflow_path}")
        
        # 发布工作流
        release_workflow = f'''name: Release

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    
    - name: Build package
      run: python -m build
    
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{{{ secrets.PYPI_API_TOKEN }}}}
      run: twine upload dist/*
'''
        
        release_workflow_path = workflows_dir / 'release.yml'
        with open(release_workflow_path, 'w', encoding='utf-8') as f:
            f.write(release_workflow)
        
        print(f"📄 创建: {release_workflow_path}")
    
    def split_project(self, project_config: Dict, source_dirs: List[str]):
        """分割单个项目"""
        project_name = project_config['name']
        print(f"\n{'='*60}")
        print(f"🚀 开始分割项目: {project_name}")
        print(f"📂 源目录: {source_dirs}")
        print(f"{'='*60}")
        
        # 创建目标路径
        target_path = self.target_dir / project_name
        
        # 克隆原始仓库
        temp_repo = self.clone_repo(target_path)
        
        try:
            # 过滤子目录
            self.filter_subdirectory(temp_repo, source_dirs, preserve_structure=True)
            
            # 设置项目结构
            self.setup_project_structure(temp_repo, project_config)
            
            # 清理git历史
            self.run_command(['git', 'gc', '--aggressive', '--prune=now'], cwd=temp_repo)
            
            print(f"✅ 项目 {project_name} 分割完成")
            print(f"📁 路径: {target_path}")
            
        except Exception as e:
            print(f"❌ 分割项目 {project_name} 时出错: {e}")
            raise
    
    def split_all_projects(self, migration_plan_file: Path):
        """根据迁移计划分割所有项目"""
        with open(migration_plan_file, 'r', encoding='utf-8') as f:
            migration_plan = json.load(f)
        
        # 项目配置映射
        project_configs = {
            'sage-core': {
                'name': 'sage-core',
                'description': '核心Python框架',
                'source_dirs': ['sage']
            },
            'sage-extensions': {
                'name': 'sage-extensions',
                'description': '高性能C++扩展',
                'source_dirs': ['sage_ext']
            },
            'sage-dashboard': {
                'name': 'sage-dashboard',
                'description': 'Web界面和API',
                'source_dirs': ['frontend']
            }
        }
        
        # 按优先级排序分割
        projects_by_priority = []
        for project_name, plan_config in migration_plan.items():
            if project_name in project_configs:
                project_config = project_configs[project_name]
                project_config['migration_priority'] = plan_config.get('migration_priority', 999)
                projects_by_priority.append(project_config)
        
        projects_by_priority.sort(key=lambda x: x['migration_priority'])
        
        # 分割每个项目
        for project_config in projects_by_priority:
            self.split_project(project_config, project_config['source_dirs'])
        
        print(f"\n🎉 所有项目分割完成！")
        print(f"📁 输出目录: {self.target_dir}")

def main():
    parser = argparse.ArgumentParser(description="SAGE项目分割工具")
    parser.add_argument("--source-repo", "-s", type=Path, required=True,
                       help="源仓库路径")
    parser.add_argument("--target-dir", "-t", type=Path, required=True,
                       help="目标目录路径")
    parser.add_argument("--migration-plan", "-p", type=Path,
                       help="迁移计划文件 (migration_plan.json)")
    parser.add_argument("--project", type=str, choices=['sage-core', 'sage-extensions', 'sage-dashboard'],
                       help="只分割指定的项目")
    
    args = parser.parse_args()
    
    if not args.source_repo.exists():
        print(f"❌ 源仓库不存在: {args.source_repo}")
        return 1
    
    if not args.source_repo.is_dir():
        print(f"❌ 源仓库不是目录: {args.source_repo}")
        return 1
    
    # 检查是否为git仓库
    if not (args.source_repo / '.git').exists():
        print(f"❌ 源路径不是git仓库: {args.source_repo}")
        return 1
    
    splitter = ProjectSplitter(args.source_repo, args.target_dir)
    
    if args.project:
        # 分割单个项目
        project_configs = {
            'sage-core': {
                'name': 'sage-core',
                'description': '核心Python框架',
                'source_dirs': ['sage']
            },
            'sage-extensions': {
                'name': 'sage-extensions',
                'description': '高性能C++扩展',
                'source_dirs': ['sage_ext']
            },
            'sage-dashboard': {
                'name': 'sage-dashboard',
                'description': 'Web界面和API',
                'source_dirs': ['frontend']
            }
        }
        
        project_config = project_configs[args.project]
        splitter.split_project(project_config, project_config['source_dirs'])
    else:
        # 分割所有项目
        if not args.migration_plan:
            print("❌ 需要指定迁移计划文件或单个项目")
            return 1
        
        if not args.migration_plan.exists():
            print(f"❌ 迁移计划文件不存在: {args.migration_plan}")
            return 1
        
        splitter.split_all_projects(args.migration_plan)
    
    return 0

if __name__ == "__main__":
    exit(main())
