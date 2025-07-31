#!/bin/bash
set -e

echo "Building SAGE release wheel with C/C++ extensions..."

# 清理之前的构建
echo "Cleaning previous builds..."
find sage -name "*.so" ! -path "*/mmap_queue/*" -delete
# 注意：不删除sage_ext下的.so文件，因为那些是通过build.sh生成的
rm -rf build dist *.egg-info

# 构建扩展 (in-place)
echo "Building extensions in-place..."
python release_build.py build_ext --inplace

# 删除 Cython 生成的 .py 文件 (保留 __init__.py)
echo "Cleaning up Cython generated files..."
if [ -f cythonized_files.txt ]; then
    xargs -d '\n' rm < <(grep -v "__init__.py" cythonized_files.txt)
fi

# 构建 wheel
echo "Building wheel..."
python release_build.py bdist_wheel

echo "✓ Build completed successfully!"
echo "Generated wheel files:"
ls -la dist/*.whl

echo ""
echo "📦 Wheel contents preview:"
unzip -l dist/*.whl | grep -E "\.(so|py)$" | head -20
