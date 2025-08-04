#!/usr/bin/env python3
"""
SAGE Utils 重构脚本
将 sage-utils 按照新架构分解为三个专门的包

执行顺序：
1. sage-kernel-utils - 基础系统工具
2. sage-kernel-runtime-extended - 运行时扩展
3. sage-middleware-llm - LLM 服务和客户端
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

class UtilsRefactor:
    def __init__(self):
        self.base_dir = Path("/home/flecther/SAGE/packages")
        self.utils_dir = self.base_dir / "sage-utils" / "src" / "sage" / "utils"
        
        # 定义文件迁移映射
        self.migration_map = {
            "sage-kernel-utils": {
                "target_path": "src/sage/kernel/utils",
                "files": {
                    # 配置管理
                    "config/": [
                        ("config.py", "config/manager.py"),
                        ("config_loader.py", "config/loader.py"),
                    ],
                    # 日志系统
                    "logging/": [
                        ("logging.py", "logging/basic.py"),
                        ("logger/", "logging/"),  # 整个目录
                    ],
                    # 系统工具
                    "system/": [
                        ("system/environment_utils.py", "system/environment.py"),
                        ("system/process_utils.py", "system/process.py"),
                        ("system/network_utils.py", "system/network.py"),
                    ],
                    # 基础序列化
                    "serialization/": [
                        ("serialization/exceptions.py", "serialization/exceptions.py"),
                        ("serialization/config.py", "serialization/config.py"),
                    ]
                }
            },
            
            "sage-kernel-runtime-extended": {
                "target_path": "src/sage/kernel/runtime",
                "files": {
                    # 通信系统
                    "communication/": [
                        ("actor_wrapper.py", "communication/actor.py"),
                        ("network/", "communication/network/"),  # 网络通信部分
                    ],
                    # 分布式支持
                    "distributed/": [
                        ("ray_helper.py", "distributed/ray.py"),
                    ],
                    # 高级序列化
                    "serialization/": [
                        ("serialization/universal_serializer.py", "serialization/universal.py"),
                        ("serialization/dill_serializer.py", "serialization/dill.py"),
                        ("serialization/ray_trimmer.py", "serialization/ray_trimmer.py"),
                        ("serialization/preprocessor.py", "serialization/preprocessor.py"),
                    ]
                }
            },
            
            "sage-middleware-llm": {
                "target_path": "src/sage/middleware/llm",
                "files": {
                    # LLM 客户端
                    "clients/": [
                        ("clients/openaiclient.py", "clients/openai.py"),
                        ("clients/hf.py", "clients/huggingface.py"),
                        ("clients/generator_model.py", "clients/base.py"),
                    ],
                    # 嵌入方法
                    "embedding/": [
                        ("embedding_methods/", "embedding/"),  # 整个目录
                    ],
                    # 状态持久化
                    "persistence/": [
                        ("state_persistence.py", "persistence/state.py"),
                    ]
                }
            }
        }

    def create_package_structure(self, package_name: str) -> Path:
        """创建新包的目录结构"""
        print(f"🏗️  创建包结构: {package_name}")
        
        package_dir = self.base_dir / package_name
        package_dir.mkdir(exist_ok=True)
        
        # 创建基本目录结构
        (package_dir / "src").mkdir(exist_ok=True)
        (package_dir / "tests").mkdir(exist_ok=True)
        
        target_path = package_dir / self.migration_map[package_name]["target_path"]
        target_path.mkdir(parents=True, exist_ok=True)
        
        return package_dir

    def create_pyproject_toml(self, package_name: str, package_dir: Path):
        """创建 pyproject.toml 文件"""
        print(f"📝 创建 {package_name}/pyproject.toml")
        
        # 基础配置模板
        base_config = {
            "sage-kernel-utils": {
                "description": "SAGE Framework - 内核基础工具",
                "dependencies": [
                    "pyyaml>=6.0.2",
                    "python-dotenv>=1.1.0",
                ]
            },
            "sage-kernel-runtime-extended": {
                "description": "SAGE Framework - 内核运行时扩展",
                "dependencies": [
                    "sage-kernel-utils",
                    "dill>=0.3.8",
                    "ray>=2.0.0",
                ]
            },
            "sage-middleware-llm": {
                "description": "SAGE Framework - LLM 中间件服务",
                "dependencies": [
                    "sage-kernel-utils",
                    "openai",
                    "transformers>=4.45.2",
                    "sentence-transformers>=3.1.1",
                    "huggingface-hub>=0.22.2",
                ]
            }
        }
        
        config = base_config[package_name]
        
        pyproject_content = f'''[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{package_name}"
version = "1.0.0"
description = "{config['description']}"
readme = "README.md"
requires-python = ">=3.10"
license = {{text = "MIT"}}
authors = [
    {{name = "IntelliStream Team", email = "sage@intellistream.cc"}},
]
keywords = ["rag", "llm", "dataflow", "reasoning", "framework"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Topic :: Software Development :: Libraries :: Python Modules",
]

dependencies = {config['dependencies']}

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "mypy>=1.0.0",
    "ruff>=0.1.0",
]

[project.urls]
Homepage = "https://github.com/intellistream/SAGE"
Repository = "https://github.com/intellistream/SAGE.git"
Documentation = "https://sage-docs.intellistream.cc"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
"*" = ["py.typed"]

# pytest配置
[tool.pytest.ini_options]
testpaths = ["tests", "src"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "--verbose",
    "-ra",
]
markers = [
    "slow: marks tests as slow (deselect with '-m \\"not slow\\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]

# Black代码格式化
[tool.black]
line-length = 88
target-version = ['py311']
include = '\\.pyi?$'

# Ruff linting
[tool.ruff]
target-version = "py311"
line-length = 88
select = ["E", "W", "F", "I", "B", "C4", "UP"]
ignore = ["E501", "B008", "C901"]

[tool.ruff.per-file-ignores]
"__init__.py" = ["F401"]
"tests/**/*" = ["PLR2004", "S101", "TID252"]

# MyPy类型检查
[tool.mypy]
python_version = "3.11"
check_untyped_defs = true
disallow_any_generics = true
disallow_incomplete_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
'''
        
        with open(package_dir / "pyproject.toml", "w", encoding="utf-8") as f:
            f.write(pyproject_content)

    def create_readme(self, package_name: str, package_dir: Path):
        """创建 README.md 文件"""
        print(f"📝 创建 {package_name}/README.md")
        
        readme_templates = {
            "sage-kernel-utils": """# SAGE Kernel Utils

