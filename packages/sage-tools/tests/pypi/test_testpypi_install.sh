#!/bin/bash
# TestPyPI安装测试脚本
# 用于验证从TestPyPI安装SAGE的完整流程

set -e  # 遇到错误立即退出

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 TestPyPI安装测试${NC}"
echo "================================"

# 1. 创建测试环境
TEST_ENV="testpypi_test_$$"
echo -e "\n${BLUE}📁 创建测试环境: ${TEST_ENV}${NC}"
python -m venv "${TEST_ENV}"

# 激活环境
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source "${TEST_ENV}/Scripts/activate"
else
    source "${TEST_ENV}/bin/activate"
fi

echo -e "${GREEN}✅ 测试环境创建成功${NC}"

# 2. 升级pip
echo -e "\n${BLUE}📦 升级pip...${NC}"
pip install --upgrade pip --quiet

# 3. 从TestPyPI安装SAGE
echo -e "\n${BLUE}📥 从TestPyPI安装SAGE（包含依赖）...${NC}"
echo -e "${YELLOW}安装命令:${NC}"
echo "pip install --index-url https://test.pypi.org/simple/ \\"
echo "            --extra-index-url https://pypi.org/simple/ \\"
echo "            isage"

pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            isage

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ SAGE安装成功${NC}"
else
    echo -e "${RED}❌ SAGE安装失败${NC}"
    deactivate
    rm -rf "${TEST_ENV}"
    exit 1
fi

# 4. 验证安装
echo -e "\n${BLUE}🔍 验证安装...${NC}"

# 检查版本
echo -e "\n${YELLOW}检查版本:${NC}"
if sage --version; then
    echo -e "${GREEN}✅ sage命令可用${NC}"
else
    echo -e "${RED}❌ sage命令不可用${NC}"
    deactivate
    rm -rf "${TEST_ENV}"
    exit 1
fi

# 测试导入
echo -e "\n${YELLOW}测试核心导入:${NC}"
python -c "
import sage
print(f'✅ SAGE版本: {sage.__version__}')

from sage.core.api.local_environment import LocalEnvironment
print('✅ LocalEnvironment导入成功')

from sage.libs.io_utils.source import FileSource
from sage.libs.io_utils.sink import TerminalSink
print('✅ IO工具导入成功')

from sage.common.utils.logging.custom_logger import CustomLogger
print('✅ 日志工具导入成功')
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 所有导入测试通过${NC}"
else
    echo -e "${RED}❌ 导入测试失败${NC}"
    deactivate
    rm -rf "${TEST_ENV}"
    exit 1
fi

# 5. 测试基本功能
echo -e "\n${YELLOW}测试基本功能:${NC}"
python -c "
from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io_utils.source import FileSource
from sage.libs.io_utils.sink import TerminalSink

# 创建环境
env = LocalEnvironment(
    name='test_env',
    source=FileSource('./test.txt'),
    sink=TerminalSink()
)
print('✅ 环境创建成功')
print(f'   环境名称: {env.name}')
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 基本功能测试通过${NC}"
else
    echo -e "${RED}❌ 基本功能测试失败${NC}"
    deactivate
    rm -rf "${TEST_ENV}"
    exit 1
fi

# 6. 清理
echo -e "\n${BLUE}🧹 清理测试环境...${NC}"
deactivate
rm -rf "${TEST_ENV}"

# 7. 总结
echo -e "\n${GREEN}🎉 TestPyPI安装测试完成！${NC}"
echo "================================"
echo -e "${GREEN}✅ 所有测试通过${NC}"
echo -e "${YELLOW}💡 可以安全发布到正式PyPI${NC}"
