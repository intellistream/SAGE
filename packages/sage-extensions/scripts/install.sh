#!/bin/bash
set -e

echo "🚀 SAGE Extensions 一键安装脚本"
echo "=================================="

# 检查系统类型
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    SYSTEM="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    SYSTEM="macos"
else
    echo "❌ 不支持的操作系统: $OSTYPE"
    exit 1
fi

echo "📋 检测到系统: $SYSTEM"

# 安装系统依赖
echo ""
echo "📦 第一步: 安装系统依赖"
echo "------------------------"

if [[ "$SYSTEM" == "linux" ]]; then
    # 检测 Linux 发行版
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
    else
        DISTRO="unknown"
    fi
    
    echo "检测到发行版: $DISTRO"
    
    if [[ "$DISTRO" == "ubuntu" || "$DISTRO" == "debian" ]]; then
        echo "安装 Ubuntu/Debian 系统依赖..."
        sudo apt-get update -y || echo "⚠ 更新包列表失败"
        
        DEPS=(
            "build-essential"
            "cmake"
            "g++"
            "gcc"
            "pkg-config"
            "libblas-dev"
            "liblapack-dev"
            "libopenblas-dev"
            "python3-dev"
            "python3-pip"
            "git"
        )
        
        for dep in "${DEPS[@]}"; do
            echo "安装 $dep..."
            sudo apt-get install -y "$dep" || echo "⚠ $dep 安装失败"
        done
        
    elif [[ "$DISTRO" == "centos" || "$DISTRO" == "rhel" || "$DISTRO" == "fedora" ]]; then
        echo "安装 CentOS/RHEL/Fedora 系统依赖..."
        
        # 选择包管理器
        if command -v dnf &> /dev/null; then
            PKG_MGR="dnf"
        else
            PKG_MGR="yum"
        fi
        
        DEPS=(
            "gcc-c++"
            "gcc"
            "make"
            "cmake"
            "pkgconfig"
            "blas-devel"
            "lapack-devel"
            "openblas-devel"
            "python3-devel"
            "python3-pip"
            "git"
        )
        
        for dep in "${DEPS[@]}"; do
            echo "安装 $dep..."
            sudo $PKG_MGR install -y "$dep" || echo "⚠ $dep 安装失败"
        done
        
    else
        echo "⚠ 未知的 Linux 发行版，请手动安装以下依赖:"
        echo "- build-essential/gcc-c++"
        echo "- cmake"
        echo "- pkg-config"
        echo "- blas-devel liblapack-dev"
        echo "- python3-dev"
    fi
    
elif [[ "$SYSTEM" == "macos" ]]; then
    echo "安装 macOS 系统依赖..."
    
    # 检查 Homebrew
    if ! command -v brew &> /dev/null; then
        echo "安装 Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    DEPS=(
        "cmake"
        "gcc"
        "pkg-config"
        "openblas"
        "lapack"
        "git"
        "python@3.11"
    )
    
    for dep in "${DEPS[@]}"; do
        echo "安装 $dep..."
        brew install "$dep" || echo "⚠ $dep 安装失败"
    done
fi

echo "✅ 系统依赖安装完成"

# 验证关键工具
echo ""
echo "🔍 第二步: 验证工具安装"
echo "----------------------"

TOOLS=("cmake" "gcc" "g++" "python3" "pip3")
for tool in "${TOOLS[@]}"; do
    if command -v "$tool" &> /dev/null; then
        VERSION=$(command "$tool" --version 2>/dev/null | head -1 || echo "未知版本")
        echo "✅ $tool: $VERSION"
    else
        echo "❌ $tool: 未找到"
    fi
done

# 检查 pkg-config
if command -v pkg-config &> /dev/null; then
    echo "✅ pkg-config: $(pkg-config --version)"
else
    echo "❌ pkg-config: 未找到"
fi

# 安装 Python 依赖
echo ""
echo "🐍 第三步: 安装 Python 依赖"
echo "-----------------------------"

# 升级 pip
python3 -m pip install --upgrade pip

# 安装基础依赖
PYTHON_DEPS=(
    "numpy"
    "pybind11[global]"
    "cmake"
    "ninja"
)

for dep in "${PYTHON_DEPS[@]}"; do
    echo "安装 $dep..."
    python3 -m pip install "$dep" || echo "⚠ $dep 安装失败"
done

# 安装 FAISS
echo "安装 FAISS..."
if command -v conda &> /dev/null; then
    echo "尝试通过 conda 安装 FAISS..."
    conda install -y -c conda-forge faiss-cpu || {
        echo "conda 安装失败，尝试 pip..."
        python3 -m pip install faiss-cpu || echo "⚠ FAISS 安装失败"
    }
else
    echo "尝试通过 pip 安装 FAISS..."
    python3 -m pip install faiss-cpu || echo "⚠ FAISS 安装失败"
fi

echo "✅ Python 依赖安装完成"

# 构建和安装 SAGE Extensions
echo ""
echo "🔧 第四步: 构建和安装 SAGE Extensions"
echo "------------------------------------"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 运行构建脚本
if [ -f "build.py" ]; then
    echo "运行构建脚本..."
    python3 build.py
else
    echo "⚠ 构建脚本不存在，尝试直接安装..."
    python3 -m pip install -e .
fi

# 验证安装
echo ""
echo "🧪 第五步: 验证安装"
echo "------------------"

if [ -f "verify_install.py" ]; then
    echo "运行安装验证..."
    python3 verify_install.py
else
    echo "运行基本验证..."
    python3 -c "
import sys
try:
    import sage.extensions
    print('✅ SAGE Extensions 导入成功')
    
    status = sage.extensions.get_extension_status()
    print(f'扩展状态: {status}')
    
    if sage.extensions.check_extensions():
        print('✅ 所有扩展加载成功!')
        sys.exit(0)
    else:
        print('⚠ 部分扩展加载失败')
        sys.exit(1)
        
except Exception as e:
    print(f'❌ 验证失败: {e}')
    sys.exit(1)
"
fi

echo ""
echo "🎉 SAGE Extensions 安装完成!"
echo "============================"
echo ""
echo "现在可以使用以下命令导入:"
echo "  import sage.extensions"
echo "  from sage.extensions.sage_db import SageDB"
echo ""
echo "如果遇到问题，请查看 INSTALL.md 获取更多帮助。"