> 🔧 SAGE 框架的内核基础工具包

## 功能特性

- **配置管理**: 统一的配置加载和管理
- **日志系统**: 结构化的日志处理
- **系统工具**: 环境、进程、网络基础工具
- **基础序列化**: 核心序列化功能

## 快速开始

```python
from sage.kernel.utils.config import ConfigManager
from sage.kernel.utils.logging import get_logger

# 配置管理
config = ConfigManager()
config.load_from_file("config.yaml")

# 日志系统
logger = get_logger(__name__)
logger.info("内核工具包已加载")
```

这是SAGE框架的基础工具包，为其他内核组件提供核心功能支持。
""",
            
            "sage-kernel-runtime-extended": """# SAGE Kernel Runtime Extended

> ⚡ SAGE 框架的内核运行时扩展包

## 功能特性

- **分布式支持**: Ray集成和分布式处理
- **序列化引擎**: 高级对象序列化和传输
- **通信框架**: Actor模型和网络通信

## 快速开始

```python
from sage.kernel.runtime.distributed import RayManager
from sage.kernel.runtime.communication import ActorWrapper

# 分布式处理
ray_manager = RayManager()
ray_manager.initialize_cluster()

# Actor通信
actor = ActorWrapper()
actor.start()
```

这是SAGE框架的运行时扩展，提供高级执行和通信能力。
""",
            
            "sage-middleware-llm": """# SAGE Middleware LLM

> 🤖 SAGE 框架的 LLM 中间件服务包

## 功能特性

- **LLM 客户端**: OpenAI、HuggingFace 等模型接入
- **嵌入服务**: 文本嵌入和向量化
- **状态管理**: 模型状态持久化
- **缓存系统**: 智能缓存和优化

## 快速开始

```python
from sage.middleware.llm.clients import OpenAIClient
from sage.middleware.llm.embedding import EmbeddingService

# LLM 客户端
client = OpenAIClient()
response = client.generate("Hello, world!")

# 嵌入服务
embedding = EmbeddingService()
vectors = embedding.embed_texts(["text1", "text2"])
```

