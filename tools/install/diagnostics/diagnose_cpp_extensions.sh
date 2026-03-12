#!/bin/bash
# CI 环境 C++ 扩展诊断脚本
# 用于诊断为什么 .so 文件没有被正确安装


# ============================================================================
# 环境变量安全默认值（防止 set -u 报错）
# ============================================================================
CI="${CI:-}"
GITHUB_ACTIONS="${GITHUB_ACTIONS:-}"
GITLAB_CI="${GITLAB_CI:-}"
JENKINS_URL="${JENKINS_URL:-}"
BUILDKITE="${BUILDKITE:-}"
VIRTUAL_ENV="${VIRTUAL_ENV:-}"
CONDA_DEFAULT_ENV="${CONDA_DEFAULT_ENV:-}"
SAGE_FORCE_CHINA_MIRROR="${SAGE_FORCE_CHINA_MIRROR:-}"
SAGE_DEBUG_OFFSET="${SAGE_DEBUG_OFFSET:-}"
SAGE_CUSTOM_OFFSET="${SAGE_CUSTOM_OFFSET:-}"
LANG="${LANG:-en_US.UTF-8}"
LC_ALL="${LC_ALL:-${LANG}}"
LC_CTYPE="${LC_CTYPE:-${LANG}}"
# ============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

echo "=================================================="
echo "C++ 扩展安装诊断"
echo "=================================================="
echo ""

# 1. 检查独立适配器包安装状态
echo "1. 检查独立适配器包安装状态"
echo "-----------------------------------"
for pkg in isage-vdb isage-flow isage-tsdb; do
    echo "📦 $pkg"
    pip show "$pkg" || echo "未安装"
    echo ""
done
echo ""

# 2. 检查历史子模块残留状态
echo "2. 检查历史子模块残留状态"
echo "-----------------------------------"
cd "$PROJECT_ROOT"

echo "ℹ️  历史文档子模块流程已移除；当前无需检查文档子模块"
echo ""

# 3. 检查适配器分发元数据
echo "3. 检查适配器分发元数据"
echo "-----------------------------------"
python3 << 'PYEOF'
from importlib import metadata

for dist_name in ("isage-vdb", "isage-flow", "isage-tsdb"):
    try:
        version = metadata.version(dist_name)
        print(f"✅ {dist_name}: {version}")
    except metadata.PackageNotFoundError:
        print(f"❌ {dist_name}: 未安装")
PYEOF
echo ""

# 4. 尝试导入主仓核心表面
echo "4. 尝试导入主仓核心表面"
echo "-----------------------------------"
python3 << 'PYEOF'
import sys
import warnings
warnings.filterwarnings('ignore')

try:
    import sage.foundation  # noqa: F401
    import sage.runtime  # noqa: F401
    import sage.stream  # noqa: F401
    import sage.serving  # noqa: F401
    print('✅ sage.foundation')
    print('✅ sage.runtime')
    print('✅ sage.stream')
    print('✅ sage.serving')
except Exception as e:
    print(f'❌ 主仓表面导入失败: {type(e).__name__}: {e}')
    sys.exit(1)
PYEOF
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
