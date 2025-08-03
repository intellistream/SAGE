# SAGE架构重构 - 代码结构迁移方案

## 📋 概述

本文档详细描述了将当前SAGE monorepo重构为Git Submodules架构的具体代码迁移步骤。迁移将分为4个阶段进行，确保零停机时间和完整的向后兼容性。

**相关文档**:
- [架构改进总体方案](./ARCHITECTURE_IMPROVEMENT_ISSUE.md)
- [Python Namespace Packages实现](./NAMESPACE_PACKAGES_IMPLEMENTATION.md)

## 🎯 迁移目标

### 当前结构 (monorepo)
```
api-rework/
├── sage/                    # Python核心框架
│   ├── core/               # 核心API和环境
│   ├── runtime/            # 运行时系统
│   ├── lib/                # 函数库 (RAG组件)
│   ├── service/            # 服务模块
│   ├── utils/              # 工具模块
│   ├── jobmanager/         # 作业管理
│   ├── cli/                # 命令行工具
│   └── plugins/            # 插件系统
├── sage_ext/               # C++扩展
│   ├── sage_queue/         # 内存映射队列
│   └── sage_db/            # 向量数据库
├── frontend/               # Web界面
│   ├── dashboard/          # Angular前端
│   ├── sage_server/        # FastAPI后端
│   └── operators/          # 操作符配置
├── app/                    # 示例应用
├── config/                 # 配置文件
├── data/                   # 测试数据
├── docs/                   # 文档
├── installation/           # 安装脚本
└── scripts/                # 构建脚本
```

### 目标结构 (Git Submodules)
```
SAGE/ (主仓库)
├── README.md               # 生态系统总览
├── .gitmodules             # Submodule配置
├── docker-compose.yml      # 统一服务编排
├── scripts/                # 统一开发工具
│   ├── setup-dev.sh       # 开发环境配置
│   ├── build-all.sh       # 构建所有组件
│   ├── test-integration.sh # 集成测试
│   └── release.sh          # 统一发布
├── docs/                   # 生态系统文档
├── examples/               # 跨组件示例
└── 子项目:
    ├── sage-core/          # Python核心 (submodule)
    ├── sage-extensions/    # C++扩展 (submodule)
    └── sage-dashboard/     # Web界面 (submodule)
```

## 📅 迁移计划

### Phase 1: 环境准备与仓库创建 (第1-2周)

#### 1.1 创建新的GitHub仓库
```bash
# 在GitHub上创建以下仓库:
# - intellistream/SAGE (主仓库)
# - intellistream/sage-core
# - intellistream/sage-extensions  
# - intellistream/sage-dashboard
```

#### 1.2 设置开发分支策略
```bash
# 每个仓库的分支结构:
# - main: 稳定版本
# - develop: 开发版本
# - feature/*: 功能分支
# - hotfix/*: 热修复分支
```

### Phase 2: sage-core 项目迁移 (第3-4周)

#### 2.1 创建sage-core项目结构
```bash
sage-core/
├── pyproject.toml          # 项目配置
├── README.md               # 核心模块文档
├── .gitignore              # 忽略文件
├── .github/
│   └── workflows/          # CI/CD配置
│       ├── test.yml
│       ├── build.yml
│       └── release.yml
├── src/
│   └── sage/               # PEP 420 namespace package
│       ├── __init__.py     # 模块发现和初始化
│       ├── core/           # 从 sage/core/ 迁移
│       ├── runtime/        # 从 sage/runtime/ 迁移
│       ├── lib/            # 从 sage/lib/ 迁移
│       ├── service/        # 从 sage/service/ 迁移
│       ├── utils/          # 从 sage/utils/ 迁移
│       ├── jobmanager/     # 从 sage/jobmanager/ 迁移
│       ├── cli/            # 从 sage/cli/ 迁移
│       └── plugins/        # 从 sage/plugins/ 迁移
├── tests/                  # 单元测试
│   ├── test_core/
│   ├── test_runtime/
│   └── ...
├── docs/                   # 核心模块文档
└── examples/               # 核心功能示例
```