这是SAGE框架的LLM中间件，提供AI模型集成和服务。
"""
        }
        
        with open(package_dir / "README.md", "w", encoding="utf-8") as f:
            f.write(readme_templates[package_name])

    def migrate_files(self, package_name: str, package_dir: Path):
        """迁移文件到新包"""
        print(f"📦 迁移文件到 {package_name}")
        
        target_base = package_dir / self.migration_map[package_name]["target_path"]
        files_config = self.migration_map[package_name]["files"]
        
        for category, file_mappings in files_config.items():
            category_dir = target_base / category
            category_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建 __init__.py
            (category_dir / "__init__.py").touch()
            
            for source_path, target_path in file_mappings:
                source_file = self.utils_dir / source_path
                target_file = target_base / target_path
                
                if source_file.exists():
                    # 确保目标目录存在
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    if source_file.is_dir():
                        # 复制整个目录
                        if target_file.exists():
                            shutil.rmtree(target_file)
                        shutil.copytree(source_file, target_file)
                        print(f"  📁 {source_path} → {target_path}")
                    else:
                        # 复制单个文件
                        shutil.copy2(source_file, target_file)
                        print(f"  📄 {source_path} → {target_path}")
                else:
                    print(f"  ⚠️  源文件不存在: {source_path}")

    def move_tests(self, package_name: str, package_dir: Path):
        """迁移相关测试文件"""
        print(f"🧪 迁移测试文件到 {package_name}")
        
        utils_tests_dir = self.utils_dir / "tests"
        package_tests_dir = package_dir / "tests"
        
        if not utils_tests_dir.exists():
            print("  ℹ️  没有找到测试文件")
            return
        
        # 根据包名决定迁移哪些测试
        test_patterns = {
            "sage-kernel-utils": ["test_config*", "test_logging*", "test_system*"],
            "sage-kernel-runtime-extended": ["test_ray*", "test_actor*", "test_serialization*"],
            "sage-middleware-llm": ["test_client*", "test_embedding*", "test_state*"]
        }
        
        if package_name in test_patterns:
            for pattern in test_patterns[package_name]:
                for test_file in utils_tests_dir.glob(pattern):
                    target_file = package_tests_dir / test_file.name
                    shutil.copy2(test_file, target_file)
                    print(f"  🧪 {test_file.name} → tests/")

    def create_init_files(self, package_name: str, package_dir: Path):
        """创建 __init__.py 文件"""
        print(f"📝 创建 {package_name} 的 __init__.py 文件")
        
        target_path = package_dir / self.migration_map[package_name]["target_path"]
        
        # 创建各级 __init__.py
        current = package_dir / "src"
        for part in self.migration_map[package_name]["target_path"].split("/")[1:]:
            current = current / part
            current.mkdir(exist_ok=True)
            
            init_file = current / "__init__.py"
            if not init_file.exists():
                with open(init_file, "w", encoding="utf-8") as f:
                    f.write(f'"""\\n{part.title()} module for SAGE framework\\n"""\\n\\n__version__ = "1.0.0"\\n')

    def update_imports(self, package_name: str, package_dir: Path):
        """更新导入路径"""
        print(f"🔄 更新 {package_name} 中的导入路径")
        
        # 定义导入路径映射
        import_mappings = {
            "from sage.utils.": f"from sage.{package_name.replace('-', '.')}.".replace("..", "."),
            "import sage.utils.": f"import sage.{package_name.replace('-', '.')}.".replace("..", "."),
        }
        
        # 遍历所有Python文件并更新导入
        for py_file in package_dir.glob("**/*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                modified = False
                for old_import, new_import in import_mappings.items():
                    if old_import in content:
                        content = content.replace(old_import, new_import)
                        modified = True
                
                if modified:
                    with open(py_file, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"  🔄 更新导入: {py_file.relative_to(package_dir)}")
                    
            except Exception as e:
                print(f"  ⚠️  无法更新 {py_file}: {e}")

    def run_refactor(self):
        """执行完整的重构过程"""
        print("🚀 开始 SAGE Utils 重构...")
        
        if not self.utils_dir.exists():
            print("❌ sage-utils 目录不存在，重构终止")
            return
        
        # 按顺序处理每个包
        for package_name in self.migration_map.keys():
            print(f"\\n{'='*60}")
            print(f"🏗️  处理包: {package_name}")
            print(f"{'='*60}")
            
            try:
                # 1. 创建包结构
                package_dir = self.create_package_structure(package_name)
                
                # 2. 创建配置文件
                self.create_pyproject_toml(package_name, package_dir)
                self.create_readme(package_name, package_dir)
                
                # 3. 迁移文件
                self.migrate_files(package_name, package_dir)
                
                # 4. 迁移测试
                self.move_tests(package_name, package_dir)
                
                # 5. 创建 __init__.py 文件
                self.create_init_files(package_name, package_dir)
                
                # 6. 更新导入路径
                self.update_imports(package_name, package_dir)
                
                print(f"✅ {package_name} 创建完成!")
                
            except Exception as e:
                print(f"❌ 处理 {package_name} 时出错: {e}")
                continue
        
        print(f"\\n{'='*60}")
        print("🎉 SAGE Utils 重构完成!")
        print("✅ sage-utils → sage-kernel-utils + sage-kernel-runtime-extended + sage-middleware-llm")
        print(f"{'='*60}")
        
        print("\\n📋 下一步:")
        print("1. 安装新包: pip install -e packages/sage-kernel-utils")
        print("2. 安装新包: pip install -e packages/sage-kernel-runtime-extended") 
        print("3. 安装新包: pip install -e packages/sage-middleware-llm")
        print("4. 更新其他包的依赖关系")
        print("5. 运行测试验证功能完整性")

def main():
    refactor = UtilsRefactor()
    refactor.run_refactor()

if __name__ == "__main__":
    main()
