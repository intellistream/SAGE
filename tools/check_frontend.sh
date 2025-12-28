#!/bin/bash
set -e

# SAGE Frontend Check Script
# Runs linting, type checking, and unit tests for sage-studio frontend

echo "🔍 Checking sage-studio frontend..."

FRONTEND_DIR="packages/sage-studio/src/sage/studio/frontend"

if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ Error: Frontend directory not found at $FRONTEND_DIR"
    exit 1
fi

cd "$FRONTEND_DIR"

# Check if node_modules exists, if not, warn user
if [ ! -d "node_modules" ]; then
    echo "⚠️  node_modules not found. Running npm install..."
    npm install
fi

echo "📝 Running Type Check (tsc)..."
npm run build

echo "🧪 Running Unit Tests..."
npm test -- --run

echo "✅ Frontend checks passed!"