#### 2.2 迁移核心代码
```bash
# 步骤1: 克隆现有代码
git clone https://github.com/intellistream/api-rework.git temp-migration
cd temp-migration

# 步骤2: 使用git filter-branch提取sage/目录的历史
git filter-branch --prune-empty --subdirectory-filter sage -- --all

# 步骤3: 推送到新的sage-core仓库
git remote add sage-core https://github.com/intellistream/sage-core.git
git push sage-core --all
```

#### 2.3 重构为namespace package结构
需要创建以下关键文件:

**src/sage/__init__.py**:
```python
"""
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
```

**pyproject.toml**:
```toml
[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "sage-core"
version = "1.0.0"
description = "SAGE Framework - Core Python Implementation"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [
    {name = "IntelliStream Team", email = "sage@intellistream.cc"},
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
# 性能增强 - C++扩展
performance = ["sage-extensions>=1.0.0"]

# Web界面
dashboard = ["sage-dashboard>=1.0.0"]

# 完整功能
full = ["sage-extensions>=1.0.0", "sage-dashboard>=1.0.0"]

# 开发依赖
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
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
include = ["sage*"]

# 测试配置
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--cov=sage",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--strict-markers",
]

# 代码格式配置
[tool.black]
line-length = 88
target-version = ["py311"]
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
multi_line_output = 3
```

#### 2.4 智能组件发现机制
在`src/sage/runtime/queue/__init__.py`中实现自动fallback:

```python
"""
队列管理 - 支持自动fallback的统一接口
"""
import logging
from typing import Optional, List
from .base_queue_descriptor import BaseQueueDescriptor

logger = logging.getLogger(__name__)

def create_queue(queue_type: str = "auto", **kwargs) -> BaseQueueDescriptor:
    """
    创建队列的统一工厂函数
    
    自动检测可用的实现，优雅降级：
    sage_queue (C++扩展) -> python_queue (Python实现)
    
    Args:
        queue_type: 队列类型 ("auto", "sage_queue", "python_queue")
        **kwargs: 队列参数
    
    Returns:
        队列描述符实例
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
```

### Phase 3: sage-extensions 项目迁移 (第5-6周)

#### 3.1 创建sage-extensions项目结构
```bash
sage-extensions/
├── pyproject.toml          # C++构建配置
├── setup.py                # 构建脚本
├── CMakeLists.txt          # 跨平台C++构建
├── README.md               # 扩展文档
├── .gitignore
├── .github/
│   └── workflows/          # CI/CD for C++
│       ├── build-linux.yml
│       ├── build-windows.yml
│       ├── build-macos.yml
│       └── release.yml
├── src/
│   └── sage/               # namespace package
│       └── extensions/     # 扩展模块
│           ├── __init__.py
│           ├── sage_queue/
│           │   ├── __init__.py
│           │   ├── core.cpp
│           │   ├── bindings.cpp
│           │   └── include/
│           └── sage_db/
│               ├── __init__.py
│               ├── core.cpp
│               ├── bindings.cpp
│               └── include/
├── tests/                  # C++扩展测试
├── benchmarks/             # 性能基准测试
├── build_scripts/          # 平台特定构建脚本
│   ├── build_linux.sh
│   ├── build_windows.bat
│   └── build_macos.sh
└── docs/                   # C++扩展文档
```

#### 3.2 迁移C++扩展代码
```bash
# 从sage_ext/迁移到新结构
# sage_ext/sage_queue/ -> src/sage/extensions/sage_queue/
# sage_ext/sage_db/ -> src/sage/extensions/sage_db/
```

#### 3.3 统一的扩展接口
**src/sage/extensions/__init__.py**:
```python
"""
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
```

