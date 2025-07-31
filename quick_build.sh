#!/bin/bash
# ===============================================================================
# SAGE 快速打包脚本 (简化版)
# ===============================================================================

set -e

echo "🚀 开始构建 SAGE 生产级 wheel 包..."

# 1. 清理
echo "📁 清理构建环境..."
rm -rf build dist *.egg-info temp_build
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# 2. 设置环境
echo "⚙️  设置构建环境..."
mkdir -p ./temp_build
export TMPDIR=$(pwd)/temp_build
export MAX_JOBS=1
export MAKEFLAGS="-j1"

# 3. 构建 C++ 扩展
echo "🔧 构建 C++ 扩展..."
if [ -d "sage_ext/sage_queue" ]; then
    (cd sage_ext/sage_queue && bash build.sh --clean) || echo "⚠️  sage_queue 构建失败"
fi

# 4. 构建 Cython 和 Python 绑定
echo "🐍 构建 Cython 扩展..."
python release_build.py build_ext --inplace

# 5. 清理源码（保留 __init__.py）
echo "🧹 清理 Python 源码..."
if [ -f "cythonized_files.txt" ]; then
    grep -v "__init__.py" cythonized_files.txt | xargs rm -f 2>/dev/null || true
    echo "✓ 已删除 Python 源文件，保留 __init__.py"
fi

# 6. 构建 wheel
echo "📦 构建 wheel 包..."
python release_build.py bdist_wheel

# 7. 显示结果
echo ""
echo "🎉 构建完成！"
ls -lh dist/*.whl
echo ""
echo "📋 验证命令:"
echo "  pip install dist/*.whl"
echo "  python -c 'import sage; print(sage.__version__)'"
