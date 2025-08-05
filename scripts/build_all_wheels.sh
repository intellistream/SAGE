#!/usr/bin/env bash
# build_all_wheels.sh
# Script to build wheel packages for all projects under packages/, packages/commercial/, and packages/tools/
# 🔧 集成了 outlines_core 和 xformers 构建问题的修复

set -euo pipefail

OUTPUT_DIR="build/wheels"
mkdir -p "$OUTPUT_DIR"

echo "🚀 构建 SAGE Wheels - 已集成构建问题修复..."

# === 构建问题修复 - 开始 ===
echo "🔧 应用构建问题修复..."

# 设置环境变量解决构建问题
export PIP_USE_PEP517=1
export PIP_PREFER_BINARY=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_NO_WARN_CONFLICTS=1

# 导入 Rust 环境（如果存在）
if [ -f ~/.cargo/env ]; then
    source ~/.cargo/env
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# 升级构建工具到最新版本（修复 xformers 警告）
echo "📦 升级构建工具..."
pip install --upgrade pip setuptools wheel build

# 预安装问题包，避免构建时冲突
echo "📦 预安装可能有构建问题的包..."
pip install --prefer-binary --only-binary=:all: \
    "outlines>=1.2.0,<1.3.0" \
    "xformers>=0.0.28" \
    --constraint=../constraints-build.txt 2>/dev/null || {
    
    echo "⚠️  预编译包安装失败，准备源码编译环境..."
    
    # 安装 Rust 构建依赖
    if ! command -v rustc &> /dev/null; then
        echo "📥 安装 Rust 编译器（outlines_core 需要）..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
        source ~/.cargo/env
        export PATH="$HOME/.cargo/bin:$PATH"
        echo "✅ Rust 安装完成"
    fi
    
    # 安装 Rust 和 C++ 构建依赖
    echo "📥 安装构建依赖..."
    pip install --upgrade \
        setuptools-rust \
        maturin \
        "pybind11[global]" \
        cmake
    
    # 设置 Rust 优化标志
    export RUSTFLAGS="-C target-cpu=native"
    
    echo "🔨 从源码构建问题包..."
    pip install --no-binary=outlines "outlines>=1.2.0,<1.3.0" --verbose
    pip install --use-pep517 "xformers>=0.0.28" --verbose
}

echo "✅ 构建问题修复完成"
# === 构建问题修复 - 结束 ===

# Install GNU parallel if not available (for faster builds)
if ! command -v parallel >/dev/null 2>&1; then
  echo "📥 Installing GNU parallel for faster wheel building..."
  if command -v apt >/dev/null 2>&1; then
    sudo apt update && sudo apt install -y parallel
  elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y parallel
  elif command -v brew >/dev/null 2>&1; then
    brew install parallel
  elif command -v conda >/dev/null 2>&1; then
    conda install -y -c conda-forge parallel
  else
    echo "Warning: Could not install GNU parallel, will build sequentially"
  fi
fi

# Ensure build tool is available
if ! python3 -c "import build" &>/dev/null; then
  echo "📥 Installing build package..."
  pip install --upgrade build
fi

# Verify build installation
if ! python3 -c "from build import ProjectBuilder; print('build module working')" &>/dev/null; then
  echo "🔧 Re-installing build with proper dependencies..."
  pip uninstall -y build
  pip install --upgrade build[virtualenv]
fi

# Ensure setuptools-scm is available if needed for build-system.requires
if ! python3 -c "import setuptools_scm" &>/dev/null; then
  echo "📥 Installing setuptools-scm..."
  pip install setuptools-scm
fi

# Install Rust if not available (required for tokenizers and other Rust-based packages)
# Note: Rust installation is now handled in the build fixes section above
if ! command -v rustc &> /dev/null; then
    echo "📥 Installing Rust toolchain for tokenizers compilation..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
    source ~/.cargo/env
    export PATH="$HOME/.cargo/bin:$PATH"
    echo "✅ Rust installed successfully"
else
    echo "✅ Rust is already available"
fi

# Pre-install dependencies to avoid compilation issues during wheel building
echo "📦 Pre-installing common dependencies..."
pip install --upgrade httpx[socks] socksio

# Directories to scan
ROOTS=("packages" "packages/commercial" "packages/tools")

echo "📋 Collecting all project dependencies for download..."
# gather main dependencies from pyproject.toml of each package
TMP_REQS=$(mktemp)
for root in "${ROOTS[@]}"; do
  [ -d "$root" ] || continue
  for TOML in "$root"/*/pyproject.toml; do
    [ -f "$TOML" ] || continue
    python3 -c "
import tomllib
with open('$TOML', 'rb') as f:
    data = tomllib.load(f)
for dep in data.get('project', {}).get('dependencies', []):
    # strip version specifiers
    print(dep.split()[0])
" >> "$TMP_REQS"
  done
done

if [ -s "$TMP_REQS" ]; then
  echo "📥 Downloading dependencies to wheelhouse..."
  pip download --dest "$OUTPUT_DIR" --no-deps -r "$TMP_REQS" || echo "Warning: Some dependencies could not be downloaded"
fi
rm "$TMP_REQS"

# Build wheels with enhanced error handling
build_package() {
  local pkg=$1
  echo "🔨 Building wheel for $pkg"
  
  # 设置构建环境变量（包含修复）
  export PIP_NO_BUILD_ISOLATION=1
  export PIP_DISABLE_PIP_VERSION_CHECK=1
  export PIP_USE_PEP517=1
  
  # 使用约束文件（如果存在）
  local constraint_args=""
  if [ -f "../constraints-build.txt" ]; then
    constraint_args="--constraint ../constraints-build.txt"
  fi
  
  # 构建时应用修复
  (cd "$pkg" && python3 -m build --wheel --no-isolation $constraint_args --outdir "$OLDPWD/$OUTPUT_DIR") 2>&1 | sed "s|^|[$pkg] |"
}

# Collect all packages first
PACKAGES=()
for root in "${ROOTS[@]}"; do
  [ -d "$root" ] || continue
  for pkg in "$root"/*; do
    [ -d "$pkg" ] || continue
    if [ -f "$pkg/pyproject.toml" ] || [ -f "$pkg/setup.py" ]; then
      PACKAGES+=("$pkg")
    fi
  done
done

# Build in parallel (limit to 4 concurrent jobs to avoid overwhelming system)
export -f build_package
export OUTPUT_DIR
export PIP_NO_BUILD_ISOLATION
export PIP_DISABLE_PIP_VERSION_CHECK
export PIP_USE_PEP517

if command -v parallel >/dev/null 2>&1; then
  echo "🔨 Building ${#PACKAGES[@]} packages in parallel..."
  printf '%s\n' "${PACKAGES[@]}" | parallel -j4 build_package
else
  echo "🔨 GNU parallel not found, building sequentially..."
  for pkg in "${PACKAGES[@]}"; do
    build_package "$pkg"
  done
fi

echo "✅ All wheels built and available in $OUTPUT_DIR/"
echo "🎉 构建完成！已应用所有修复补丁。"