#### 3.4 pyproject.toml配置
```toml
[build-system]
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
description = "SAGE Framework - High-Performance C++ Extensions"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [
    {name = "IntelliStream Team", email = "sage@intellistream.cc"},
]
keywords = ["rag", "llm", "dataflow", "high-performance", "cpp"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: C++",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]

dependencies = [
    "sage-core>=1.0.0",
    "numpy>=1.21.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "cmake>=3.18",
    "ninja",
]

[project.urls]
Homepage = "https://github.com/intellistream/sage-extensions"
Repository = "https://github.com/intellistream/sage-extensions.git"

[tool.setuptools]
package-dir = {"" = "src"}
include-package-data = true

[tool.setuptools.packages.find]
where = ["src"]
include = ["sage*"]

[tool.setuptools.package-data]
"sage.extensions" = ["*.so", "*.pyd", "*.dll"]
```

### Phase 4: sage-dashboard 项目迁移 (第7-8周)

#### 4.1 创建sage-dashboard项目结构
```bash
sage-dashboard/
├── README.md               # Dashboard文档
├── docker-compose.yml      # 服务编排
├── .gitignore
├── .github/
│   └── workflows/          # CI/CD for Web
│       ├── frontend-ci.yml
│       ├── backend-ci.yml
│       └── docker-build.yml
├── frontend/               # Angular前端
│   ├── package.json
│   ├── angular.json
│   ├── tsconfig.json
│   ├── src/
│   └── dist/
├── backend/                # FastAPI后端
│   ├── pyproject.toml
│   ├── src/
│   │   └── sage/
│   │       └── dashboard/
│   │           ├── __init__.py
│   │           ├── client.py
│   │           ├── server/
│   │           └── api/
│   ├── tests/
│   └── docs/
├── docker/                 # 容器化配置
│   ├── Dockerfile.frontend
│   ├── Dockerfile.backend
│   └── nginx.conf
└── k8s/                    # Kubernetes部署
    ├── namespace.yaml
    ├── frontend-deployment.yaml
    ├── backend-deployment.yaml
    └── service.yaml
```

#### 4.2 迁移Web组件
```bash
# 迁移frontend/dashboard/ -> frontend/
# 迁移frontend/sage_server/ -> backend/src/sage/dashboard/server/
# 迁移frontend/operators/ -> backend/src/sage/dashboard/operators/
```

#### 4.3 Dashboard客户端API
**backend/src/sage/dashboard/__init__.py**:
```python
"""
SAGE Dashboard - Web界面和API客户端
"""
__version__ = "1.0.0"

from .client import DashboardClient
from .server.main import create_app

__all__ = ["DashboardClient", "create_app"]
```

**backend/src/sage/dashboard/client.py**:
```python
"""
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
```

### Phase 5: 主仓库创建与集成 (第9-10周)

#### 5.1 创建主仓库(SAGE)结构
```bash
SAGE/
├── README.md               # 生态系统总览
├── LICENSE                 # 许可证
├── .gitignore             
├── .gitmodules             # Submodule配置
├── VERSION_MATRIX.json     # 兼容性矩阵
├── docker-compose.yml      # 统一服务编排
├── .github/
│   └── workflows/          # 集成CI/CD
│       ├── integration.yml
│       ├── release.yml
│       └── submodule-update.yml
├── scripts/                # 统一开发工具
│   ├── setup-dev.sh       # 开发环境配置
│   ├── build-all.sh       # 构建所有组件
│   ├── test-integration.sh # 集成测试
│   ├── release.sh          # 统一发布
│   ├── update-submodules.sh # 更新子模块
│   └── doctor.sh           # 环境诊断
├── docs/                   # 生态系统文档
│   ├── architecture.md
│   ├── installation.md
│   ├── development.md
│   └── deployment.md
├── examples/               # 跨组件示例
│   ├── basic-rag/
│   ├── high-performance/
│   └── full-stack/
└── 子项目 (Git Submodules):
    ├── sage-core/          # Python核心
    ├── sage-extensions/    # C++扩展
    └── sage-dashboard/     # Web界面
```

