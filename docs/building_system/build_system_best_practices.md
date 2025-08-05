# 构建系统最佳实践

## 目录
- [概述](#概述)
- [企业级构建标准](#企业级构建标准)
- [依赖管理最佳实践](#依赖管理最佳实践)
- [CI/CD 集成](#cicd-集成)
- [性能优化](#性能优化)
- [安全考虑](#安全考虑)
- [监控和维护](#监控和维护)
- [团队协作](#团队协作)

## 概述

本文档总结了 SAGE 项目在构建系统方面的最佳实践，这些实践经过实际项目验证，适用于企业级 Python 项目开发。

### 核心原则

1. **标准化优先**: 遵循 Python 官方标准和社区最佳实践
2. **自动化为王**: 最大化自动化构建、测试和部署流程
3. **可重现构建**: 确保在任何环境下都能获得一致的构建结果
4. **性能导向**: 优化构建时间和资源使用
5. **安全第一**: 在构建过程中集成安全检查

## 企业级构建标准

### 1. 项目结构标准化

#### Monorepo 组织最佳实践

```
project-root/
├── pyproject.toml          # 工作空间配置
├── requirements/           # 分层依赖管理
│   ├── base.txt           # 核心依赖
│   ├── dev.txt            # 开发依赖
│   ├── prod.txt           # 生产依赖
│   └── ci.txt             # CI 专用依赖
├── packages/              # 子包
│   ├── core/
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   └── tests/
│   └── extensions/
├── tools/                 # 构建工具
│   ├── build.py          # 主构建脚本
│   ├── deploy.py         # 部署脚本
│   └── quality.py        # 代码质量检查
├── scripts/              # 便利脚本
├── docs/
├── tests/               # 集成测试
└── .github/             # CI/CD 配置
```

#### 配置文件层次结构

```toml
# 根 pyproject.toml - 工作空间级配置
[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "sage-workspace"
dynamic = ["version"]

# 工具配置统一管理
[tool.black]
line-length = 88
target-version = ["py311"]

[tool.isort]
profile = "black"
known_first_party = ["sage"]

[tool.mypy]
python_version = "3.11"
strict = true
```

### 2. 版本管理策略

#### 语义化版本控制

```python
# tools/version_manager.py
import subprocess
from pathlib import Path
import re

class VersionManager:
    """统一版本管理"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.version_file = project_root / "VERSION"
    
    def get_version(self) -> str:
        """获取当前版本"""
        if self.version_file.exists():
            return self.version_file.read_text().strip()
        
        # 从 git 标签推导版本
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                capture_output=True, text=True, check=True
            )
            return result.stdout.strip().lstrip('v')
        except subprocess.CalledProcessError:
            return "0.1.0"
    
    def bump_version(self, part: str = "patch") -> str:
        """版本递增"""
        current = self.get_version()
        major, minor, patch = map(int, current.split('.'))
        
        if part == "major":
            major += 1
            minor = patch = 0
        elif part == "minor":
            minor += 1
            patch = 0
        else:  # patch
            patch += 1
        
        new_version = f"{major}.{minor}.{patch}"
        self.version_file.write_text(new_version)
        return new_version
    
    def update_all_packages(self, version: str):
        """更新所有子包版本"""
        for package_dir in (self.project_root / "packages").glob("*/"):
            pyproject_file = package_dir / "pyproject.toml"
            if pyproject_file.exists():
                self._update_pyproject_version(pyproject_file, version)
    
    def _update_pyproject_version(self, file_path: Path, version: str):
        """更新 pyproject.toml 中的版本"""
        content = file_path.read_text()
        updated = re.sub(
            r'version\s*=\s*"[^"]*"',
            f'version = "{version}"',
            content
        )
        file_path.write_text(updated)
```

### 3. 构建脚本标准化

#### 主构建脚本

```python
# tools/build.py
#!/usr/bin/env python3
"""
SAGE 项目统一构建脚本
"""

import sys
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class SAGEBuilder:
    """SAGE 项目构建器"""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.packages_dir = self.project_root / "packages"
        self.dist_dir = self.project_root / "dist"
        
    def clean(self):
        """清理构建产物"""
        logger.info("🧹 Cleaning build artifacts...")
        
        patterns = [
            "**/__pycache__",
            "**/*.pyc", 
            "**/*.pyo",
            "**/build",
            "**/dist",
            "**/*.egg-info",
            "**/.pytest_cache",
            "**/.mypy_cache",
        ]
        
        for pattern in patterns:
            for path in self.project_root.glob(pattern):
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
        
        logger.info("✅ Clean completed")
    
    def check_dependencies(self):
        """检查构建依赖"""
        logger.info("🔍 Checking build dependencies...")
        
        required_tools = {
            "python": "python --version",
            "pip": "pip --version",
            "build": "python -m build --version",
        }
        
        missing_tools = []
        for tool, check_cmd in required_tools.items():
            try:
                subprocess.run(check_cmd.split(), 
                             capture_output=True, check=True)
                logger.info(f"✅ {tool} available")
            except (subprocess.CalledProcessError, FileNotFoundError):
                missing_tools.append(tool)
                logger.error(f"❌ {tool} not found")
        
        if missing_tools:
            logger.error(f"Missing tools: {missing_tools}")
            logger.info("Install with: pip install build")
            sys.exit(1)
    
    def build_package(self, package_name: str, build_type: str = "wheel"):
        """构建单个包"""
        package_dir = self.packages_dir / package_name
        
        if not package_dir.exists():
            logger.error(f"Package {package_name} not found")
            return False
        
        logger.info(f"🔨 Building {package_name}...")
        
        try:
            cmd = ["python", "-m", "build"]
            if build_type == "wheel":
                cmd.append("--wheel")
            elif build_type == "sdist":
                cmd.append("--sdist")
            
            subprocess.run(cmd, cwd=package_dir, check=True)
            logger.info(f"✅ {package_name} built successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to build {package_name}: {e}")
            return False
    
    def build_all(self, build_type: str = "wheel", parallel: bool = True):
        """构建所有包"""
        logger.info("🚀 Building all packages...")
        
        # 获取构建顺序（考虑依赖关系）
        build_order = self._get_build_order()
        
        results = {}
        for package in build_order:
            results[package] = self.build_package(package, build_type)
        
        # 报告结果
        successful = [pkg for pkg, success in results.items() if success]
        failed = [pkg for pkg, success in results.items() if not success]
        
        logger.info(f"✅ Successfully built: {successful}")
        if failed:
            logger.error(f"❌ Failed to build: {failed}")
            return False
        
        return True
    
    def _get_build_order(self) -> List[str]:
        """获取包的构建顺序（基于依赖关系）"""
        # 简化版本：按字母顺序
        # 实际项目中应该分析 pyproject.toml 的依赖关系
        packages = []
        for package_dir in self.packages_dir.iterdir():
            if package_dir.is_dir() and (package_dir / "pyproject.toml").exists():
                packages.append(package_dir.name)
        
        # 定义已知的依赖顺序
        known_order = [
            "sage-utils",
            "sage-kernel", 
            "sage-lib",
            "sage-extensions",
            "sage-plugins",
            "sage-service",
            "sage-cli",
        ]
        
        # 按已知顺序排序，未知包放最后
        ordered = []
        for pkg in known_order:
            if pkg in packages:
                ordered.append(pkg)
                packages.remove(pkg)
        
        ordered.extend(sorted(packages))
        return ordered
    
    def test(self, package: Optional[str] = None, coverage: bool = False):
        """运行测试"""
        logger.info("🧪 Running tests...")
        
        cmd = ["python", "-m", "pytest"]
        
        if package:
            test_path = self.packages_dir / package / "tests"
        else:
            test_path = self.project_root / "tests"
        
        cmd.append(str(test_path))
        
        if coverage:
            cmd.extend(["--cov", "--cov-report=html", "--cov-report=term"])
        
        try:
            subprocess.run(cmd, check=True)
            logger.info("✅ Tests passed")
            return True
        except subprocess.CalledProcessError:
            logger.error("❌ Tests failed")
            return False
    
    def lint(self):
        """代码质量检查"""
        logger.info("🔍 Running code quality checks...")
        
        checks = [
            ("black --check .", "Code formatting"),
            ("isort --check-only .", "Import sorting"),
            ("mypy packages/", "Type checking"),
            ("ruff check .", "Linting"),
        ]
        
        all_passed = True
        for cmd, description in checks:
            logger.info(f"Running {description}...")
            try:
                subprocess.run(cmd.split(), check=True, cwd=self.project_root)
                logger.info(f"✅ {description} passed")
            except subprocess.CalledProcessError:
                logger.error(f"❌ {description} failed")
                all_passed = False
        
        return all_passed

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="SAGE 项目构建工具")
    parser.add_argument("action", choices=[
        "clean", "build", "test", "lint", "all"
    ], help="构建操作")
    parser.add_argument("--package", help="指定包名")
    parser.add_argument("--type", choices=["wheel", "sdist"], 
                       default="wheel", help="构建类型")
    parser.add_argument("--coverage", action="store_true", 
                       help="运行测试时启用覆盖率")
    
    args = parser.parse_args()
    builder = SAGEBuilder()
    
    if args.action == "clean":
        builder.clean()
    elif args.action == "build":
        builder.check_dependencies()
        if args.package:
            builder.build_package(args.package, args.type)
        else:
            builder.build_all(args.type)
    elif args.action == "test":
        builder.test(args.package, args.coverage)
    elif args.action == "lint":
        builder.lint()
    elif args.action == "all":
        builder.clean()
        builder.check_dependencies()
        if not builder.lint():
            sys.exit(1)
        if not builder.test():
            sys.exit(1)
        if not builder.build_all():
            sys.exit(1)
        logger.info("🎉 All tasks completed successfully!")

if __name__ == "__main__":
    main()
```

## 依赖管理最佳实践

### 1. 分层依赖管理

```
requirements/
├── base.txt              # 核心运行时依赖
├── dev.txt              # 开发依赖
├── test.txt             # 测试依赖
├── docs.txt             # 文档生成依赖
├── ci.txt               # CI 专用依赖
└── constraints.txt      # 版本约束
```

```text
# requirements/base.txt
numpy>=1.21.0,<2.0.0
requests>=2.28.0
pydantic>=1.10.0,<2.0.0

# requirements/dev.txt
-r base.txt
black>=23.0.0
isort>=5.12.0
mypy>=1.0.0
pre-commit>=3.0.0

# requirements/constraints.txt
# 统一版本约束，解决依赖冲突
certifi==2023.7.22
urllib3==2.0.4
```

### 2. 依赖版本锁定策略

```python
# tools/dependency_manager.py
import subprocess
import json
from pathlib import Path

class DependencyManager:
    """依赖管理器"""
    
    def generate_lockfile(self):
        """生成依赖锁定文件"""
        cmd = [
            "pip-compile", 
            "--generate-hashes",  # 安全哈希
            "--resolver=backtracking",
            "requirements/base.txt"
        ]
        
        subprocess.run(cmd, check=True)
    
    def check_vulnerabilities(self):
        """检查安全漏洞"""
        cmd = ["safety", "check", "--json"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            vulnerabilities = json.loads(result.stdout)
            for vuln in vulnerabilities:
                print(f"⚠️  {vuln['package']}: {vuln['advisory']}")
            return False
        return True
    
    def audit_licenses(self):
        """审计许可证"""
        cmd = ["pip-licenses", "--format=json"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        licenses = json.loads(result.stdout)
        problematic = []
        
        allowed_licenses = {
            "MIT", "BSD", "Apache", "Apache-2.0", "ISC", "MPL-2.0"
        }
        
        for pkg in licenses:
            if pkg["License"] not in allowed_licenses:
                problematic.append(pkg)
        
        if problematic:
            print("🚨 Problematic licenses found:")
            for pkg in problematic:
                print(f"  {pkg['Name']}: {pkg['License']}")
        
        return len(problematic) == 0
```

## CI/CD 集成

### 1. GitHub Actions 最佳实践

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  PYTHON_VERSION: "3.11"
  POETRY_VERSION: "1.6.0"

jobs:
  quality:
    name: Code Quality
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        cache: 'pip'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements/dev.txt
    
    - name: Run quality checks
      run: |
        python tools/build.py lint
    
    - name: Security audit
      run: |
        pip install safety
        safety check
    
    - name: License audit  
      run: |
        pip install pip-licenses
        python tools/dependency_manager.py audit-licenses

  test:
    name: Test Suite
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.10", "3.11", "3.12"]
        
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
        cache: 'pip'
    
    - name: Install system dependencies
      if: runner.os == 'Linux'
      run: |
        sudo apt-get update
        sudo apt-get install -y build-essential cmake
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements/test.txt
    
    - name: Run tests
      run: |
        python tools/build.py test --coverage
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  build:
    name: Build Packages
    runs-on: ubuntu-latest
    needs: [quality, test]
    strategy:
      matrix:
        package: [sage-kernel, sage-lib, sage-extensions]
        
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        cache: 'pip'
    
    - name: Install build dependencies
      run: |
        python -m pip install --upgrade pip build
    
    - name: Build package
      run: |
        python tools/build.py build --package ${{ matrix.package }}
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: dist-${{ matrix.package }}
        path: packages/${{ matrix.package }}/dist/

  deploy:
    name: Deploy
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Download all artifacts
      uses: actions/download-artifact@v3
    
    - name: Publish to PyPI
      uses: pypa/gh-action-pypi-publish@v1.8.10
      with:
        password: ${{ secrets.PYPI_API_TOKEN }}
        packages_dir: dist/
```

### 2. 智能测试选择

```python
# tools/smart_testing.py
import subprocess
import json
from pathlib import Path
from typing import Set, List

class SmartTestSelector:
    """智能测试选择器"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        
    def get_changed_files(self, base_branch: str = "main") -> Set[Path]:
        """获取变更文件"""
        cmd = ["git", "diff", "--name-only", f"{base_branch}...HEAD"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        changed_files = set()
        for line in result.stdout.strip().split('\n'):
            if line:
                changed_files.add(Path(line))
        
        return changed_files
    
    def find_related_tests(self, changed_files: Set[Path]) -> Set[Path]:
        """查找相关测试"""
        test_files = set()
        
        for file_path in changed_files:
            # 直接测试文件
            if self._is_test_file(file_path):
                test_files.add(file_path)
                continue
            
            # 查找对应的测试文件
            related_tests = self._find_tests_for_file(file_path)
            test_files.update(related_tests)
        
        return test_files
    
    def _is_test_file(self, file_path: Path) -> bool:
        """检查是否为测试文件"""
        return (file_path.name.startswith("test_") and 
                file_path.suffix == ".py")
    
    def _find_tests_for_file(self, file_path: Path) -> Set[Path]:
        """查找文件对应的测试"""
        tests = set()
        
        # 1. 同名测试文件
        if file_path.suffix == ".py":
            test_name = f"test_{file_path.stem}.py"
            
            # 在包的测试目录中查找
            if "packages" in file_path.parts:
                package_idx = file_path.parts.index("packages")
                package_name = file_path.parts[package_idx + 1]
                test_dir = self.project_root / "packages" / package_name / "tests"
                
                potential_test = test_dir / test_name
                if potential_test.exists():
                    tests.add(potential_test)
        
        # 2. 导入关系分析（简化版）
        tests.update(self._find_tests_by_imports(file_path))
        
        return tests
    
    def _find_tests_by_imports(self, file_path: Path) -> Set[Path]:
        """通过导入关系查找测试"""
        tests = set()
        
        # 搜索所有测试文件，查找导入了目标文件的测试
        for test_file in self.project_root.glob("**/test_*.py"):
            try:
                content = test_file.read_text(encoding='utf-8')
                
                # 简单的导入检查
                module_path = self._get_module_path(file_path)
                if module_path and module_path in content:
                    tests.add(test_file)
                    
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        return tests
    
    def _get_module_path(self, file_path: Path) -> str:
        """获取模块导入路径"""
        if "src" not in file_path.parts:
            return ""
        
        src_idx = file_path.parts.index("src")
        module_parts = file_path.parts[src_idx + 1:]
        
        if module_parts[-1].endswith(".py"):
            module_parts = module_parts[:-1] + (module_parts[-1][:-3],)
        
        return ".".join(module_parts)
```

## 性能优化

### 1. 构建缓存策略

```python
# tools/build_cache.py
import hashlib
import json
import pickle
from pathlib import Path
from typing import Dict, Any

class BuildCache:
    """构建缓存管理"""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self.metadata_file = cache_dir / "metadata.json"
        
    def get_file_hash(self, file_path: Path) -> str:
        """计算文件哈希"""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def get_cache_key(self, package_name: str, 
                     source_files: List[Path]) -> str:
        """生成缓存键"""
        key_data = {
            "package": package_name,
            "files": {str(f): self.get_file_hash(f) for f in source_files}
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def is_cached(self, cache_key: str) -> bool:
        """检查是否已缓存"""
        cache_file = self.cache_dir / f"{cache_key}.cache"
        return cache_file.exists()
    
    def store(self, cache_key: str, data: Any):
        """存储到缓存"""
        cache_file = self.cache_dir / f"{cache_key}.cache"
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
    
    def load(self, cache_key: str) -> Any:
        """从缓存加载"""
        cache_file = self.cache_dir / f"{cache_key}.cache"
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    
    def cleanup_old_cache(self, max_age_days: int = 7):
        """清理旧缓存"""
        import time
        
        cutoff_time = time.time() - (max_age_days * 24 * 3600)
        
        for cache_file in self.cache_dir.glob("*.cache"):
            if cache_file.stat().st_mtime < cutoff_time:
                cache_file.unlink()
```

### 2. 并行构建优化

```python
# tools/parallel_builder.py
import concurrent.futures
import multiprocessing
from typing import List, Callable, Any

class ParallelBuilder:
    """并行构建器"""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or multiprocessing.cpu_count()
    
    def build_packages_parallel(self, packages: List[str], 
                               build_func: Callable[[str], bool]) -> Dict[str, bool]:
        """并行构建多个包"""
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            # 提交所有构建任务
            future_to_package = {
                executor.submit(build_func, pkg): pkg 
                for pkg in packages
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_package):
                package = future_to_package[future]
                try:
                    results[package] = future.result()
                except Exception as exc:
                    print(f'Package {package} generated an exception: {exc}')
                    results[package] = False
        
        return results
    
    def run_tests_parallel(self, test_groups: List[List[str]]) -> List[bool]:
        """并行运行测试组"""
        def run_test_group(test_files: List[str]) -> bool:
            import subprocess
            cmd = ["python", "-m", "pytest"] + test_files
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                return True
            except subprocess.CalledProcessError:
                return False
        
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            futures = [executor.submit(run_test_group, group) 
                      for group in test_groups]
            
            return [future.result() for future in futures]
```

## 安全考虑

### 1. 依赖安全扫描

```python
# tools/security_scanner.py
import subprocess
import json
from typing import List, Dict

class SecurityScanner:
    """安全扫描器"""
    
    def scan_dependencies(self) -> List[Dict]:
        """扫描依赖漏洞"""
        cmd = ["safety", "check", "--json", "--ignore", "70612"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return []  # 无漏洞
        
        try:
            vulnerabilities = json.loads(result.stdout)
            return vulnerabilities
        except json.JSONDecodeError:
            return []
    
    def scan_code_secrets(self) -> List[Dict]:
        """扫描代码中的密钥"""
        cmd = ["truffleHog", ".", "--json"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        secrets = []
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                try:
                    secret = json.loads(line)
                    secrets.append(secret)
                except json.JSONDecodeError:
                    continue
        
        return secrets
    
    def generate_sbom(self) -> Dict:
        """生成软件物料清单 (SBOM)"""
        cmd = ["pip", "list", "--format=json"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        packages = json.loads(result.stdout)
        
        sbom = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "components": []
        }
        
        for pkg in packages:
            component = {
                "type": "library",
                "name": pkg["name"],
                "version": pkg["version"],
                "purl": f"pkg:pypi/{pkg['name']}@{pkg['version']}"
            }
            sbom["components"].append(component)
        
        return sbom
```

### 2. 构建环境隔离

```dockerfile
# Dockerfile.build - 构建环境隔离
FROM python:3.11-slim as builder

# 安全更新
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git && \
    rm -rf /var/lib/apt/lists/*

# 创建非特权用户
RUN useradd --create-home --shell /bin/bash builder
USER builder
WORKDIR /home/builder

# 复制依赖文件
COPY --chown=builder:builder requirements/ ./requirements/
COPY --chown=builder:builder pyproject.toml ./

# 安装依赖
RUN pip install --user --no-cache-dir -r requirements/dev.txt

# 复制源码
COPY --chown=builder:builder . .

# 构建
RUN python tools/build.py all

# 生产环境镜像
FROM python:3.11-slim as runtime

RUN useradd --create-home --shell /bin/bash sage
USER sage
WORKDIR /home/sage

# 只复制必要文件
COPY --from=builder --chown=sage:sage /home/builder/dist/ ./dist/

# 安装构建产物
RUN pip install --user --no-cache-dir dist/*.whl

CMD ["python", "-m", "sage"]
```

## 监控和维护

### 1. 构建指标收集

```python
# tools/build_metrics.py
import time
import json
import psutil
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass, asdict

@dataclass
class BuildMetrics:
    """构建指标"""
    duration: float
    memory_peak_mb: float
    cpu_usage_avg: float
    cache_hit_rate: float
    test_coverage: float
    package_size_mb: float
    
class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.start_time = None
        self.memory_samples = []
        self.cpu_samples = []
        
    def start_collection(self):
        """开始收集指标"""
        self.start_time = time.time()
        self.memory_samples = []
        self.cpu_samples = []
        
    def sample_resources(self):
        """采样资源使用"""
        process = psutil.Process()
        self.memory_samples.append(process.memory_info().rss / 1024 / 1024)
        self.cpu_samples.append(process.cpu_percent())
        
    def finalize_metrics(self, cache_hits: int, cache_total: int,
                        coverage: float, package_size: float) -> BuildMetrics:
        """完成指标收集"""
        duration = time.time() - self.start_time
        memory_peak = max(self.memory_samples) if self.memory_samples else 0
        cpu_avg = sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0
        cache_hit_rate = cache_hits / cache_total if cache_total > 0 else 0
        
        return BuildMetrics(
            duration=duration,
            memory_peak_mb=memory_peak,
            cpu_usage_avg=cpu_avg,
            cache_hit_rate=cache_hit_rate,
            test_coverage=coverage,
            package_size_mb=package_size
        )
    
    def save_metrics(self, metrics: BuildMetrics, output_file: Path):
        """保存指标"""
        with open(output_file, 'w') as f:
            json.dump(asdict(metrics), f, indent=2)
```

### 2. 健康检查和报告

```python
# tools/health_checker.py
import subprocess
import json
from pathlib import Path
from typing import Dict, List

class HealthChecker:
    """项目健康检查"""
    
    def check_project_health(self) -> Dict:
        """全面健康检查"""
        results = {
            "overall": "healthy",
            "checks": {}
        }
        
        # 依赖检查
        results["checks"]["dependencies"] = self._check_dependencies()
        
        # 代码质量检查
        results["checks"]["code_quality"] = self._check_code_quality()
        
        # 测试状态检查
        results["checks"]["tests"] = self._check_tests()
        
        # 安全检查
        results["checks"]["security"] = self._check_security()
        
        # 文档检查
        results["checks"]["documentation"] = self._check_documentation()
        
        # 判断整体状态
        failed_checks = [name for name, result in results["checks"].items() 
                        if not result.get("passed", False)]
        
        if failed_checks:
            results["overall"] = "unhealthy"
            results["failed_checks"] = failed_checks
        
        return results
    
    def _check_dependencies(self) -> Dict:
        """检查依赖状态"""
        try:
            # 检查过期依赖
            result = subprocess.run(
                ["pip", "list", "--outdated", "--format=json"],
                capture_output=True, text=True, check=True
            )
            outdated = json.loads(result.stdout)
            
            return {
                "passed": len(outdated) == 0,
                "outdated_packages": len(outdated),
                "details": outdated[:5]  # 只显示前5个
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}
    
    def _check_code_quality(self) -> Dict:
        """检查代码质量"""
        checks = [
            (["black", "--check", "."], "formatting"),
            (["isort", "--check-only", "."], "imports"),
            (["mypy", "packages/"], "typing"),
            (["ruff", "check", "."], "linting"),
        ]
        
        results = {}
        all_passed = True
        
        for cmd, name in checks:
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                results[name] = True
            except subprocess.CalledProcessError:
                results[name] = False
                all_passed = False
        
        return {"passed": all_passed, "details": results}
    
    def _check_tests(self) -> Dict:
        """检查测试状态"""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--collect-only", "-q"],
                capture_output=True, text=True
            )
            
            # 解析输出获取测试数量
            lines = result.stdout.strip().split('\n')
            test_count = 0
            for line in lines:
                if "test session starts" in line:
                    continue
                if " collected" in line:
                    test_count = int(line.split()[0])
                    break
            
            return {
                "passed": test_count > 0,
                "test_count": test_count,
                "collection_issues": result.returncode != 0
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}
    
    def _check_security(self) -> Dict:
        """检查安全状态"""
        try:
            result = subprocess.run(
                ["safety", "check", "--json"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                return {"passed": True, "vulnerabilities": 0}
            else:
                vulns = json.loads(result.stdout)
                return {
                    "passed": False,
                    "vulnerabilities": len(vulns),
                    "critical": len([v for v in vulns if v.get("severity") == "critical"])
                }
        except Exception as e:
            return {"passed": False, "error": str(e)}
    
    def _check_documentation(self) -> Dict:
        """检查文档状态"""
        doc_files = list(Path(".").glob("**/*.md"))
        readme_exists = (Path("README.md").exists() or 
                        Path("readme.md").exists())
        
        return {
            "passed": readme_exists and len(doc_files) > 0,
            "readme_exists": readme_exists,
            "doc_files_count": len(doc_files)
        }
```

## 团队协作

### 1. 开发环境标准化

```python
# tools/dev_setup.py
#!/usr/bin/env python3
"""
开发环境自动化设置脚本
"""

import subprocess
import sys
from pathlib import Path

class DevEnvironmentSetup:
    """开发环境设置"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        
    def setup(self):
        """完整开发环境设置"""
        print("🚀 Setting up SAGE development environment...")
        
        self._check_python_version()
        self._install_dependencies()
        self._setup_pre_commit()
        self._create_vscode_settings()
        self._run_initial_build()
        
        print("✅ Development environment setup complete!")
        print("\n📝 Next steps:")
        print("1. Activate your virtual environment")
        print("2. Run: python tools/build.py test")
        print("3. Start coding! 🎉")
    
    def _check_python_version(self):
        """检查Python版本"""
        version = sys.version_info
        if version < (3, 10):
            raise RuntimeError(f"Python 3.10+ required, got {version.major}.{version.minor}")
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    
    def _install_dependencies(self):
        """安装开发依赖"""
        print("📦 Installing dependencies...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-e", ".", 
            "-r", "requirements/dev.txt"
        ], check=True)
    
    def _setup_pre_commit(self):
        """设置pre-commit钩子"""
        print("🔧 Setting up pre-commit hooks...")
        subprocess.run(["pre-commit", "install"], check=True)
    
    def _create_vscode_settings(self):
        """创建VSCode设置"""
        vscode_dir = self.project_root / ".vscode"
        vscode_dir.mkdir(exist_ok=True)
        
        settings = {
            "python.defaultInterpreterPath": "./venv/bin/python",
            "python.linting.enabled": True,
            "python.linting.mypyEnabled": True,
            "python.formatting.provider": "black",
            "python.sortImports.args": ["--profile", "black"],
            "editor.formatOnSave": True,
            "editor.codeActionsOnSave": {
                "source.organizeImports": True
            }
        }
        
        import json
        settings_file = vscode_dir / "settings.json"
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
    
    def _run_initial_build(self):
        """运行初始构建"""
        print("🔨 Running initial build...")
        subprocess.run([sys.executable, "tools/build.py", "lint"], check=True)

if __name__ == "__main__":
    setup = DevEnvironmentSetup()
    setup.setup()
```

### 2. 代码审查清单

```markdown
# 代码审查清单

## 📋 构建系统审查要点

### pyproject.toml 配置
- [ ] 版本号遵循语义化版本规范
- [ ] 依赖版本约束合理（不过于宽松或严格）
- [ ] 构建系统要求完整且版本适当
- [ ] 工具配置（black, mypy, pytest）统一且正确

### setup.py（如有）
- [ ] 自定义构建逻辑必要且合理
- [ ] 错误处理完善
- [ ] 跨平台兼容性考虑
- [ ] 系统依赖检查完整

### 依赖管理
- [ ] 新增依赖必要且经过评估
- [ ] 依赖许可证兼容
- [ ] 无已知安全漏洞
- [ ] 不与现有依赖冲突

### 测试
- [ ] 新功能有对应测试
- [ ] 测试覆盖率不下降
- [ ] 测试可靠且快速
- [ ] 测试文件结构规范

### 文档
- [ ] API 变更有文档更新
- [ ] README 保持最新
- [ ] 变更日志已更新
- [ ] 使用示例正确

### CI/CD
- [ ] 构建在所有平台通过
- [ ] 所有质量检查通过
- [ ] 部署流程测试正常
- [ ] 性能无显著回归
```

## 总结

这些最佳实践为 SAGE 项目提供了：

1. **标准化流程**: 统一的构建、测试、部署标准
2. **自动化工具**: 减少手工操作，提高效率
3. **质量保证**: 多层次的质量检查机制
4. **安全考虑**: 从依赖到部署的全方位安全
5. **团队协作**: 标准化的开发环境和流程

通过遵循这些最佳实践，项目能够：
- **提高开发效率**: 自动化减少重复工作
- **保证代码质量**: 多重检查确保高质量
- **增强安全性**: 全方位安全扫描和防护
- **改善协作**: 标准化流程便于团队协作
- **降低维护成本**: 良好的结构和文档化

这些实践经过 SAGE 项目的实际验证，可以直接应用于类似的企业级 Python 项目。

← 返回：[Python C++ 项目规范](./python_cpp_project_standards.md) | [文档首页](./README.md)
