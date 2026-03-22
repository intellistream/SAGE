#!/bin/bash
set -e

# SAGE Frontend Check Script
# Runs linting, type checking, and unit tests for sage-studio frontend

echo "🔍 Checking sage-studio frontend..."

FRONTEND_DIR="${FRONTEND_DIR:-../sage-studio/frontend}"

if [ ! -d "$FRONTEND_DIR" ]; then
    echo "⚠️  Frontend directory not found at $FRONTEND_DIR"
    echo "   Skipping frontend checks (this is OK for CI without frontend changes)"
    exit 0
fi

cd "$FRONTEND_DIR"

# Check if package.json exists
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found in $FRONTEND_DIR"
    exit 1
fi

# Check if node_modules exists, if not, run npm install
if [ ! -d "node_modules" ]; then
    echo "⚠️  node_modules not found. Running npm install..."
    # Use npm ci for CI environments (faster and more reliable)
    if [ -f "package-lock.json" ]; then
        npm ci --prefer-offline --no-audit || npm install --prefer-offline --no-audit
    else
        npm install --prefer-offline --no-audit
    fi
fi

echo "📝 Running Type Check (tsc)..."
npm run build

echo "🧪 Running Unit Tests..."
npm test -- --run

echo "✅ Frontend checks passed!"
