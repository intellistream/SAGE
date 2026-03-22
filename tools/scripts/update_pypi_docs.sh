#!/bin/bash
# Update documentation to use wheelwright instead of legacy sage-dev package PyPI commands

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🔄 Updating PyPI publishing documentation..."
echo "📁 SAGE root: $SAGE_ROOT"

# Files to update
files=(
    "packages/sage-libs/docs/amms/BUILD_PUBLISH.md"
    "packages/sage-libs/docs/amms/PYPI_PUBLISH_GUIDE.md"
    "tools/docs/scripts/LIBAMM_MIGRATION_QUICKREF.md"
    "docs-public/docs_src/developers/ci-cd.md"
    "docs-public/docs_src/developers/commands.md"
    "docs-public/docs_src/dev-notes/l6-cli/COMMAND_CHEATSHEET.md"
)

echo ""
echo "📝 Files to update:"
for file in "${files[@]}"; do
    if [ -f "$SAGE_ROOT/$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ⚠️  $file (not found)"
    fi
done

echo ""
echo "🔧 Performing replacements..."

# Add deprecation notice at the top of relevant files
deprecation_notice="
> **⚠️  DEPRECATED**: The \`sage-dev package pypi\` command has been removed.
> Please use the standalone [wheelwright](https://github.com/intellistream/wheelwright) tool instead.
>
> **Migration**:
> \`\`\`bash
> git clone https://github.com/intellistream/wheelwright.git
> cd wheelwright
> ./publish.sh <package-name> --auto-bump patch
> \`\`\`
"

# Function to add deprecation notice
add_deprecation_notice() {
    local file="$1"
    if [ ! -f "$file" ]; then
        return
    fi

    # Check if notice already exists
    if grep -q "wheelwright\|sage-pypi-publisher" "$file"; then
        echo "  ℹ️  Deprecation notice already present in $(basename "$file")"
        return
    fi

    # Add after first heading
    awk -v notice="$deprecation_notice" '
        /^#/ && !found {
            print $0
            print notice
            found=1
            next
        }
        {print}
    ' "$file" > "$file.tmp" && mv "$file.tmp" "$file"

    echo "  ✅ Added deprecation notice to $(basename "$file")"
}

# Add notices to key files
for file in "${files[@]}"; do
    full_path="$SAGE_ROOT/$file"
    if [ -f "$full_path" ]; then
        add_deprecation_notice "$full_path"
    fi
done

echo ""
echo "✅ Documentation update complete!"
echo ""
echo "📖 Next steps:"
echo "  1. Review the changes: git diff"
echo "  2. Commit the updates: git commit -am 'docs: update PyPI publishing to use wheelwright'"
echo "  3. Update any remaining internal documentation as needed"