#### 5.2 配置Git Submodules
**.gitmodules**:
```ini
[submodule "sage-core"]
    path = sage-core
    url = https://github.com/intellistream/sage-core.git
    branch = main

[submodule "sage-extensions"]
    path = sage-extensions
    url = https://github.com/intellistream/sage-extensions.git
    branch = main

[submodule "sage-dashboard"]
    path = sage-dashboard
    url = https://github.com/intellistream/sage-dashboard.git
    branch = main
```

#### 5.3 版本兼容性管理
**VERSION_MATRIX.json**:
```json
{
  "sage-ecosystem": "1.0.0",
  "components": {
    "sage-core": ">=1.0.0,<2.0.0",
    "sage-extensions": ">=1.0.0,<2.0.0", 
    "sage-dashboard": ">=1.0.0,<2.0.0"
  },
  "tested_combinations": [
    {
      "core": "1.0.0",
      "extensions": "1.0.0",
      "dashboard": "1.0.0",
      "tested_date": "2025-01-15",
      "python_versions": ["3.11", "3.12"],
      "platforms": ["linux", "macos", "windows"]
    }
  ],
  "compatibility_notes": {
    "sage-extensions": "Requires C++ compiler and CMake 3.18+",
    "sage-dashboard": "Requires Node.js 18+ for frontend development"
  }
}
```

#### 5.4 统一开发脚本
**scripts/setup-dev.sh**:
```bash
#!/bin/bash
set -e

echo "🚀 设置SAGE完整开发环境..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查Git是否可用
if ! command -v git &> /dev/null; then
    print_error "Git未安装，请先安装Git"
    exit 1
fi

# 初始化所有submodules
print_info "初始化Git submodules..."
git submodule update --init --recursive
print_success "Submodules初始化完成"

# 检查Python环境
print_info "检查Python环境..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3未安装，请先安装Python 3.11+"
    exit 1
fi

python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
print_info "Python版本: $python_version"

if [[ $(echo "$python_version >= 3.11" | bc -l) -ne 1 ]]; then
    print_error "需要Python 3.11+，当前版本: $python_version"
    exit 1
fi

# 配置Python核心环境
print_info "配置sage-core环境..."
cd sage-core
if [[ -f "pyproject.toml" ]]; then
    pip install -e ".[dev]"
    print_success "sage-core安装完成"
else
    print_warning "sage-core/pyproject.toml不存在，跳过"
fi
cd ..

# 配置C++扩展环境 (可选)
print_info "检查C++扩展环境..."
if command -v gcc &> /dev/null && command -v cmake &> /dev/null; then
    print_info "检测到C++编译环境，配置sage-extensions..."
    cd sage-extensions
    if [[ -f "pyproject.toml" ]]; then
        pip install -e ".[dev]"
        print_success "sage-extensions安装完成"
    else
        print_warning "sage-extensions/pyproject.toml不存在，跳过"
    fi
    cd ..
else
    print_warning "跳过C++扩展 (未检测到gcc或cmake)"
    print_info "如需C++扩展，请安装: gcc g++ cmake make"
fi

# 配置前端环境 (可选)
print_info "检查前端环境..."
if command -v node &> /dev/null; then
    node_version=$(node --version | sed 's/v//')
    print_info "Node.js版本: $node_version"
    
    cd sage-dashboard/frontend
    if [[ -f "package.json" ]]; then
        npm install
        print_success "前端依赖安装完成"
    else
        print_warning "sage-dashboard/frontend/package.json不存在，跳过"
    fi
    cd ../..
    
    # 配置后端环境
    cd sage-dashboard/backend
    if [[ -f "pyproject.toml" ]]; then
        pip install -e ".[dev]"
        print_success "Dashboard后端安装完成"
    else
        print_warning "sage-dashboard/backend/pyproject.toml不存在，跳过"
    fi
    cd ../..
else
    print_warning "跳过Dashboard (未检测到Node.js)"
    print_info "如需Web界面，请安装Node.js 18+"
fi

# 创建开发环境信息文件
cat > .dev-env-info << EOF
# SAGE开发环境信息
生成时间: $(date)
Python版本: $python_version
Node.js版本: $(node --version 2>/dev/null || echo "未安装")
Git版本: $(git --version)

# 可用组件
$(python3 -c "
try:
    import sage
    print(f'SAGE Core: ✅ v{sage.__version__}')
    extensions = sage.check_extensions()
    if extensions.get('extensions', {}).get('available'):
        print(f'SAGE Extensions: ✅ v{extensions[\"extensions\"][\"version\"]}')
    else:
        print('SAGE Extensions: ❌ 不可用')
    if extensions.get('dashboard', {}).get('available'):
        print(f'SAGE Dashboard: ✅ v{extensions[\"dashboard\"][\"version\"]}')
    else:
        print('SAGE Dashboard: ❌ 不可用')
except ImportError:
    print('SAGE Core: ❌ 导入失败')
" 2>/dev/null || echo "SAGE导入失败")
EOF

print_success "开发环境配置完成！"
echo
print_info "环境信息已保存到 .dev-env-info"
print_info "运行以下命令验证安装:"
echo "  ./scripts/test-integration.sh  # 运行集成测试"
echo "  python3 examples/basic-rag/main.py  # 运行示例"
echo "  sage doctor  # 系统诊断"
```

