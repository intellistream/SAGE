#!/usr/bin/env bash
# Fix code quality issues before commit
# This script runs the same checks as CI/CD

set -e

cd "$(dirname "$0")/.."

echo "🔍 Running code quality checks..."
echo ""

# Run black
echo "📝 Running black formatter..."
pre-commit run black --all-files --config tools/pre-commit-config.yaml || true

# Run isort
echo "📦 Running isort..."
pre-commit run isort --all-files --config tools/pre-commit-config.yaml || true

# Run ruff
echo "🔧 Running ruff linter..."
pre-commit run ruff --all-files --config tools/pre-commit-config.yaml || true

echo ""
echo "✅ Code quality fixes applied!"
echo "📌 Please review changes and commit them."
echo ""
echo "💡 To prevent this in the future:"
echo "   1. Make sure pre-commit hooks are installed:"
echo "      pre-commit install --config tools/pre-commit-config.yaml"
echo "   2. Don't use 'git commit -n' or '--no-verify'"
echo "   3. Run 'pre-commit run --all-files --config tools/pre-commit-config.yaml' before pushing"
