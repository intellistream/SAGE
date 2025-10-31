#!/bin/bash
# CI 环境 C++ 扩展诊断脚本
# 用于诊断为什么 .so 文件没有被正确安装

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "=================================================="
echo "C++ 扩展安装诊断"
echo "=================================================="
echo ""

# 1. 检查 isage-middleware 安装状态
echo "1. 检查 isage-middleware 安装状态"
echo "-----------------------------------"
pip show isage-middleware || echo "未安装"
echo ""

# 2. 检查子模块状态
echo "2. 检查子模块状态"
echo "-----------------------------------"
cd "$PROJECT_ROOT"
for submodule in \
    "packages/sage-middleware/src/sage/middleware/components/sage_db/sageDB" \
    "packages/sage-middleware/src/sage/middleware/components/sage_flow/sageFlow" \
    "packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB"; do

    if [ -d "$submodule" ]; then
        if [ -n "$(ls -A "$submodule" 2>/dev/null)" ]; then
            echo "✅ $submodule (已初始化)"
        else
            echo "⚠️  $submodule (空目录)"
        fi
    else
        echo "❌ $submodule (不存在)"
    fi
done
echo ""

# 3. 检查 .so 文件位置
echo "3. 检查 .so 文件位置"
echo "-----------------------------------"
for ext in sage_flow sage_db sage_tsdb; do
    echo "📦 ${ext}:"

    ext_dir="$PROJECT_ROOT/packages/sage-middleware/src/sage/middleware/components/${ext}"

    # 检查 python 目录中的 .so 文件
    if [ -d "$ext_dir/python" ]; then
        lib_files=$(find "$ext_dir/python" -maxdepth 1 -name "*.so" -type f 2>/dev/null || true)
        if [ -n "$lib_files" ]; then
            echo "$lib_files" | while read -r file; do
                size=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null || echo "?")
                echo "  ✅ $(basename "$file") (${size} bytes)"
            done
        else
            echo "  ❌ python/ 目录中没有 .so 文件"
        fi
    else
        echo "  ❌ python/ 目录不存在"
    fi

    # 检查子模块 python 目录
    submodule_dir=$(find "$ext_dir" -maxdepth 1 -type d \( -iname "sage${ext#sage_}" -o -iname "${ext}" \) 2>/dev/null | head -1 || true)
    if [ -n "$submodule_dir" ] && [ -d "$submodule_dir/python" ]; then
        lib_files=$(find "$submodule_dir/python" -maxdepth 1 -name "*.so" -type f 2>/dev/null || true)
        if [ -n "$lib_files" ]; then
            echo "  子模块 python/ 目录:"
            echo "$lib_files" | while read -r file; do
                size=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null || echo "?")
                echo "    📄 $(basename "$file") (${size} bytes)"
            done
        fi
    fi

    # 检查 build 目录
    if [ -d "$ext_dir/build" ] || [ -d "$PROJECT_ROOT/packages/sage-middleware/build" ]; then
        build_files=$(find "$ext_dir" "$PROJECT_ROOT/packages/sage-middleware/build" -name "lib*.so" -type f 2>/dev/null | grep -i "$ext" || true)
        if [ -n "$build_files" ]; then
            echo "  build/ 目录:"
            echo "$build_files" | head -3 | while read -r file; do
                size=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null || echo "?")
                echo "    📄 $(basename "$file") (${size} bytes)"
            done
        fi
    fi

    echo ""
done

# 4. 尝试导入扩展
echo "4. 尝试导入 Python 扩展"
echo "-----------------------------------"
python3 << 'PYEOF'
import sys
import warnings
warnings.filterwarnings('ignore')

try:
    from sage.middleware.components.extensions_compat import check_extensions_availability
    available = check_extensions_availability()

    for ext, status in available.items():
        symbol = '✅' if status else '❌'
        print(f"{symbol} {ext}")

        if not status:
            # 尝试获取详细错误
            try:
                if ext == 'sage_flow':
                    from sage.middleware.components.sage_flow.python import _sage_flow
                elif ext == 'sage_db':
                    from sage.middleware.components.sage_db.python import _sage_db
                elif ext == 'sage_tsdb':
                    from sage.middleware.components.sage_tsdb.python import _sage_tsdb
            except Exception as e:
                print(f"   错误: {e}")
except Exception as e:
    print(f"❌ 无法检查扩展: {e}")
    import traceback
    traceback.print_exc()
PYEOF

echo ""
echo "=================================================="
echo "诊断完成"
echo "=================================================="