#### 5.5 集成测试脚本
**scripts/test-integration.sh**:
```bash
#!/bin/bash
set -e

echo "🧪 运行SAGE生态系统集成测试..."

# 基础功能测试
echo "📋 测试1: 基础模块导入"
python3 -c "
import sage
print(f'✅ SAGE Core v{sage.__version__} 导入成功')
available = sage.get_available_modules()
print(f'✅ 可用模块: {available}')
extensions = sage.check_extensions()
print(f'✅ 扩展状态: {extensions}')
"

# 队列系统测试
echo "📋 测试2: 队列系统fallback机制"
python3 -c "
from sage.runtime.queue import create_queue, get_available_queue_types
print(f'✅ 可用队列类型: {get_available_queue_types()}')
queue = create_queue('auto')
print(f'✅ 创建队列成功: {queue}')
"

# 扩展可用性测试
echo "📋 测试3: C++扩展可用性"
python3 -c "
try:
    from sage.extensions.sage_queue import SageQueueDescriptor
    print('✅ sage_queue扩展可用')
except ImportError:
    print('⚠️  sage_queue扩展不可用 (使用Python fallback)')

try:
    from sage.extensions.sage_db import SageDB
    print('✅ sage_db扩展可用')
except ImportError:
    print('⚠️  sage_db扩展不可用')
"

# Dashboard连接测试
echo "📋 测试4: Dashboard连接"
python3 -c "
try:
    from sage.dashboard.client import DashboardClient
    client = DashboardClient()
    if client.check_health():
        print('✅ Dashboard服务运行中')
    else:
        print('⚠️  Dashboard服务未运行')
except ImportError:
    print('⚠️  Dashboard客户端不可用')
except Exception as e:
    print(f'⚠️  Dashboard连接失败: {e}')
"

# 简单RAG流水线测试
echo "📋 测试5: 基础RAG流水线"
if [[ -f "examples/basic-rag/test.py" ]]; then
    cd examples/basic-rag
    python3 test.py
    cd ../..
    echo "✅ 基础RAG流水线测试通过"
else
    echo "⚠️  基础RAG测试文件不存在，跳过"
fi

echo "🎉 集成测试完成！"
```

## 🔄 向后兼容性策略

### 临时兼容层
在迁移期间，创建一个兼容层确保现有代码继续工作:

