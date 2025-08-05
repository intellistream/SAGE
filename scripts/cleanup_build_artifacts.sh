#!/bin/bash
# SAGE Build Artifacts Cleanup Script
# Generated on 2025-08-05 23:21:51

set -e

PROJECT_ROOT="/home/shuhao/SAGE"
cd "$PROJECT_ROOT"

echo "🧹 SAGE Build Artifacts Cleanup"
echo "================================"
echo "Project Root: $PROJECT_ROOT"
echo

# Function to show size
show_size() {
    if command -v du >/dev/null 2>&1; then
        du -sh "$1" 2>/dev/null || echo "0"
    else
        echo "Unknown"
    fi
}

# Function to safely remove
safe_remove() {
    local path="$1"
    local type="$2"
    
    if [ -e "$path" ]; then
        echo "  🗑️  Removing $type: $path"
        if [ "$type" = "directory" ]; then
            rm -rf "$path"
        else
            rm -f "$path"
        fi
    fi
}

echo "📊 Scanning for build artifacts..."

# Clean egg-info directories
echo
echo "🥚 Cleaning egg-info directories..."
find . -name "*.egg-info" -type d -not -path "./.venv/*" -not -path "./.git/*" | while read -r dir; do
    if [ -d "$dir" ]; then
        size=$(show_size "$dir")
        safe_remove "$dir" "directory"
    fi
done

# Clean dist directories  
echo
echo "📦 Cleaning dist directories..."
find . -name "dist" -type d -not -path "./.venv/*" -not -path "./.git/*" | while read -r dir; do
    if [ -d "$dir" ]; then
        size=$(show_size "$dir")
        safe_remove "$dir" "directory"
    fi
done

# Clean __pycache__ directories
echo
echo "🐍 Cleaning __pycache__ directories..."
find . -name "__pycache__" -type d -not -path "./.venv/*" -not -path "./.git/*" | while read -r dir; do
    if [ -d "$dir" ]; then
        safe_remove "$dir" "directory"
    fi
done

# Clean build directories
echo  
echo "🔨 Cleaning build directories..."
find . -name "build" -type d -not -path "./.venv/*" -not -path "./.git/*" | while read -r dir; do
    if [ -d "$dir" ]; then
        size=$(show_size "$dir")
        safe_remove "$dir" "directory"
    fi
done

# Clean coverage files
echo
echo "📊 Cleaning coverage files..."
find . -name ".coverage" -o -name "coverage.xml" -o -name "htmlcov" -type f -o -type d | while read -r item; do
    if [ -e "$item" ]; then
        if [ -d "$item" ]; then
            safe_remove "$item" "directory"
        else
            safe_remove "$item" "file"
        fi
    fi
done

# Clean pytest cache
echo
echo "🧪 Cleaning pytest cache..."
find . -name ".pytest_cache" -type d -not -path "./.venv/*" -not -path "./.git/*" | while read -r dir; do
    if [ -d "$dir" ]; then
        safe_remove "$dir" "directory"
    fi
done

echo
echo "✅ Cleanup completed!"
echo "🗑️  To see what would be removed without actually deleting, use: sage-dev clean --dry-run"
