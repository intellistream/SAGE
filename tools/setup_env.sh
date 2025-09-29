#!/bin/bash
# SAGE Environment Setup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔧 SAGE Environment Setup"
echo "=========================="
echo "Project root: $PROJECT_ROOT"
echo

# Check if .env file exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "✅ .env file already exists at $PROJECT_ROOT/.env"
    echo
else
    echo "📋 Creating .env file from template..."
    
    if [ -f "$PROJECT_ROOT/.env.template" ]; then
        cp "$PROJECT_ROOT/.env.template" "$PROJECT_ROOT/.env"
        echo "✅ Created .env file at $PROJECT_ROOT/.env"
        echo "📝 Please edit this file and fill in your API keys:"
        echo "   - OPENAI_API_KEY (required for most examples)"
        echo "   - HF_TOKEN (for Hugging Face models)"
        echo "   - Other service API keys as needed"
        echo
        
        # Open .env file in editor if available
        if command -v code &> /dev/null; then
            echo "💡 Opening .env file in VS Code..."
            code "$PROJECT_ROOT/.env"
        elif command -v nano &> /dev/null; then
            echo "💡 You can edit the file with: nano $PROJECT_ROOT/.env"
        elif command -v vim &> /dev/null; then
            echo "💡 You can edit the file with: vim $PROJECT_ROOT/.env"
        else
            echo "💡 Please edit the file: $PROJECT_ROOT/.env"
        fi
    else
        echo "❌ .env.template not found!"
        echo "Please create a .env file manually with your API keys."
        exit 1
    fi
fi

# Check Python and dependencies
echo "🐍 Checking Python environment..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo "❌ Python not found!"
    exit 1
fi

echo "✅ Python found: $($PYTHON_CMD --version)"

# Check if python-dotenv is installed
if $PYTHON_CMD -c "import dotenv" 2>/dev/null; then
    echo "✅ python-dotenv is installed"
else
    echo "📦 Installing python-dotenv..."
    $PYTHON_CMD -m pip install python-dotenv
fi

# Run environment check
echo
echo "🔍 Checking environment configuration..."
$PYTHON_CMD -m sage.tools.cli.main config env setup --no-open

echo
echo "🎉 Environment setup complete!"
echo
echo "Next steps:"
echo "1. Edit $PROJECT_ROOT/.env and add your API keys"
echo "2. Run examples: python examples/agents/agent.py"
echo "3. Run tests: python -m pytest"