**sage-core/src/sage/compat.py**:
```python
"""
向后兼容层 - 确保现有代码在迁移期间继续工作
"""
import warnings
from typing import Any

def deprecated_import_warning(old_path: str, new_path: str):
    """发出废弃导入警告"""
    warnings.warn(
        f"Importing from '{old_path}' is deprecated. "
        f"Use '{new_path}' instead. "
        f"The old import path will be removed in v2.0.0.",
        DeprecationWarning,
        stacklevel=3
    )

# 为常用导入路径提供兼容性
class CompatibilityModule:
    """兼容性模块代理"""
    
    def __init__(self, old_path: str, new_path: str):
        self.old_path = old_path
        self.new_path = new_path
        self._module = None
    
    def __getattr__(self, name: str) -> Any:
        if self._module is None:
            deprecated_import_warning(self.old_path, self.new_path)
            module_parts = self.new_path.split('.')
            self._module = __import__(self.new_path, fromlist=[module_parts[-1]])
        return getattr(self._module, name)

# 兼容性映射
import sys

# 旧的导入路径 -> 新的导入路径
COMPATIBILITY_MAP = {
    'sage.core.api.local_environment': 'sage.core.api.local_environment',
    'sage.lib.io.source': 'sage.lib.io.source',
    'sage.lib.rag.retriever': 'sage.lib.rag.retriever',
    # 可根据需要添加更多映射
}

# 注册兼容性模块
for old_path, new_path in COMPATIBILITY_MAP.items():
    if old_path not in sys.modules:
        sys.modules[old_path] = CompatibilityModule(old_path, new_path)
```

### 迁移指南生成
创建自动化工具来帮助用户迁移现有代码:

**scripts/migration-helper.py**:
```python
#!/usr/bin/env python3
"""
SAGE迁移助手 - 帮助用户迁移到新的模块化架构
"""
import os
import re
import argparse
from pathlib import Path
from typing import List, Tuple

# 导入路径迁移映射
IMPORT_MIGRATIONS = {
    r'from sage\.core\.api\.local_environment import': 'from sage.core.api.local_environment import',
    r'from sage\.lib\.io\.source import': 'from sage.lib.io.source import',
    r'from sage\.lib\.rag\.retriever import': 'from sage.lib.rag.retriever import',
    # 添加更多迁移规则
}

def scan_python_files(directory: Path) -> List[Path]:
    """扫描目录中的Python文件"""
    python_files = []
    for file_path in directory.rglob("*.py"):
        if not any(part.startswith('.') for part in file_path.parts):
            python_files.append(file_path)
    return python_files

def analyze_file(file_path: Path) -> List[Tuple[int, str, str]]:
    """分析文件中需要迁移的导入语句"""
    issues = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                for old_pattern, new_pattern in IMPORT_MIGRATIONS.items():
                    if re.search(old_pattern, line):
                        issues.append((line_num, line.strip(), new_pattern))
    except Exception as e:
        print(f"警告: 无法读取文件 {file_path}: {e}")
    return issues

def main():
    parser = argparse.ArgumentParser(description="SAGE迁移助手")
    parser.add_argument("directory", help="要扫描的目录路径")
    parser.add_argument("--fix", action="store_true", help="自动修复导入语句")
    args = parser.parse_args()
    
    directory = Path(args.directory)
    if not directory.exists():
        print(f"错误: 目录 {directory} 不存在")
        return 1
    
    print(f"🔍 扫描目录: {directory}")
    python_files = scan_python_files(directory)
    print(f"📋 找到 {len(python_files)} 个Python文件")
    
    total_issues = 0
    for file_path in python_files:
        issues = analyze_file(file_path)
        if issues:
            print(f"\n📄 {file_path.relative_to(directory)}:")
            for line_num, old_line, new_pattern in issues:
                print(f"  行 {line_num}: {old_line}")
                print(f"  建议: 使用新的导入路径")
                total_issues += 1
    
    if total_issues == 0:
        print("✅ 未发现需要迁移的导入语句")
    else:
        print(f"\n📊 总计发现 {total_issues} 个需要注意的导入语句")
        print("💡 大多数导入在当前版本中仍然兼容，但建议更新到新的路径")

if __name__ == "__main__":
    exit(main())
```

