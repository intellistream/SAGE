#!/usr/bin/env bash

# Script to generate a requirements-lock.txt file for SAGE
# This will provide the fastest possible installation experience for users

set -e

echo "=== Generating optimized requirements-lock.txt for SAGE ==="

# Create a comprehensive locked requirements file
cat > requirements-lock.txt << 'EOF'
# SAGE Framework - Locked Dependencies for Fast Installation
# This file pins all dependencies to specific versions to avoid
# pip's dependency resolution backtracking hell.
# Generated on $(date)

# Core SAGE packages
sage-kernel==1.0.0
sage-middleware==1.0.0  
sage-userspace==1.0.0
sage-dev-toolkit==1.0.0

# Core system dependencies
numpy==2.2.6
scipy==1.15.3
pandas==2.3.1
packaging==25.0
typing-extensions==4.14.1
six==1.17.0

# Configuration and data formats
pyyaml==6.0.2
python-dotenv==1.1.1
tomli==2.2.1
tomli-w==1.2.0
jinja2==3.1.6
MarkupSafe==3.0.2

# Network and HTTP stack
httpx==0.28.1
httpcore==1.0.9
h11==0.16.0
sniffio==1.3.1
anyio==4.10.0
socksio==1.0.0
aiohttp==3.12.15
aiohappyeyeballs==2.6.1
aiosignal==1.4.0
frozenlist==1.7.0
propcache==0.3.2
yarl==1.20.1
multidict==6.6.3
attrs==25.3.0
requests==2.32.4
charset-normalizer==3.4.2
urllib3==2.5.0
certifi==2025.8.3
idna==3.10

# Web framework stack
fastapi==0.115.12
uvicorn==0.34.3
starlette==0.46.2
python-multipart==0.0.20

# ML and AI core
torch==2.7.1
torchvision==0.22.1
transformers==4.54.1
tokenizers==0.21.4
accelerate==1.9.0
huggingface-hub==0.34.3
sentence-transformers==5.0.0
InstructorEmbedding==1.0.1
peft==0.17.0

# Search and retrieval
faiss-cpu==1.9.0
bm25s==0.2.13
rank-bm25==0.2.2
PyStemmer==3.0.0

# AWS/Cloud services
aioboto3==14.1.0
aiobotocore==2.21.1
boto3==1.37.1
botocore==1.37.1
aiofiles==24.1.0
aioitertools==0.12.0
jmespath==1.0.1
wrapt==1.17.2
s3transfer==0.11.5

# Distributed computing
ray==2.48.0
grpcio==1.74.0
protobuf==6.31.1
msgpack==1.1.1
dill==0.4.0

# LLM service APIs
openai==1.98.0
ollama==0.5.1
vllm==0.10.0
zhipuai==2.1.5.20250801
cohere==5.16.2

# Task queue and workers
celery==5.5.3
flower==2.0.1

# Security and authentication
passlib==1.7.4
python-jose==3.5.0
cryptography==45.0.5

# Development and testing tools
rich==14.1.0
typer==0.16.0
pytest==8.4.1
pytest-cov==6.2.1
pytest-asyncio==1.1.0
pytest-benchmark==5.1.0
safety==3.6.0

# System utilities
psutil==6.1.0
pathspec==0.12.1
gitpython==3.1.45
gitdb==4.0.12
smmap==5.0.2
shellingham==1.5.4
networkx==3.4.2

# Data processing utilities
feedparser==6.0.11
python-dateutil==2.9.0.post0
pytz==2025.2
tzdata==2025.2

# Testing and quality tools
iniconfig==2.1.0
pluggy==1.6.0
pygments==2.19.2
py-cpuinfo==9.0.0
coverage==7.10.2
markdown-it-py==3.0.0
mdurl==0.1.2

# Security scanning
authlib==1.6.1
click==8.2.1
dparse==0.6.4
filelock==3.16.1
marshmallow==4.0.0
nltk==3.9.1
pydantic==2.9.2
pydantic-core==2.23.4
annotated-types==0.7.0
ruamel.yaml==0.18.14
ruamel.yaml.clib==0.2.12
safety-schemas==0.0.14
tenacity==9.1.2
tomlkit==0.13.3
regex==2025.7.34
tqdm==4.67.1
joblib==1.5.1

# Math and symbolic computation
sympy==1.14.0
fsspec==2025.7.0

# JSON schema validation
jsonschema==4.25.0

# Build tools
Cython==3.1.2
pybind11==3.0.0
EOF

echo "Generated requirements-lock.txt with pinned versions"

# Create a PyPI-ready setup.py with these locked dependencies
cat > setup_optimized.py << 'EOF'
"""
Optimized setup.py for SAGE with locked dependencies
This version prioritizes installation speed over flexibility
"""

from setuptools import setup, find_packages

# Read locked requirements
with open('requirements-lock.txt', 'r') as f:
    locked_requirements = [
        line.strip() 
        for line in f 
        if line.strip() and not line.startswith('#') and '==' in line
    ]

setup(
    name="sage-optimized",
    version="1.0.0",
    description="SAGE Framework (Optimized for Fast Installation)",
    long_description="SAGE Framework with locked dependencies for fastest installation experience",
    packages=find_packages(),
    install_requires=locked_requirements,
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
EOF

echo "=== Optimization Complete ==="
echo ""
echo "📦 Generated files:"
echo "  - requirements-lock.txt: Locked dependencies for fastest installation"
echo "  - setup_optimized.py: Optimized setup script"
echo ""
echo "🚀 For fastest user installation experience:"
echo "  pip install sage -r requirements-lock.txt"
echo ""
echo "📈 This should reduce installation time from minutes to seconds by:"
echo "  1. Eliminating dependency resolution backtracking"
echo "  2. Using exact version specifications"
echo "  3. Preferring binary wheels over source builds"
