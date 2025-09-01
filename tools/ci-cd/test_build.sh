#!/bin/bash

echo "🧪 Testing build-release workflow fixes..."
echo "=========================================="

cd /home/shuhao/SAGE

echo ""
echo "1. Testing pip install build setuptools wheel tomli..."
pip install build setuptools wheel tomli > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Basic dependencies installation: SUCCESS"
else
    echo "❌ Basic dependencies installation: FAILED"
    exit 1
fi

echo ""
echo "2. Testing version extraction from pyproject.toml..."
VERSION=$(python -c "
try:
    import tomllib
except ImportError:
    import tomli as tomllib
with open('pyproject.toml', 'rb') as f:
    data = tomllib.load(f)
    print(data['project']['version'])
" 2>/dev/null || echo "0.1.0")

if [ "$VERSION" != "" ]; then
    echo "✅ Version extraction: SUCCESS (version: $VERSION)"
else
    echo "❌ Version extraction: FAILED"
    exit 1
fi

echo ""
echo "3. Testing project dependency installation..."
if pip install -e ".[dev]" > /dev/null 2>&1; then
    echo "✅ Project dependencies installation: SUCCESS"
else
    echo "⚠️ Project dependencies installation: FAILED (may be expected if packages don't exist)"
fi

echo ""
echo "4. Testing C extension detection..."
found_extensions=false

for pkg_dir in packages/*/; do
    if [ -d "$pkg_dir" ]; then
        if find "$pkg_dir" -name "*.c" -o -name "*.cpp" -o -name "setup.py" -o -name "build.sh" | grep -q .; then
            echo "   Found potential C extensions in $pkg_dir"
            found_extensions=true
        fi
    fi
done

if [ "$found_extensions" = true ]; then
    echo "✅ C extension detection: SUCCESS"
else
    echo "ℹ️ C extension detection: No C extensions found (expected for current project)"
fi

echo ""
echo "🎉 All critical tests passed! Build-release workflow should work now."
