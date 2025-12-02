#!/bin/bash
# 测试脚本 - 验证 benchmark_anns 项目结构 (独立项目)

set -e

echo "=========================================="
echo "Benchmark ANNS - 项目验证 (独立项目)"
echo "=========================================="
echo ""

# 检查目录结构
echo "✓ 检查目录结构..."
dirs=("datasets" "bench" "bench/algorithms" "algorithms_impl" "utils" "runbooks" "tests")
for dir in "${dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✓ $dir/"
    else
        echo "  ✗ $dir/ 缺失"
        exit 1
    fi
done
echo ""

# 检查核心文件
echo "✓ 检查核心文件..."
files=(
    "README.md"
    "requirements.txt"
)
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file 缺失"
    fi
done
echo ""

# 检查模块文件
echo "✓ 检查模块文件..."
module_files=(
    "datasets/__init__.py"
    "bench/__init__.py"
    "bench/worker.py"
    "bench/runner.py"
    "bench/metrics.py"
    "bench/maintenance.py"
    "bench/algorithms/__init__.py"
    "bench/algorithms/base.py"
    "bench/algorithms/registry.py"
    "algorithms_impl/__init__.py"
    "algorithms_impl/candy_wrapper.py"
    "algorithms_impl/faiss_wrapper.py"
    "algorithms_impl/diskann_wrapper.py"
    "algorithms_impl/puck_wrapper.py"
    "algorithms_impl/bindings/PyCANDY.cpp"
    "utils/__init__.py"
)
for file in "${module_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file 缺失"
    fi
done
echo ""

# 检查第三方库源码
echo "✓ 检查第三方库源码..."
thirdparty_dirs=(
    "algorithms_impl/faiss"
    "algorithms_impl/DiskANN"
    "algorithms_impl/puck"
    "algorithms_impl/SPTAG"
    "algorithms_impl/pybind11"
    "algorithms_impl/candy"
)
for dir in "${thirdparty_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✓ $dir/ (源码已复制)"
    else
        echo "  ✗ $dir/ (源码缺失)"
    fi
done
echo ""

# 检查配置文件
echo "✓ 检查配置文件..."
config_files=(
    "runbooks/streaming_simple.yaml"
    "runbooks/streaming_full.yaml"
)
for file in "${config_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ⚠ $file 缺失 (可选)"
    fi
done
echo ""

# 统计文件数量
echo "✓ 文件统计:"
py_count=$(find bench algorithms_impl utils tests -name "*.py" 2>/dev/null | wc -l)
yaml_count=$(find runbooks -name "*.yaml" 2>/dev/null | wc -l)
md_count=$(find . -maxdepth 2 -name "*.md" 2>/dev/null | wc -l)

echo "  Python 文件: $py_count"
echo "  YAML 配置: $yaml_count"
echo "  Markdown 文档: $md_count"
echo ""

# Python 模块导入测试
echo "✓ Python 模块导入测试..."
if command -v python3 &> /dev/null; then
    cd .. && python3 -c "
import sys
sys.path.insert(0, '.')

modules_ok = True
try:
    from benchmark_anns.bench import BenchmarkRunner
    print('  ✓ BenchmarkRunner')
except Exception as e:
    print(f'  ✗ BenchmarkRunner: {e}')
    modules_ok = False

try:
    from benchmark_anns.bench import BenchmarkMetrics
    print('  ✓ BenchmarkMetrics')
except Exception as e:
    print(f'  ✗ BenchmarkMetrics: {e}')
    modules_ok = False

try:
    from benchmark_anns.bench.algorithms import BaseStreamingANN
    print('  ✓ BaseStreamingANN')
except Exception as e:
    print(f'  ✗ BaseStreamingANN: {e}')
    modules_ok = False

try:
    from benchmark_anns.algorithms_impl import candy_wrapper
    print('  ✓ candy_wrapper')
except Exception as e:
    print(f'  ✗ candy_wrapper: {e}')
    modules_ok = False

sys.exit(0 if modules_ok else 1)
" 2>&1 && cd benchmark_anns
else
    echo "  ⚠ Python3 未安装，跳过模块测试"
fi
echo ""

echo "=========================================="
echo "✅ 项目验证完成！"
echo "=========================================="
echo ""
echo "benchmark_anns 是一个独立的流式索引测试框架"
echo ""
echo "下一步:"
echo "  1. 安装依赖: pip install -r requirements.txt"
echo "  2. 编译算法库 (可选): cd algorithms_impl && ./build.sh"
echo "  3. 运行测试: cd tests && python test_streaming.py"
echo "  4. 查看文档: cat README.md"
echo ""
