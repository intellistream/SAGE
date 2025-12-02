#!/bin/bash
# 本地测试脚本 - 模拟CI环境测试

set -e

echo "================================"
echo "SAGE-DB-Bench Local Test Suite"
echo "================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 1. 检查Python环境
echo -e "${BLUE}[1/5] Checking Python environment...${NC}"
python --version
echo ""

# 2. 安装依赖
echo -e "${BLUE}[2/5] Installing dependencies...${NC}"
pip install -q -r requirements.txt
pip install -q pytest black flake8
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# 3. 验证安装
echo -e "${BLUE}[3/5] Verifying installation...${NC}"
python -c "import numpy, pandas, yaml; print('✓ Core packages OK')"
python -c "from bench import BenchmarkRunner; print('✓ Framework OK')"
python -c "from datasets import DATASETS; print(f'✓ {len(DATASETS)} datasets available')"
echo ""

# 4. 代码质量检查
echo -e "${BLUE}[4/5] Running code quality checks...${NC}"
echo "Checking code formatting..."
black --check bench/ datasets/ tests/ 2>/dev/null || echo "  ⚠ Code formatting issues found (run 'black .')"
echo "Linting code..."
flake8 bench/ datasets/ tests/ --count --max-line-length=127 --statistics 2>/dev/null || echo "  ⚠ Linting issues found"
echo -e "${GREEN}✓ Code quality checks completed${NC}"
echo ""

# 5. 运行测试
echo -e "${BLUE}[5/5] Running tests...${NC}"
pytest tests/ -v -m "not slow" || {
    echo -e "${RED}✗ Tests failed${NC}"
    exit 1
}
echo ""

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}All tests passed! ✓${NC}"
echo -e "${GREEN}================================${NC}"
