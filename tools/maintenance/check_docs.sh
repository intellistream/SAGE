#!/bin/bash
# SAGE Documentation Quality Check Script
# This script runs comprehensive documentation quality checks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "======================================================================"
echo "📚 SAGE Documentation Quality Check"
echo "======================================================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

cd "$PROJECT_ROOT"

# 1. Check dev-notes documentation
echo "1️⃣  Checking dev-notes documentation..."
if python tools/devnotes_checker.py --all; then
    echo -e "${GREEN}✅ Dev-notes check passed${NC}"
else
    echo -e "${RED}❌ Dev-notes check failed${NC}"
    exit 1
fi
echo ""

# 2. Check package README quality
echo "2️⃣  Checking package README quality..."
if python tools/package_readme_checker.py --all; then
    echo -e "${GREEN}✅ Package README check passed${NC}"
else
    echo -e "${YELLOW}⚠️  Some packages have low README quality${NC}"
fi
echo ""

# 3. Check for broken links (basic check)
echo "3️⃣  Checking for common documentation issues..."

# Check for placeholder text
echo "   Checking for placeholder text..."
PLACEHOLDERS=$(grep -r "{[A-Z_]*}" docs/ packages/*/README.md 2>/dev/null | grep -v ".git" | grep -v "node_modules" || true)
if [ -z "$PLACEHOLDERS" ]; then
    echo -e "   ${GREEN}✅ No placeholders found${NC}"
else
    echo -e "   ${YELLOW}⚠️  Found placeholder text:${NC}"
    echo "$PLACEHOLDERS" | head -5
fi

# Check for TODO/FIXME in documentation
echo "   Checking for TODO/FIXME markers..."
TODOS=$(grep -r "TODO\|FIXME" docs/ examples/*/README.md packages/*/README.md 2>/dev/null | grep -v ".git" | grep -v "node_modules" | wc -l || true)
echo "   Found $TODOS TODO/FIXME markers"

# Check for very short README files (< 10 lines)
echo "   Checking for short README files..."
SHORT_READMES=$(find packages/ examples/ -name "README.md" -type f -exec sh -c 'lines=$(wc -l < "$1"); if [ "$lines" -lt 10 ]; then echo "$1: $lines lines"; fi' _ {} \; 2>/dev/null | grep -v "pytest_cache\|node_modules\|build\|vendor" || true)
if [ -z "$SHORT_READMES" ]; then
    echo -e "   ${GREEN}✅ No unusually short READMEs${NC}"
else
    echo -e "   ${YELLOW}⚠️  Short README files found:${NC}"
    echo "$SHORT_READMES" | head -5
fi

echo ""

# 4. Statistics
echo "4️⃣  Documentation statistics:"
TOTAL_MD=$(find . -name "*.md" -type f 2>/dev/null | grep -v ".git\|node_modules\|build/_deps\|vendors/vllm\|.sage" | wc -l)
DEV_NOTES=$(find docs/dev-notes -name "*.md" -type f 2>/dev/null | wc -l)
PACKAGE_READMES=$(find packages/ -maxdepth 2 -name "README.md" -type f 2>/dev/null | wc -l)
EXAMPLE_READMES=$(find examples/ -name "README.md" -type f 2>/dev/null | wc -l)

echo "   Total markdown files: $TOTAL_MD"
echo "   Dev-notes documents: $DEV_NOTES"
echo "   Package READMEs: $PACKAGE_READMES"
echo "   Example READMEs: $EXAMPLE_READMES"
echo ""

# 5. Generate report
echo "5️⃣  Generating quality report..."
REPORT_FILE="docs/dev-notes/ci-cd/DOCUMENTATION_CHECK_REPORT_$(date +%Y%m%d).md"

python tools/package_readme_checker.py --all --report --output "$REPORT_FILE"
echo -e "${GREEN}✅ Report generated: $REPORT_FILE${NC}"
echo ""

echo "======================================================================"
echo "📊 Documentation Check Complete"
echo "======================================================================"
echo ""
echo "Summary:"
echo "  - Dev-notes: ✅ Passed"
echo "  - Package READMEs: Check output above"
echo "  - Total docs: $TOTAL_MD files"
echo ""
echo "For detailed results, see:"
echo "  - $REPORT_FILE"
echo ""