## 📋 迁移检查清单

### Phase 1: 环境准备 ✅
- [ ] 创建GitHub仓库 (SAGE, sage-core, sage-extensions, sage-dashboard)
- [ ] 设置分支策略和权限管理
- [ ] 准备CI/CD模板

### Phase 2: sage-core迁移 ✅
- [ ] 创建项目结构和配置文件
- [ ] 迁移核心Python代码
- [ ] 实现namespace package结构
- [ ] 实现动态模块发现机制
- [ ] 创建自动fallback机制
- [ ] 编写单元测试
- [ ] 设置CI/CD流水线
- [ ] 发布第一个版本

### Phase 3: sage-extensions迁移 ✅
- [ ] 创建C++项目结构
- [ ] 迁移sage_queue和sage_db代码
- [ ] 配置跨平台构建系统
- [ ] 实现统一的扩展接口
- [ ] 编写C++扩展测试
- [ ] 设置多平台CI/CD
- [ ] 发布第一个版本

### Phase 4: sage-dashboard迁移 ✅
- [ ] 分离前端和后端项目
- [ ] 迁移Angular前端代码
- [ ] 迁移FastAPI后端代码
- [ ] 实现Dashboard API客户端
- [ ] 配置容器化部署
- [ ] 设置Web技术栈CI/CD
- [ ] 发布第一个版本

### Phase 5: 主仓库集成 ✅
- [ ] 创建主仓库结构
- [ ] 配置Git submodules
- [ ] 创建统一开发脚本
- [ ] 实现版本兼容性管理
- [ ] 编写集成测试
- [ ] 创建生态系统文档
- [ ] 设置集成CI/CD

### Phase 6: 测试与优化 (第11-12周)
- [ ] 全面的集成测试
- [ ] 性能基准测试
- [ ] 用户体验测试
- [ ] 文档完善
- [ ] 迁移工具验证

## 🚀 发布计划

### Beta版本 (第10周)
- 所有组件的基础功能完成
- 基本的集成测试通过
- 开发者预览版本

### Release Candidate (第11周)
- 完整的功能测试
- 性能优化
- 文档完善

### 正式版本1.0.0 (第12周)
- 生产就绪
- 完整的向后兼容性
- 全面的文档和示例

## 📝 风险缓解

### 技术风险
1. **namespace packages兼容性问题**
   - 缓解: 在多个Python版本上测试
   - 备选: 提供传统的`__init__.py`安装选项

2. **C++扩展构建复杂性**
   - 缓解: 提供预编译二进制包
   - 备选: Docker构建环境

3. **Git submodules学习曲线**
   - 缓解: 详细的文档和脚本工具
   - 备选: 提供传统的单仓库分支

### 项目风险
1. **迁移时间过长**
   - 缓解: 分阶段迁移，保持向后兼容
   - 监控: 每周进度评估

2. **用户困惑**
   - 缓解: 清晰的迁移指南和自动化工具
   - 支持: 建立迁移支持渠道

## 🎯 成功指标

1. **技术指标**
   - 所有现有测试用例通过
   - 新架构的集成测试通过
   - 构建和部署时间减少30%+

2. **用户体验指标**
   - 安装成功率提升到98%+
   - 新用户上手时间减少50%+
   - 技术支持请求减少60%+

3. **开发体验指标**
   - 单组件CI时间减少60%+
   - 代码贡献者增加40%+
   - 跨技术栈协作效率提升

---

**下一步行动**:
1. 🏗️ 建立迁移工作组（每个组件1-2名技术负责人）
2. 📅 细化每个阶段的具体时间表和里程碑
3. 🧪 开始Phase 1的原型验证
4. 📢 准备社区沟通计划

这个详细的迁移方案为SAGE项目的架构重构提供了完整的路线图，确保了技术先进性、用户体验和开发效率的全面提升。
