#!/bin/bash
eval "$(conda shell.bash hook)"
conda activate sage
echo "🎉 Welcome to SAGE! Environment activated successfully."
echo "📝 Your prompt now shows (sage) indicating the active environment"
echo "🚀 Quick test: python -c 'import sage; print(\"SAGE ready!\")'"
echo ""
exec bash
