#!/bin/bash
# SAGE Documentation Quality Check Script
# Basic documentation checks for the current SAGE meta-repo layout

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd "$PROJECT_ROOT"

echo "======================================================================"
echo "📚 SAGE Documentation Quality Check"
echo "======================================================================"
echo ""

doc_roots=(README.md DEVELOPER.md CONTRIBUTING.md CHANGELOG.md)
[[ -d docs ]] && doc_roots+=(docs)
[[ -d examples ]] && doc_roots+=(examples)

collect_markdown_files() {
    find "${doc_roots[@]}" -type f \( -name "*.md" -o -name "README*" \) 2>/dev/null | \
        grep -vE '(/\.git/|node_modules|dist|build/_deps|/\.sage/|/site/|/\.pytest_cache/)' || true
}

MD_FILES=$(collect_markdown_files)

echo "1️⃣  Collecting documentation files..."
TOTAL_MD=$(printf '%s\n' "$MD_FILES" | sed '/^$/d' | wc -l)
echo "   Found $TOTAL_MD markdown/doc files"
echo ""

echo "2️⃣  Checking for placeholder text..."
PLACEHOLDERS=$(printf '%s\n' "$MD_FILES" | xargs -r grep -nE '\{[A-Z_][A-Z0-9_]*\}' 2>/dev/null || true)
if [ -z "$PLACEHOLDERS" ]; then
    echo -e "   ${GREEN}✅ No placeholder text found${NC}"
else
    echo -e "   ${YELLOW}⚠️  Placeholder text detected:${NC}"
    echo "$PLACEHOLDERS" | head -10
fi
echo ""

echo "3️⃣  Checking for TODO/FIXME markers..."
TODOS=$(printf '%s\n' "$MD_FILES" | xargs -r grep -nEi 'TODO|FIXME' 2>/dev/null || true)
TODO_COUNT=$(printf '%s\n' "$TODOS" | sed '/^$/d' | wc -l)
echo "   Found $TODO_COUNT TODO/FIXME markers"
if [ -n "$TODOS" ]; then
    echo "$TODOS" | head -10
fi
echo ""

echo "4️⃣  Checking for short README files..."
SHORT_READMES=$(find . -type f -name 'README*.md' 2>/dev/null | \
    grep -vE '(/\.git/|node_modules|/\.sage/|dist|build)' | \
    while read -r file; do
        lines=$(wc -l < "$file")
        if [ "$lines" -lt 10 ]; then
            echo "$file: $lines lines"
        fi
    done || true)
if [ -z "$SHORT_READMES" ]; then
    echo -e "   ${GREEN}✅ No unusually short README files${NC}"
else
    echo -e "   ${YELLOW}⚠️  Short README files found:${NC}"
    echo "$SHORT_READMES" | head -10
fi
echo ""

echo "5️⃣  Computing statistics..."
ROOT_READMES=$(find . -maxdepth 2 -type f -name 'README*.md' 2>/dev/null | wc -l)
DOCS_COUNT=0
EXAMPLE_DOCS_COUNT=0
[[ -d docs ]] && DOCS_COUNT=$(find docs -type f -name '*.md' | wc -l)
[[ -d examples ]] && EXAMPLE_DOCS_COUNT=$(find examples -type f -name '*.md' | wc -l)

echo "   Total markdown files: $TOTAL_MD"
echo "   Root/near-root READMEs: $ROOT_READMES"
echo "   docs markdown: $DOCS_COUNT"
echo "   example markdown: $EXAMPLE_DOCS_COUNT"
echo ""

echo "6️⃣  Generating report..."
REPORT_DIR="artifacts/reports"
mkdir -p "$REPORT_DIR"
REPORT_FILE="$REPORT_DIR/DOCUMENTATION_CHECK_REPORT_$(date +%Y%m%d).md"

cat > "$REPORT_FILE" <<EOF
# Documentation Check Report

- Date: $(date '+%Y-%m-%d %H:%M:%S')
- Repository: SAGE
- Total markdown files: $TOTAL_MD
- TODO/FIXME count: $TODO_COUNT

## Statistics

- Root/near-root READMEs: $ROOT_READMES
- docs markdown files: $DOCS_COUNT
- example markdown files: $EXAMPLE_DOCS_COUNT

## Placeholder Findings

$(if [ -n "$PLACEHOLDERS" ]; then echo '```'; echo "$PLACEHOLDERS" | head -50; echo '```'; else echo 'None'; fi)

## TODO/FIXME Findings

$(if [ -n "$TODOS" ]; then echo '```'; echo "$TODOS" | head -50; echo '```'; else echo 'None'; fi)

## Short README Findings

$(if [ -n "$SHORT_READMES" ]; then echo '```'; echo "$SHORT_READMES" | head -50; echo '```'; else echo 'None'; fi)
EOF

echo -e "   ${GREEN}✅ Report generated: $REPORT_FILE${NC}"
echo ""
echo "======================================================================"
echo "📊 Documentation Check Complete"
echo "======================================================================"
echo ""
echo "Summary:"
echo "  - Total docs: $TOTAL_MD files"
echo "  - TODO/FIXME: $TODO_COUNT"
echo "  - Report: $REPORT_FILE"
echo ""
